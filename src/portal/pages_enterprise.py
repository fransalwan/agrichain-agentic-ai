"""Operational pages for each partner enterprise."""
from __future__ import annotations

from typing import Any, Dict, List

import altair as alt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.settings import DATA_DIR, settings
from src.portal import components as ui
from src.portal import core
from src.portal.core import fmt_kg, fmt_num, fmt_pct, fmt_rp, fmt_rp_short

LOCK_HELP = "Data rahasia milik mitra lain. Hanya pemilik data yang dapat melihatnya."


def _locked(value: Any) -> bool:
    return isinstance(value, str) and "REDACTED" in value


# ===========================================================================
# AgroFarm
# ===========================================================================
def agrofarm_fields() -> None:
    state = ui.require_cycle()
    blocks = state.get("agrofarm_monitoring", [])

    ui.section("Kondisi blok lahan",
               "Status dihitung dari NDVI (kehijauan tanaman) dibanding rata-rata 14 hari dan curah hujan.")
    if any(b.get("stale_data") for b in blocks):
        st.warning("Sensor salah satu blok mati ≥ 3 hari. Perkiraan memakai data historis dan rentangnya diperlebar.",
                   icon=":material/sensors_off:")
    if blocks:
        df = pd.DataFrame([{
            "Blok": b["block_id"], "Lot": b["lot_id"], "Varietas": b["variety"], "Luas (ha)": b["area_ha"],
            "NDVI hari ini": b["ndvi_today"], "Batas bawah normal": b["ndvi_2sigma_lower"],
            "Hujan 14 hari (mm)": b["rain_14d_mm"], "Kelembapan tanah (%)": b["soil_moisture_pct"],
            "Status": "Normal" if b["status"] == "NORMAL" else "Perlu dicek",
            "Catatan": core.id_text("; ".join(b["causes"])) if b["causes"] else "-",
        } for b in blocks])
        styled = df.style.map(
            lambda v: f"color: {'#15803D' if v == 'Normal' else '#C2410C'}; font-weight: 600", subset=["Status"])
        st.dataframe(styled, hide_index=True, column_config={
            "NDVI hari ini": st.column_config.ProgressColumn(
                min_value=0.0, max_value=1.0, format="%.2f",
                help="Indeks kehijauan tanaman (0–1). Makin tinggi makin sehat."),
            "Batas bawah normal": st.column_config.NumberColumn(
                format="%.2f",
                help="NDVI terendah yang masih wajar untuk blok ini: rata-rata 14 hari terakhir dikurangi "
                     "2× simpangan bakunya. Jika NDVI hari ini di bawah angka ini, blok ditandai 'Perlu dicek'."),
        })

    ui.section("Perkirakan hasil panen", "Masukkan kondisi blok untuk melihat perkiraan hasil dan jendela panen.")
    left, right = st.columns([1, 1.2])
    with left, st.form("agro_predict", border=True):
        blk = st.selectbox("Blok", [b["block_id"] for b in blocks] or ["BLK-11"])
        cur = next((b for b in blocks if b["block_id"] == blk), {})
        c1, c2 = st.columns(2)
        area = c1.number_input("Luas (ha)", 0.4, 2.0, float(cur.get("area_ha", 0.7)), 0.05)
        ndvi = c2.number_input("NDVI", 0.30, 0.90, float(cur.get("ndvi_today", 0.64)), 0.01)
        rain = c1.number_input("Curah hujan (mm)", 0.0, 150.0, float(min(cur.get("rain_14d_mm", 24.0), 150.0)), 2.0)
        age = c2.number_input("Umur tanaman (hari)", 65, 90, 78)
        offline = st.toggle(
            "Sensor lahan tidak mengirim data (≥ 3 hari)", value=bool(cur.get("stale_data")),
            help="Aktifkan bila sensor kelembapan/suhu/NDVI di blok ini rusak atau terputus. "
                 "Perkiraan akan memakai rata-rata panen historis dengan rentang lebih lebar, "
                 "jadi gunakan hanya sebagai acuan kasar.")
        submitted = st.form_submit_button("Hitung perkiraan", type="primary", icon=":material/calculate:")

    with right:
        if submitted or "agro_pred" not in st.session_state:
            payload = {
                "block_id": blk, "lot_id": cur.get("lot_id", "H003"), "area_ha": area,
                "avg_temp_c": float(cur.get("avg_temp_c", 26.5)), "soil_moisture_pct": float(cur.get("soil_moisture_pct", 66.0)),
                "rainfall_mm": rain, "fertilizer_kg_ha": 165.0, "crop_age_days": int(age), "ndvi": ndvi,
                "extreme_rain_flag": rain > 90, "sensor_offline_days": 3 if offline else 0,
            }
            ok, res = core.api_call("POST", "/api/v1/agrofarm/predict", token=core.token(), json=payload)
            st.session_state["agro_pred"] = (ok, res)
        ok, res = st.session_state["agro_pred"]
        if not ok:
            st.error(res, icon=":material/error:")
        else:
            p = res["prediction"]
            hw = p["harvest_window"]
            with st.container(border=True):
                with st.container(horizontal=True):
                    st.metric("Perkiraan hasil", fmt_kg(p["predicted_kg"]))
                    st.metric("Rentang kemungkinan", f"{fmt_num(p['pi80_interval_kg'][0])}–{fmt_num(p['pi80_interval_kg'][1])} kg",
                              help="80% kemungkinan hasil panen berada di rentang ini.")
                shift = hw["shift_days"]
                shift_txt = "sesuai jadwal" if shift == 0 else (f"dimajukan {abs(shift)} hari" if shift < 0 else f"dimundurkan {shift} hari")
                st.markdown(f":material/event: **Jendela panen:** {hw['start']} s.d. {hw['end']} ({shift_txt})")
                st.caption(core.id_text(hw["reason"]))
                if p.get("doubtful"):
                    st.warning("Perkiraan kurang pasti karena sensor mati; gunakan sebagai acuan kasar.", icon=":material/warning:")
            fi = res.get("feature_importance", {})
            if fi:
                with st.expander("Faktor yang paling berpengaruh", icon=":material/insights:"):
                    names = {"area_ha": "Luas lahan", "soil_moisture_pct": "Kelembapan tanah", "ndvi": "NDVI",
                             "fertilizer_kg_ha": "Pupuk", "rainfall_mm": "Curah hujan", "crop_age_days": "Umur tanaman",
                             "avg_temp_c": "Suhu rata-rata"}
                    st.caption("Seberapa besar model mengandalkan tiap faktor, dipelajari dari riwayat panen "
                               "saat model dilatih. Berlaku umum untuk semua blok, bukan khusus perkiraan di atas, "
                               "dan tidak menunjukkan arah pengaruh (naik/turun).")
                    fdf = pd.DataFrame({"Faktor": [names.get(k, k) for k in fi],
                                        "Pengaruh (%)": [v * 100 for v in fi.values()]})
                    st.bar_chart(fdf, x="Faktor", y="Pengaruh (%)", horizontal=True, sort="-Pengaruh (%)", height=240)


def agrofarm_signals() -> None:
    state = ui.require_cycle()
    ui.section("Masukan mutu dari FreshFood", "Temuan pemeriksaan mutu yang berkaitan dengan blok lahan Anda.")
    fb = state.get("freshfood_qc_feedback", {}).get("feedback_to_agrofarm", [])
    if not fb:
        st.success("Tidak ada temuan mutu pada siklus ini.", icon=":material/task_alt:")
    for f in fb:
        with st.container(border=True):
            with st.container(horizontal=True, vertical_alignment="center"):
                st.markdown(f"**{f['block_id']} · Lot {f['lot_id']}**")
                crit = f["severity"] == "CRITICAL"
                st.badge("Kritis" if crit else "Saran", color="red" if crit else "blue")
            st.caption("Temuan: " + ", ".join(core.humanize_reason(x) for x in f["findings"]))
            st.write(core.id_text(f["recommendation"]))

    ui.section("Perkiraan permintaan SuperMart 7 hari", "Dipakai untuk merencanakan waktu dan volume panen.")
    with st.container(border=True):
        ui.demand_chart(state.get("supermart_horizon_7d", {}).get("horizon_7d", []))


# ===========================================================================
# Koperasi
# ===========================================================================
PERFORMATIVE = {
    "CFP": "Permintaan penawaran", "PROPOSE": "Penawaran", "ACCEPT_PROPOSAL": "Penawaran diterima",
    "REJECT_PROPOSAL": "Penawaran ditolak", "COUNTER_PROPOSE": "Tawaran balik", "INFORM": "Informasi",
    "REQUEST": "Permintaan", "AGREE": "Setuju", "REFUSE": "Menolak",
}


def koperasi_pricing() -> None:
    state = ui.require_cycle()
    st.caption("Perkiraan harga pasar per grade dan penilaian tawaran pembeli.")

    grade = st.segmented_control("Grade tomat", ["A", "B", "C"], default="A", required=True, key="kop_grade")
    ok, res = core.api_read("POST", "/api/v1/koperasi/price-forecast", json={"grade": grade})
    if not ok:
        st.error(res, icon=":material/error:")
        return
    market, floor = res["predicted_market_price_rp"], res["floor_price_rp"]

    left, right = st.columns(2)
    with left, st.container(border=True):
        st.markdown("**Harga acuan**")
        with st.container(horizontal=True):
            st.metric("Perkiraan harga pasar", f"{fmt_rp(market)}/kg", help="Prediksi model LightGBM untuk grade ini.")
            if _locked(floor):
                st.metric("Harga minimum", "Tersembunyi", help=LOCK_HELP)
            else:
                st.metric("Harga minimum", f"{fmt_rp(floor)}/kg", help="Harga terendah yang masih layak bagi petani.")
    with right, st.container(border=True):
        st.markdown("**Nilai tawaran pembeli**")
        offer = st.number_input("Tawaran (Rp/kg)", 1000, 20000, int(market * 0.92 // 100 * 100), 100)
        if _locked(floor):
            st.caption("Penilaian tawaran memerlukan harga minimum, yang hanya dapat dilihat Koperasi Tani.")
        elif offer >= floor:
            st.success(f"Tawaran layak diterima. Selisih di atas harga minimum: {fmt_rp(offer - floor)}/kg.",
                       icon=":material/thumb_up:")
        else:
            st.error(f"Tawaran {fmt_rp(floor - offer)}/kg di bawah harga minimum. Ajukan tawaran balik minimal "
                     f"{fmt_rp(floor)}/kg.", icon=":material/thumb_down:")

    ui.section("Negosiasi pada siklus ini")
    msgs = [m for m in state.get("messages", []) if m["performative"] in PERFORMATIVE and m["protocol"].upper().find("CONTRACT") >= 0]
    if msgs:
        st.dataframe(pd.DataFrame([{
            "Waktu": core.fmt_time(m["timestamp"]), "Dari": m["sender"], "Ke": m["receiver"],
            "Jenis": PERFORMATIVE[m["performative"]], "Putaran": m["negotiation_round"],
        } for m in msgs]), hide_index=True)
    else:
        st.caption(f"Tidak ada negosiasi ulang. Putaran yang dipakai: {state['global_kpis']['negotiation_rounds_used']} dari 3.")

    ui.section("Perkiraan permintaan SuperMart 7 hari")
    with st.container(border=True):
        ui.demand_chart(state.get("supermart_horizon_7d", {}).get("horizon_7d", []))


# ===========================================================================
# FreshFood
# ===========================================================================
@st.cache_resource(show_spinner=False)
def _cnn_model():
    from src.models.freshfood_cnn import FreshFoodVisualGradingModel
    return FreshFoodVisualGradingModel.load()


@st.cache_data(show_spinner=False)
def _cnn_samples() -> List[Dict[str, Any]]:
    path = DATA_DIR / "freshfood_tomato_images.npz"
    if not path.exists():
        return []
    data = np.load(path, allow_pickle=False)
    imgs, labels = data["images"], data["labels"]
    out = []
    for cls in ("A", "B", "C", "Reject"):
        for idx in np.where(labels == cls)[0][:2]:
            out.append({"true": str(labels[idx]), "image": imgs[idx]})
    return out


def freshfood_quality() -> None:
    ui.require_cycle()
    ui.section("Inspeksi mutu & keamanan pangan",
               "Lot yang gagal salah satu uji keamanan otomatis diblokir (0 kg masuk jalur pangan).")
    left, right = st.columns([1, 1.1])
    with left, st.form("ff_qc", border=True):
        c1, c2 = st.columns(2)
        lot = c1.selectbox("Lot", ["H001", "H002", "H003"], index=2)
        block = c2.selectbox("Blok asal", ["BLK-07", "BLK-03", "BLK-11"], index=2)
        qty = c1.number_input("Volume (kg)", 100.0, 3000.0, 1000.0, 100.0)
        ph = c2.number_input("pH (aman 4,0–4,6)", 3.0, 6.0, 4.35, 0.05)
        pest = c1.number_input("Residu pestisida (ppm, maks 0,05)", 0.0, 0.2, 0.02, 0.01)
        defect = c2.number_input("Cacat permukaan (%)", 0, 40, 14, 1)
        microbe = st.toggle("Lolos uji mikroba", value=True)
        run = st.form_submit_button("Jalankan inspeksi", type="primary", icon=":material/biotech:")

    with right:
        if run:
            payload = {"lot_id": lot, "block_id": block, "qty_kg": qty, "ph_level": ph, "pesticide_residue_ppm": pest,
                       "microbial_pass": microbe, "defect_ratio": defect / 100}
            st.session_state["ff_qc_res"] = core.api_call("POST", "/api/v1/freshfood/qc-inspect", token=core.token(),
                                                          json=payload)
        if "ff_qc_res" not in st.session_state:
            with st.container(border=True):
                st.caption("Hasil inspeksi akan tampil di sini.")
        else:
            ok, res = st.session_state["ff_qc_res"]
            if not ok:
                st.error(res, icon=":material/error:")
            else:
                v = res["safety_verdict"]
                with st.container(border=True):
                    if v["food_safety_approved"]:
                        st.success(f"Lot {res['lot_id']} lolos uji keamanan pangan dan boleh diproses.", icon=":material/verified:")
                    else:
                        st.error(f"Lot {res['lot_id']} diblokir dari jalur pangan.", icon=":material/block:")
                        for r in v["violation_reasons"]:
                            st.markdown(f"- {core.humanize_reason(r)}")
                        plan = res.get("waste_valorization_plan") or {}
                        if plan:
                            st.caption("Lot dialihkan ke mitra kompos/biogas agar tidak terbuang.")
                    fb = res.get("qc_feedback_to_agrofarm")
                    if fb:
                        st.info(f"Masukan dikirim ke AgroFarm ({fb['block_id']}): {core.id_text(fb['recommendation'])}", icon=":material/send:")
                    st.caption(f"Tercatat di log audit · {res['audit_hash'][:12]}…")

    with st.expander("Contoh penilaian visual otomatis (kamera)", icon=":material/photo_camera:"):
        st.caption("Model CNN menilai grade tomat dari foto. Contoh dari data uji:")
        if st.toggle("Tampilkan contoh", key="ff_show_cnn"):
            samples = _cnn_samples()
            if not samples:
                st.caption("Data gambar tidak tersedia.")
            else:
                preds = _cnn_model().classify_images(np.stack([s["image"] for s in samples]))
                from PIL import Image
                with st.container(horizontal=True):
                    for s, p in zip(samples, preds):
                        img = Image.fromarray(s["image"].astype(np.uint8)).resize((96, 96), Image.Resampling.NEAREST)
                        g = p["predicted_grade"]
                        st.image(img, caption=f"{'Ditolak' if g == 'Reject' else 'Grade ' + g} · {p['confidence'] * 100:.0f}%")


def freshfood_schedule() -> None:
    state = ui.require_cycle()
    ff = state.get("freshfood_qc_feedback", {})
    st.caption("Lot diproses berdasarkan umur simpan terpendek lebih dulu (FEFO).")
    overtime = st.toggle("Aktifkan shift lembur (+500 kg, dok buka hingga 14:00)",
                         value=bool(state["global_kpis"].get("overtime_activated")), key="ff_overtime")
    ok, res = core.api_read("POST", "/api/v1/freshfood/schedule", json={"include_overtime": overtime},
                            spinner="Menyusun jadwal…")
    if not ok:
        st.error(res, icon=":material/error:")
        return
    sched, dock = res["fefo_schedule"], res["receiving_dock_window"]
    with st.container(horizontal=True):
        st.metric("Total dijadwalkan", fmt_kg(sched.get("total_scheduled_kg", 0)), border=True)
        st.metric("Utilisasi lini", fmt_pct(sched.get("capacity_utilization_pct", 0), 0), border=True)
        st.metric("Jam terima barang", f"{dock['open_time']}–{dock['close_time']}", border=True,
                  help="Disinkronkan otomatis ke rute ColdChain.")
        st.metric("Slot bongkar", str(dock["unloading_slots"]), border=True)
    lots = sched.get("scheduled_lots", [])
    if lots:
        st.dataframe(pd.DataFrame([{
            "Lot": x["lot_id"], "Grade": x["grade"], "Umur simpan (hari)": x["shelf_life_days"],
            "Dijadwalkan (kg)": x["scheduled_kg"], "Shift": "Lembur" if x["slot"] == "OVERTIME" else "Reguler",
        } for x in lots]), hide_index=True)

    val = ff.get("waste_valorization_plan", [])
    if val:
        ui.section("Lot yang dialihkan ke kompos/biogas")
        st.dataframe(pd.DataFrame([{
            "Lot": v["lot_id"], "Volume (kg)": v["blocked_qty_kg"], "Perkiraan nilai pemulihan": fmt_rp(v["est_recovery_value_rp"]),
            "Catatan": v["note"],
        } for v in val]), hide_index=True)


# ===========================================================================
# ColdChain
# ===========================================================================
VRPTW_SCENARIOS = {
    "NORMAL": "Normal", "ROAD_DISRUPTION": "Jalan terganggu",
    "VEHICLE_BREAKDOWN": "Kendaraan rusak", "COLD_STORAGE_DROP": "Kapasitas gudang turun",
}
TRAFFIC = {0: "Lancar", 1: "Sedang", 2: "Padat"}


def _route_map(plan: Dict[str, Any]) -> go.Figure:
    palette = ["#0F766E", "#2563EB", "#D97706", "#7C3AED"]
    fig = go.Figure()
    for i, r in enumerate(plan.get("routes", [])):
        coords = r.get("coords", [])
        if not coords:
            continue
        fig.add_trace(go.Scattermap(
            lat=[c["lat"] for c in coords], lon=[c["lon"] for c in coords], mode="lines+markers",
            name=f"{r['truck']} · {r['distance_km']} km", line=dict(width=4, color=palette[i % 4]),
            marker=dict(size=10, color=palette[i % 4]),
            hovertext=[f"{c['name']} · tiba {core.minutes_to_clock(c['arrival_min'])}" for c in coords], hoverinfo="text",
        ))
    fig.update_layout(map=dict(style="open-street-map", center=dict(lat=-7.775, lon=110.355), zoom=10.3),
                      height=420, margin=dict(l=0, r=0, t=0, b=0),
                      legend=dict(orientation="h", y=0.01, x=0.01, bgcolor="rgba(255,255,255,0.9)"))
    return fig


def coldchain_routes() -> None:
    state = ui.require_cycle()
    st.caption("Rute dioptimalkan agar semua tiba dalam jam terima mitra dengan suhu 7–12 °C.")
    default = {"COLD_STORAGE_FAILURE": "COLD_STORAGE_DROP", "COMPOUND": "COLD_STORAGE_DROP",
               "EXTREME_RAIN": "ROAD_DISRUPTION"}.get(state["trigger_mode"], "NORMAL")
    with st.container(horizontal=True):
        scen = st.segmented_control("Kondisi", list(VRPTW_SCENARIOS), default=default, required=True,
                                    format_func=VRPTW_SCENARIOS.get, key=f"cc_scen_{state['trigger_mode']}")
        traffic = st.segmented_control("Lalu lintas", list(TRAFFIC), default=1, required=True,
                                       format_func=TRAFFIC.get, key="cc_traffic")
    ok, res = core.api_read("POST", "/api/v1/coldchain/vrptw", json={"scenario": scen, "traffic_level": traffic},
                            spinner="Menghitung rute terbaik…")
    if not ok:
        st.error(res, icon=":material/error:")
        return
    plan, normal = res["active_plan"], res["normal_baseline"]
    d_km = plan["optimized_distance_km"] - normal["optimized_distance_km"]
    with st.container(horizontal=True):
        st.metric("Total jarak", f"{fmt_num(plan['optimized_distance_km'])} km",
                  f"{d_km:+.0f} km vs normal" if abs(d_km) > 0.5 else None, delta_color="inverse", border=True)
        st.metric("Biaya transport", fmt_rp_short(plan["transport_cost_rp"]), border=True)
        st.metric("Truk dipakai", str(len(plan.get("routes", []))), border=True)
        st.metric("Pengiriman terlambat", str(plan["time_window_violations"]), border=True)

    left, right = st.columns([1.3, 1])
    with left, st.container(border=True):
        st.plotly_chart(_route_map(plan), config={"displayModeBar": False})
    with right:
        for r in plan.get("routes", []):
            with st.container(border=True):
                st.markdown(f":material/local_shipping: **{r['truck']}** · {r['distance_km']} km · ±{r['predicted_eta_min']:.0f} menit")
                st.caption(" → ".join(r["stops"]))
                st.progress(min(r["utilization_pct"] / 100, 1.0),
                            text=f"Muatan {fmt_kg(r['load_kg'])} dari {fmt_kg(r['capacity_kg'])} ({fmt_num(r['utilization_pct'], 0)}%)")


@st.dialog("Tambah kendaraan")
def _vehicle_dialog() -> None:
    with st.form("cc_vehicle"):
        vid = st.text_input("ID kendaraan", "V005")
        cap = st.number_input("Kapasitas (kg)", 500, 10000, 3500, 250)
        status = st.selectbox("Status", ["Available", "In Transit", "Maintenance"],
                              format_func={"Available": "Tersedia", "In Transit": "Dalam perjalanan", "Maintenance": "Perawatan"}.get)
        driver = st.text_input("Pengemudi", "D-005 (Eko P.)")
        if st.form_submit_button("Simpan", type="primary"):
            ok, res = core.api_call("POST", "/api/v1/coldchain/fleet", token=core.token(), json={
                "vehicle_id": vid, "capacity_kg": cap, "min_temp_c": 7.0, "max_temp_c": 12.0, "status": status, "driver_ref": driver})
            if ok:
                st.session_state["_toast"] = (f"Kendaraan {vid} tersimpan.", ":material/check_circle:")
                st.rerun()
            st.error(res)


@st.dialog("Buat permintaan kirim")
def _shipment_dialog() -> None:
    with st.form("cc_ship"):
        c1, c2 = st.columns(2)
        sid = c1.text_input("ID pengiriman", "SH004")
        lot = c2.text_input("Lot", "H004")
        qty = c1.number_input("Volume (kg)", 100, 5000, 800, 100)
        dest = c2.selectbox("Tujuan", ["SuperMart_DC", "FreshFood_Plant", "SuperMart_B2", "Partner3PL_WH"])
        ready = c1.text_input("Siap diambil (JJ:MM)", "08:30")
        deadline = c2.text_input("Batas tiba (JJ:MM)", "12:30")
        if st.form_submit_button("Simpan", type="primary"):
            ok, res = core.api_call("POST", "/api/v1/coldchain/shipments", token=core.token(), json={
                "shipment_id": sid, "lot_id": lot, "quantity_kg": qty, "destination": dest, "ready_time": ready, "deadline": deadline})
            if ok:
                st.session_state["_toast"] = (f"Permintaan {sid} tersimpan.", ":material/check_circle:")
                st.rerun()
            st.error(res)


def coldchain_fleet() -> None:
    ui.require_cycle()
    fleet_tab, ship_tab = st.tabs(["Armada", "Permintaan kirim"])
    with fleet_tab:
        with st.container(horizontal=True, horizontal_alignment="right"):
            if st.button("Tambah kendaraan", icon=":material/add:", type="primary"):
                _vehicle_dialog()
        ok, res = core.api_call("GET", "/api/v1/coldchain/fleet", token=core.token())
        if ok:
            st.dataframe(pd.DataFrame(res["vehicles"]).rename(columns={
                "vehicle_id": "Kendaraan", "reefer_type": "Jenis", "capacity_kg": "Kapasitas (kg)",
                "min_temp_c": "Suhu min (°C)", "max_temp_c": "Suhu maks (°C)", "status": "Status",
                "driver_ref": "Pengemudi", "maintenance_due": "Jadwal servis"}), hide_index=True)
        else:
            st.error(res)
    with ship_tab:
        with st.container(horizontal=True, horizontal_alignment="right"):
            if st.button("Buat permintaan", icon=":material/add:", type="primary"):
                _shipment_dialog()
        ok, res = core.api_call("GET", "/api/v1/coldchain/shipments", token=core.token())
        if ok:
            st.dataframe(pd.DataFrame(res["shipments"]).rename(columns={
                "shipment_id": "Pengiriman", "lot_id": "Lot", "product": "Produk", "grade": "Grade",
                "quantity_kg": "Volume (kg)", "pickup": "Ambil di", "destination": "Tujuan", "ready_time": "Siap",
                "deadline": "Batas tiba", "req_temp_min_c": "Suhu min", "req_temp_max_c": "Suhu maks",
                "shelf_life_hours": "Umur simpan (jam)", "priority": "Prioritas", "status": "Status"}), hide_index=True)
        else:
            st.error(res)


@st.cache_data(ttl=300, show_spinner=False)
def _telemetry() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "coldchain_iot_telemetry.csv")
    df["ts"] = pd.to_datetime(df["ts"])
    return df


def coldchain_temperature() -> None:
    ui.require_cycle()
    ui.section("Suhu gudang dingin", f"Batas aman tomat {settings.tomato_safe_temp_min_c:g}–{settings.tomato_safe_temp_max_c:g} °C. "
                                     "Titik merah adalah anomali yang terdeteksi otomatis.")
    df = _telemetry()
    zones = sorted(df["zone_id"].unique())
    zone = st.segmented_control("Zona", zones, default=zones[0], required=True, key="cc_zone")
    z = df[df["zone_id"] == zone].tail(300)
    last = z.iloc[-1]
    with st.container(horizontal=True):
        st.metric("Suhu terakhir", f"{last['temp_c']:.1f} °C", border=True)
        st.metric("Kelembapan", f"{last['humidity_pct']:.0f}%", border=True)
        st.metric("Anomali (periode ini)", str(int(z["is_anomaly"].sum())), border=True)
        st.metric("Kapasitas terpakai", f"{fmt_kg(last['used_cap_kg'])} / {fmt_kg(last['usable_cap_kg'])}", border=True)

    band = alt.Chart(pd.DataFrame({"y": [settings.tomato_safe_temp_min_c], "y2": [settings.tomato_safe_temp_max_c]})).mark_rect(
        color="#10B981", opacity=0.10).encode(y="y:Q", y2="y2:Q")
    line = alt.Chart(z).mark_line(color="#0F766E").encode(
        x=alt.X("ts:T", title=None), y=alt.Y("temp_c:Q", title="°C", scale=alt.Scale(zero=False)),
        tooltip=[alt.Tooltip("ts:T", title="Waktu"), alt.Tooltip("temp_c:Q", title="Suhu")])
    pts = alt.Chart(z[z["is_anomaly"] == 1]).mark_point(color="#DC2626", size=70, filled=True).encode(
        x="ts:T", y="temp_c:Q", tooltip=[alt.Tooltip("ts:T", title="Waktu"), alt.Tooltip("temp_c:Q", title="Suhu"),
                                         alt.Tooltip("event_note:N", title="Catatan")])
    with st.container(border=True):
        st.altair_chart(band + line + pts, width="stretch")

    ui.section("Perkiraan waktu tempuh", "Estimasi lama perjalanan berdasarkan jarak, lalu lintas, dan cuaca.")
    left, right = st.columns([1, 1])
    with left, st.form("cc_eta", border=True):
        dist = st.number_input("Jarak (km)", 5.0, 150.0, 48.0, 1.0)
        c1, c2, c3 = st.columns(3)
        traf = c1.selectbox("Lalu lintas", list(TRAFFIC), index=1, format_func=TRAFFIC.get)
        stops = c2.number_input("Jumlah singgah", 1, 6, 2)
        weather = c3.selectbox("Cuaca", [0, 1, 2], format_func={0: "Cerah", 1: "Hujan", 2: "Hujan lebat"}.get)
        go_eta = st.form_submit_button("Hitung", type="primary", icon=":material/schedule:")
    with right:
        if go_eta:
            st.session_state["cc_eta_res"] = core.api_call("POST", "/api/v1/coldchain/eta", token=core.token(), json={
                "distance_km": dist, "traffic_level": traf, "num_stops": int(stops), "weather_severity": weather})
        if "cc_eta_res" in st.session_state:
            ok, res = st.session_state["cc_eta_res"]
            if ok:
                e = res["eta"]
                with st.container(border=True):
                    st.metric("Perkiraan waktu tempuh", f"{e['predicted_duration_min']:.0f} menit")
                    st.caption(f"Rentang: {e['error_band_min'][0]:.0f}–{e['error_band_min'][1]:.0f} menit")
            else:
                st.error(res)


# ===========================================================================
# SuperMart
# ===========================================================================
@st.dialog("Buat pesanan pembelian")
def _po_dialog() -> None:
    st.caption("Grade C tidak diterima. Porsi pengganti Grade B maksimal 30%.")
    with st.form("sm_po"):
        c1, c2 = st.columns(2)
        po_id = c1.text_input("No. pesanan", "PO-SM-002")
        lot = c2.text_input("Lot", "H001")
        grade = c1.selectbox("Grade", ["A", "B", "C"])
        qty = c2.number_input("Volume (kg)", 100.0, 5000.0, 1200.0, 100.0)
        price = c1.number_input("Harga sepakat (Rp/kg)", 3000.0, 15000.0, 10000.0, 100.0)
        sub = c2.number_input("Porsi pengganti Grade B (%)", 0.0, 50.0, 0.0, 5.0)
        if st.form_submit_button("Kirim pesanan", type="primary"):
            ok, res = core.api_call("POST", "/api/v1/supermart/po", token=core.token(), json={
                "po_id": po_id, "lot_id": lot, "grade": grade, "qty_kg": qty, "agreed_price_rp": price, "grade_b_sub_pct": sub})
            if ok:
                st.session_state["_toast"] = (f"Pesanan {po_id} tersimpan.", ":material/check_circle:")
                st.rerun()
            st.error(res)


def supermart_demand() -> None:
    state = ui.require_cycle()
    trig = state["trigger_mode"]
    ok, f7 = core.api_read("GET", "/api/v1/supermart/forecast-7d",
                           params={"demand_surge": trig in ("DEMAND_SURGE", "COMPOUND"),
                                   "early_harvest_signal": trig == "EXTREME_RAIN"},
                           spinner="Memuat perkiraan permintaan…")
    if not ok:
        st.error(f7, icon=":material/error:")
        return
    rows = f7["horizon_7d"]
    fp = f7["flash_promo_absorption"]
    ceiling = f7.get("ceiling_price_grade_a_rp")

    with st.container(horizontal=True):
        st.metric("Permintaan 7 hari", fmt_kg(sum(r["forecast_demand_kg"] for r in rows)), border=True)
        st.metric("Saran total pesanan", fmt_kg(sum(r["recommended_po_kg"] for r in rows)), border=True,
                  help="Dihitung agar stok cukup tanpa risiko busuk berlebih (model newsvendor).")
        st.metric("Promo kilat", f"+{fmt_kg(fp['extra_absorption_cap_kg'])}" if fp["enabled"] else "Tidak aktif", border=True)
        if _locked(ceiling):
            st.metric("Harga maksimum Grade A", "Tersembunyi", border=True, help=LOCK_HELP)
        else:
            st.metric("Harga maksimum Grade A", f"{fmt_rp(ceiling)}/kg", border=True,
                      help="Batas harga beli internal SuperMart. Tidak dibagikan ke mitra.")

    with st.container(border=True):
        st.markdown("**Perkiraan permintaan 7 hari ke depan**")
        ui.demand_chart(rows)

    with st.container(horizontal=True, vertical_alignment="center"):
        st.subheader("Pesanan pembelian")
        if core.is_owner("supermart"):
            if st.button("Buat pesanan", icon=":material/add:", type="primary"):
                _po_dialog()
    ok, po = core.api_call("GET", "/api/v1/supermart/po", token=core.token())
    if ok:
        st.dataframe(pd.DataFrame(po["purchase_orders"]).rename(columns={
            "po_id": "No. pesanan", "lot_id": "Lot", "grade": "Grade", "qty_kg": "Volume (kg)",
            "agreed_price_rp": "Harga (Rp/kg)", "branch": "Cabang", "receiving_window": "Jam terima",
            "grade_b_sub_pct": "Pengganti Grade B (%)", "status": "Status"}), hide_index=True)
    else:
        st.error(po)


def supermart_receiving() -> None:
    state = ui.require_cycle()
    ui.section("Penerimaan barang siklus ini", "Barang wajib tiba sebelum batas waktu dengan suhu 7–12 °C.")
    sla = state.get("goods_receipt_sla", [])
    if sla:
        st.dataframe(pd.DataFrame([{
            "Lot": x["lot_id"], "Suhu saat tiba (°C)": x["delivered_temp_c"],
            "Tiba": core.minutes_to_clock(x["arrival_min"]), "Batas": core.minutes_to_clock(x["deadline_min"]),
            "Hasil": core.SLA_LABELS.get(x["sla_status"], (x["sla_status"], ""))[0],
            "Klaim": fmt_rp(x["sla_penalty_rp"]) if x["sla_penalty_rp"] else "-",
        } for x in sla]), hide_index=True)
    else:
        st.caption("Belum ada penerimaan pada siklus ini.")

    ui.section("Periksa kedatangan", "Masukkan data truk yang tiba untuk menentukan diterima atau ditolak.")
    left, right = st.columns(2)
    with left, st.form("sm_sla", border=True):
        temp = st.number_input("Suhu truk saat tiba (°C)", 2.0, 20.0, 9.4, 0.2)
        c1, c2 = st.columns(2)
        arr = c1.time_input("Jam tiba", value=pd.Timestamp("2026-01-01 09:35").time(), step=300)
        ddl = c2.time_input("Batas tiba", value=pd.Timestamp("2026-01-01 12:20").time(), step=300)
        check = st.form_submit_button("Periksa", type="primary", icon=":material/fact_check:")
    with right:
        if check:
            to_min = lambda t: (t.hour - 8) * 60 + t.minute
            st.session_state["sm_sla_res"] = core.api_call("POST", "/api/v1/supermart/goods-receipt-sla", token=core.token(), json={
                "lot_id": "H001", "delivered_temp_c": temp, "arrival_min": to_min(arr), "deadline_min": to_min(ddl)})
        if "sm_sla_res" in st.session_state:
            ok, res = st.session_state["sm_sla_res"]
            if not ok:
                st.error(res)
            else:
                v = res["sla_verdict"]
                label, color = core.SLA_LABELS.get(v["sla_status"], (v["sla_status"], "gray"))
                box = {"green": st.success, "orange": st.warning, "red": st.error}.get(color, st.info)
                box(f"**{label}**", icon=":material/inventory_2:")
                if v["sla_penalty_rp"]:
                    st.caption(f"Klaim ke ColdChain: {fmt_rp(v['sla_penalty_rp'])}")
                st.caption(core.id_text(v["action_note"]))


# ===========================================================================
# Control Center: all partner work pages behind one menu entry
# ===========================================================================
ENTERPRISE_PAGES = {
    "agrofarm": [(agrofarm_fields, "Lahan & panen", "lahan"), (agrofarm_signals, "Masukan mitra", "masukan")],
    "koperasi": [(koperasi_pricing, "Harga & penawaran", "harga")],
    "freshfood": [(freshfood_quality, "Kontrol mutu", "mutu"), (freshfood_schedule, "Jadwal produksi", "produksi")],
    "coldchain": [(coldchain_routes, "Rute pengiriman", "rute"), (coldchain_fleet, "Armada & pengiriman", "armada"),
                  (coldchain_temperature, "Suhu & waktu tempuh", "suhu")],
    "supermart": [(supermart_demand, "Permintaan & pesanan", "permintaan"),
                  (supermart_receiving, "Penerimaan barang", "penerimaan")],
}


def _keep(state_key: str, widget_key: str) -> None:
    st.session_state[state_key] = st.session_state[widget_key]


def partner_workspace() -> None:
    """One page for the Control Center to open any partner's work pages.

    Selections live in their own session keys (widget state resets on page switches), so
    "Lihat detail" links from the overview can preselect a partner and page.
    """
    ss = st.session_state
    ss.setdefault("mitra_ent", "agrofarm")
    ss.setdefault("mitra_sub", {})
    ss["_w_mitra_ent"] = ss["mitra_ent"]
    st.segmented_control("Mitra", core.ENTERPRISES, required=True, key="_w_mitra_ent",
                         format_func=lambda e: ui.ENTERPRISE_NAMES[e][0],
                         on_change=_keep, args=("mitra_ent", "_w_mitra_ent"))
    ent = ss["mitra_ent"]
    pages = ENTERPRISE_PAGES[ent]
    paths = [p for _, _, p in pages]
    sub = ss["mitra_sub"].get(ent) if ss["mitra_sub"].get(ent) in paths else paths[0]
    if len(pages) > 1:
        ss["_w_mitra_sub"] = sub

        def _keep_sub() -> None:
            ss["mitra_sub"][ent] = ss["_w_mitra_sub"]

        st.segmented_control("Halaman", paths, required=True, key="_w_mitra_sub", on_change=_keep_sub,
                             format_func=lambda p: next(t for _, t, q in pages if q == p))
        sub = ss["mitra_sub"].get(ent, sub) if ss["mitra_sub"].get(ent) in paths else sub
    fn, title, path = next(x for x in pages if x[2] == sub)
    st.subheader(f"{ui.ENTERPRISE_NAMES[ent][0]} · {title}")
    ui.model_tags(path)
    fn()
