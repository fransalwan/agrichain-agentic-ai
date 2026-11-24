"""Pages shared across roles: overview, approvals, data, and activity/audit."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

import altair as alt
import pandas as pd
import streamlit as st

from src.portal import components as ui
from src.portal import core
from src.portal.core import fmt_kg, fmt_num, fmt_pct, fmt_rp_short


def _delta(cur: float, base: Dict[str, Any] | None, key: str, fmt=None) -> str | None:
    """Delta text that always starts with its sign, so st.metric picks the right arrow."""
    if not base:
        return None
    diff = cur - base["global_kpis"][key]
    if abs(diff) < 1e-9:
        return None
    sign = "+" if diff > 0 else "-"
    return sign + (fmt(abs(diff)) if fmt else fmt_num(abs(diff), 2))


# ---------------------------------------------------------------------------
# Global overview
# ---------------------------------------------------------------------------
def global_overview() -> None:
    state = ui.require_cycle()
    base = core.get_baseline()
    k = state["global_kpis"]

    if state["hitl_status"] == "PENDING_APPROVAL":
        with st.container(border=True, horizontal=True, vertical_alignment="center"):
            with st.container():
                st.markdown(":orange[:material/pending_actions:] **1 keputusan menunggu persetujuan Anda**")
                st.caption(" · ".join(core.humanize_reason(r) for r in state["hitl_reasons"]))
            ui.go_to("approvals", "Tinjau sekarang", primary=True)

    st.caption("Dibandingkan dengan rencana tanpa penyesuaian otomatis oleh agen.")
    with st.container(horizontal=True):
        st.metric("Susut pangan", fmt_pct(k["food_loss_rate_pct"], 2),
                  _delta(k["food_loss_rate_pct"], base, "food_loss_rate_pct", fmt=lambda d: f"{fmt_num(d, 2)} poin"),
                  delta_color="inverse", border=True,
                  help="Persentase tomat yang terbuang atau tidak terserap. Semakin kecil semakin baik.")
        st.metric("Pesanan terpenuhi", fmt_pct(k["order_fulfillment_rate_pct"]),
                  _delta(k["order_fulfillment_rate_pct"], base, "order_fulfillment_rate_pct", fmt=lambda d: f"{fmt_num(d, 1)} poin"),
                  border=True, help="Porsi permintaan SuperMart yang bisa dipenuhi.")
        st.metric("Laba bersih ekosistem", fmt_rp_short(k["net_ecosystem_profit_rp"]),
                  _delta(k["net_ecosystem_profit_rp"], base, "net_ecosystem_profit_rp", fmt=fmt_rp_short),
                  border=True, help="Total pendapatan dikurangi total biaya kelima mitra.")
        st.metric("Biaya rantai pasok", fmt_rp_short(k["total_supply_chain_cost_rp"]),
                  _delta(k["total_supply_chain_cost_rp"], base, "total_supply_chain_cost_rp", fmt=fmt_rp_short),
                  delta_color="inverse", border=True)
        st.metric("Pemerataan keuntungan", fmt_num(k["jains_fairness_index"], 2),
                  _delta(k["jains_fairness_index"], base, "jains_fairness_index"),
                  border=True, help="Indeks 0–1 (Jain's fairness). Mendekati 1 berarti keuntungan terbagi merata antar mitra.")

    ui.section("Status mitra", "Urutan mengikuti alur tomat dari kebun hingga rak toko.")
    ui.partner_strip(state)

    left, right = st.columns(2)
    with left, st.container(border=True):
        st.markdown("**Ke mana tomat dialokasikan**")
        st.caption(f"Total pasokan {fmt_kg(state['milp_result']['total_supply_kg'])}")
        ui.allocation_chart(state)
    with right, st.container(border=True):
        st.markdown("**Keuntungan per mitra**")
        st.caption("Siklus perencanaan saat ini")
        prof = pd.DataFrame({"Mitra": list(state["enterprise_profits_rp"].keys()),
                             "Rp juta": [v / 1e6 for v in state["enterprise_profits_rp"].values()]})
        chart = alt.Chart(prof).mark_bar(cornerRadiusEnd=4, color="#2563EB").encode(
            x=alt.X("Rp juta:Q", title="Rp juta"),
            y=alt.Y("Mitra:N", sort="-x", title=None, axis=alt.Axis(labelLimit=220)),
            tooltip=["Mitra", alt.Tooltip("Rp juta:Q", format=",.2f")],
        ).properties(height=alt.Step(34))
        st.altair_chart(chart, width="stretch")

    with st.expander("Ringkasan siklus", icon=":material/summarize:"):
        st.write(core.plain_briefing(state))
        st.caption(f"Siklus {state['cycle_id']} · diperbarui {core.fmt_time(state['_synced_at'])}")


# ---------------------------------------------------------------------------
# Enterprise overview (one per partner role)
# ---------------------------------------------------------------------------
def _enterprise_kpis(ent: str, state: Dict[str, Any]) -> None:
    k = state["global_kpis"]
    milp = state["milp_result"]
    profit_key = {"agrofarm": "AgroFarm", "koperasi": "Koperasi Tani", "freshfood": "FreshFood Processing",
                  "coldchain": "ColdChain Logistics", "supermart": "SuperMart"}[ent]
    profit = state["enterprise_profits_rp"].get(profit_key, 0)
    with st.container(horizontal=True):
        if ent == "agrofarm":
            blocks = state.get("agrofarm_monitoring", [])
            flagged = sum(1 for b in blocks if b.get("status") != "NORMAL")
            fb = state.get("freshfood_qc_feedback", {}).get("feedback_to_agrofarm", [])
            st.metric("Total pasokan panen", fmt_kg(milp["total_supply_kg"]), border=True)
            st.metric("Blok perlu dicek", f"{flagged} dari {len(blocks)}", border=True,
                      help="Blok dengan NDVI di bawah batas normal 14 hari atau curah hujan > 90 mm.")
            st.metric("Catatan mutu dari FreshFood", str(len(fb)), border=True)
        elif ent == "koperasi":
            st.metric("Volume diperdagangkan", fmt_kg(milp["total_supply_kg"]), border=True)
            st.metric("Putaran negosiasi", f"{k['negotiation_rounds_used']} dari 3", border=True)
            st.metric("Negosiasi berhasil", fmt_pct(k["negotiation_success_rate_pct"], 0), border=True)
        elif ent == "freshfood":
            sched = state.get("freshfood_qc_feedback", {}).get("fefo_line_schedule", {})
            st.metric("Volume diproses", fmt_kg(milp.get("freshfood_used_kg", 0)), border=True)
            st.metric("Utilisasi lini produksi", fmt_pct(sched.get("capacity_utilization_pct", 0), 0), border=True)
            st.metric("Shift lembur", "Aktif" if k.get("overtime_activated") else "Tidak aktif", border=True)
        elif ent == "coldchain":
            vr = state.get("vrptw_plan", {})
            st.metric("Kapasitas gudang dingin", fmt_kg(state["cold_storage_cap_kg"]),
                      f"-{fmt_num(state['capacity_drop_pct'], 0)}%" if state["capacity_drop_pct"] else None,
                      delta_color="inverse", border=True)
            st.metric("Total jarak rute", f"{fmt_num(vr.get('optimized_distance_km', 0))} km",
                      f"-{fmt_num(vr.get('distance_reduction_pct', 0), 0)}% dari rute biasa", delta_color="inverse",
                      border=True)
            st.metric("Pengiriman terlambat", str(vr.get("time_window_violations", 0)), border=True)
        elif ent == "supermart":
            sla = state.get("goods_receipt_sla", [])
            ok = sum(1 for x in sla if x.get("sla_status") == "ACCEPTED_ON_TIME")
            st.metric("Pesanan terpenuhi", fmt_pct(k["order_fulfillment_rate_pct"]), border=True)
            st.metric("Volume diterima", fmt_kg(milp.get("supermart_fulfilled_kg", 0)), border=True)
            st.metric("Diterima tepat waktu", f"{ok} dari {len(sla)}", border=True)
        st.metric("Keuntungan siklus ini", fmt_rp_short(profit), border=True)


def _enterprise_attention(ent: str, state: Dict[str, Any]) -> List[Tuple[str, str]]:
    level, text = core.enterprise_health(state)[ent]
    items: List[Tuple[str, str]] = []
    if level != "ok":
        items.append((level, text))
    if ent == "agrofarm":
        for b in state.get("agrofarm_monitoring", []):
            if b.get("status") != "NORMAL" and b.get("causes"):
                items.append(("warn", f"**{b['block_id']}**: {'; '.join(b['causes'])}"))
        for f in state.get("freshfood_qc_feedback", {}).get("feedback_to_agrofarm", []):
            items.append(("info", f"Masukan FreshFood untuk **{f['block_id']}**: {f['recommendation']}"))
    elif ent == "freshfood":
        for v in state.get("freshfood_qc_feedback", {}).get("waste_valorization_plan", []):
            items.append(("alert", f"Lot **{v.get('lot_id', '-')}** ({fmt_kg(v.get('blocked_qty_kg', 0))}) diblokir "
                                   "dan dialihkan ke kompos/biogas"))
    elif ent == "supermart":
        fp = state.get("supermart_horizon_7d", {}).get("flash_promo_absorption", {})
        if fp.get("enabled"):
            items.append(("info", f"Promo kilat bisa menyerap tambahan {fmt_kg(fp['extra_absorption_cap_kg'])} Grade A."))
        for x in state.get("goods_receipt_sla", []):
            if x.get("sla_status") != "ACCEPTED_ON_TIME":
                items.append(("alert", x.get("action_note", "")))
    elif ent == "coldchain":
        synced = state.get("vrptw_plan", {}).get("dock_windows_synced_nodes", [])
        if synced:
            items.append(("info", f"Jadwal bongkar mitra sudah disinkronkan ke rute: {', '.join(synced)}"))
    return items


def enterprise_overview(ent: str) -> None:
    state = ui.require_cycle()
    ui.hitl_notice(state)
    _enterprise_kpis(ent, state)

    ui.section("Perlu perhatian", icon=":material/notifications:")
    ui.attention_list(_enterprise_attention(ent, state))

    ui.section("Status mitra", "Posisi Anda dalam rantai pasok tomat.")
    ui.partner_strip(state, highlight=ent)

    with st.expander("Ringkasan siklus", icon=":material/summarize:"):
        st.write(core.plain_briefing(state))
        st.caption(f"Siklus {state['cycle_id']} · diperbarui {core.fmt_time(state['_synced_at'])}")


# ---------------------------------------------------------------------------
# Approvals (global operator only)
# ---------------------------------------------------------------------------
@st.dialog("Konfirmasi keputusan", width="small")
def _confirm_decision(action: str, cycle_id: str, note: str) -> None:
    verb = "menyetujui" if action == "approve" else "menolak"
    st.write(f"Anda akan **{verb}** rencana siklus `{cycle_id}`. Keputusan ini dicatat permanen di log audit.")
    if note:
        st.caption(f"Catatan: {note}")
    with st.container(horizontal=True, horizontal_alignment="right"):
        if st.button("Batal"):
            st.rerun()
        if st.button("Ya, setujui" if action == "approve" else "Ya, tolak", type="primary"):
            ok, res = core.api_call("POST", f"/api/v1/orchestrator/hitl/{cycle_id}/{action}", token=core.token(),
                                    params={"operator_name": core.role()["email"], "note": note})
            if ok:
                state = st.session_state["cycles"][st.session_state["scenario"]]
                state["hitl_status"] = res["hitl_status"]
                st.session_state["_toast"] = ("Rencana disetujui." if action == "approve" else "Rencana ditolak.",
                                              ":material/check_circle:" if action == "approve" else ":material/cancel:")
                st.rerun()
            else:
                st.error(res)


def approvals() -> None:
    state = ui.require_cycle()
    status = state["hitl_status"]

    if status != "PENDING_APPROVAL":
        with st.container(border=True):
            st.markdown(":green[:material/task_alt:] **Tidak ada keputusan yang menunggu persetujuan.**")
            st.caption(f"Status rencana siklus {state['cycle_id']}:")
            ui.status_badge(status)
    else:
        base = core.get_baseline()
        k = state["global_kpis"]
        with st.container(border=True):
            with st.container(horizontal=True, vertical_alignment="center"):
                st.markdown(f"**Rencana penyesuaian · siklus `{state['cycle_id']}`**")
                ui.status_badge(status)
            st.caption(core.SCENARIOS[state["trigger_mode"]][1])
            st.markdown("**Mengapa perlu persetujuan manusia**")
            for r in state["hitl_reasons"]:
                st.markdown(f"- {core.humanize_reason(r)}")

        left, right = st.columns([1.1, 1])
        with left, st.container(border=True):
            st.markdown("**Dampak jika disetujui**")
            if base:
                bk = base["global_kpis"]
                vr, bvr = state.get("vrptw_plan", {}), base.get("vrptw_plan", {})
                rows = [
                    ("Susut pangan", fmt_pct(bk["food_loss_rate_pct"], 2), fmt_pct(k["food_loss_rate_pct"], 2)),
                    ("Pesanan terpenuhi", fmt_pct(bk["order_fulfillment_rate_pct"]), fmt_pct(k["order_fulfillment_rate_pct"])),
                    ("Laba bersih ekosistem", fmt_rp_short(bk["net_ecosystem_profit_rp"]), fmt_rp_short(k["net_ecosystem_profit_rp"])),
                    ("Biaya rantai pasok", fmt_rp_short(bk["total_supply_chain_cost_rp"]), fmt_rp_short(k["total_supply_chain_cost_rp"])),
                    ("Jarak rute pengiriman", f"{fmt_num(bvr.get('optimized_distance_km', 0))} km", f"{fmt_num(vr.get('optimized_distance_km', 0))} km"),
                    ("Shift lembur FreshFood", "Ya" if bk.get("overtime_activated") else "Tidak", "Ya" if k.get("overtime_activated") else "Tidak"),
                    ("Gudang mitra (3PL)", "Ya" if bk.get("third_pl_activated") else "Tidak", "Ya" if k.get("third_pl_activated") else "Tidak"),
                ]
                st.dataframe(pd.DataFrame(rows, columns=["Indikator", "Tanpa penyesuaian", "Dengan penyesuaian"]),
                             hide_index=True)
            else:
                st.caption("Perbandingan belum tersedia.")
        with right, st.container(border=True):
            st.markdown("**Perubahan alokasi tomat**")
            if base:
                ui.comparison_chart(base, state)

        with st.container(border=True):
            st.markdown("**Keputusan Anda**")
            note = st.text_area("Catatan untuk log audit", placeholder="Contoh: Disetujui, suhu armada sudah dicek 7–12 °C.",
                                height=80)
            with st.container(horizontal=True):
                if st.button("Setujui rencana", type="primary", icon=":material/check:"):
                    _confirm_decision("approve", state["cycle_id"], note)
                if st.button("Tolak", icon=":material/close:"):
                    _confirm_decision("reject", state["cycle_id"], note)

    ui.section("Riwayat keputusan", icon=":material/history:")
    ok, aud = core.api_call("GET", "/api/v1/audit/trail", token=core.token(), params={"limit": 200})
    if ok:
        rows = [
            {
                "Waktu": core.fmt_time(e["timestamp"]),
                "Keputusan": {"HITL_MANUAL_APPROVAL": "Disetujui", "HITL_MANUAL_REJECTION": "Ditolak"}[e["event_type"]],
                "Oleh": e["actor"],
                "Siklus": e["details"].get("cycle_id", "-"),
                "Catatan": e["details"].get("note", ""),
            }
            for e in aud["entries"] if e["event_type"] in ("HITL_MANUAL_APPROVAL", "HITL_MANUAL_REJECTION")
        ]
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True)
        else:
            st.caption("Belum ada keputusan manual yang tercatat.")
    else:
        st.caption(aud)


# ---------------------------------------------------------------------------
# Data explorer
# ---------------------------------------------------------------------------
DATA_CATALOG = [
    ("agrofarm", "active_harvest_lots", "Lot panen aktif"),
    ("agrofarm", "farm_harvest_history", "Riwayat panen"),
    ("agrofarm", "private_costs", "Biaya produksi (rahasia)"),
    ("koperasi", "market_price_negotiations", "Riwayat negosiasi harga"),
    ("freshfood", "qc_docs", "Dokumen kontrol mutu"),
    ("coldchain", "cold_storage_telemetry", "Telemetri gudang dingin"),
    ("coldchain", "fleet_delivery_routes", "Riwayat rute armada"),
    ("supermart", "retail_pos_sales", "Penjualan ritel"),
]


def data_page() -> None:
    mine = core.role_key()
    catalog = sorted(DATA_CATALOG, key=lambda x: (x[0] != mine,))
    st.caption("Data diambil melalui server. Kolom rahasia milik mitra lain otomatis disembunyikan sesuai hak akses Anda.")

    with st.container(horizontal=True, vertical_alignment="bottom"):
        sel = st.selectbox("Tabel", catalog, format_func=lambda x: f"{ui.ENTERPRISE_NAMES[x[0]][0]} — {x[2]}",
                           width=420)
        q = st.text_input("Cari", placeholder="Lot, blok, grade…", width=260)
        limit = st.selectbox("Tampilkan", [25, 50, 100, 300], index=1, width=120)

    ent, table, label = sel
    ok, data = core.api_call("GET", f"/api/v1/data-explorer/{ent}/{table}", token=core.token(),
                             params={"search": q, "limit": limit})
    if not ok:
        st.error(data, icon=":material/error:")
        return

    redacted = data["redacted_columns"]
    with st.container(horizontal=True, vertical_alignment="center"):
        st.caption(f"Menampilkan {fmt_num(len(data['records']))} dari {fmt_num(data['matched_rows'])} baris yang cocok "
                   f"(total {fmt_num(data['total_rows'])}).")
        if redacted:
            st.badge(f"{len(redacted)} kolom disembunyikan", color="orange", icon=":material/lock:",
                     help=f"Kolom rahasia: {', '.join(redacted)}. Hanya pemilik data yang dapat melihatnya.")
        else:
            st.badge("Akses penuh", color="green", icon=":material/lock_open:")

    df = pd.DataFrame(data["records"])
    if df.empty:
        st.info("Tidak ada data yang cocok dengan pencarian Anda.", icon=":material/search_off:")
        return
    st.dataframe(df, hide_index=True)
    st.download_button("Unduh CSV", df.to_csv(index=False).encode("utf-8"), file_name=f"{ent}_{table}.csv",
                       mime="text/csv", icon=":material/download:")


# ---------------------------------------------------------------------------
# Activity & audit
# ---------------------------------------------------------------------------
STEP_LABELS = {
    "collect_telemetry": "Mengumpulkan data dari 5 mitra",
    "run_milp": "Menghitung alokasi optimal",
    "validate_local_policy": "Memeriksa kebijakan harga koperasi",
    "negotiation_loop": "Negosiasi antar-agen",
    "risk_hitl_gate": "Menilai risiko keputusan",
    "escalate_hitl": "Meminta persetujuan manusia",
    "commit_and_audit": "Menetapkan rencana & mencatat audit",
}
STEP_OK = {"COMPLETED", "ACCEPTED", "AGREED", "AUTO_PASS", "COMMITTED", "SKIPPED", "HUMAN_APPROVED", "AUTO_APPROVED"}


def _step_label(node: str) -> str:
    base, _, suffix = node.partition(" ")
    label = STEP_LABELS.get(base, node)
    return f"{label} {suffix.strip('()')}".strip() if suffix else label

EVENT_LABELS = {
    "COMMIT_PLAN": "Rencana ditetapkan",
    "HITL_ESCALATION": "Diteruskan ke persetujuan manusia",
    "HITL_MANUAL_APPROVAL": "Disetujui manusia",
    "HITL_MANUAL_REJECTION": "Ditolak manusia",
    "COLLECT_TELEMETRY": "Pengumpulan data",
    "NEGOTIATION_ROUND": "Putaran negosiasi",
    "DISRUPTION_ALERT": "Peringatan gangguan",
    "FRESHFOOD_QC_INSPECTION": "Inspeksi mutu",
    "GOODS_RECEIPT_SLA_CHECK": "Pemeriksaan penerimaan barang",
    "CREATE_PO": "Pesanan pembelian dibuat",
    "UPDATE_PO": "Pesanan pembelian diubah",
    "CREATE_VEHICLE": "Kendaraan ditambahkan",
    "UPDATE_VEHICLE": "Kendaraan diperbarui",
    "CREATE_SHIPMENT": "Permintaan kirim dibuat",
}


def activity_page() -> None:
    state = ui.require_cycle()
    tabs = st.tabs(["Jejak keputusan", "Log audit", "Status agen AI", "Pesan antar-agen"])

    with tabs[0]:
        st.caption(f"Langkah yang dijalankan agen untuk siklus {state['cycle_id']}.")
        for step in state.get("decision_trace", []):
            icon = ":green[:material/check_circle:]" if step["status"] in STEP_OK else ":orange[:material/warning:]"
            with st.container(border=True):
                st.markdown(f"{icon} **{step['step']}. {_step_label(step['node'])}**")
                st.caption(f"{step['actors']} · {core.fmt_time(step['timestamp'])}")
                st.write(step["summary"])
        if state.get("lineage"):
            with st.expander("Ketertelusuran lot (dari kebun ke toko)", icon=":material/timeline:"):
                lin = pd.DataFrame(state["lineage"]).rename(columns={
                    "block_id": "Blok", "lot_id": "Lot", "grade": "Grade", "qc_doc_id": "Dokumen QC",
                    "shipment_id": "Pengiriman", "trip_id": "Perjalanan", "vehicle_id": "Kendaraan",
                    "destination_channel": "Tujuan", "qty_kg": "Volume (kg)", "po_ref": "Ref. PO"})
                st.dataframe(lin, hide_index=True)

    with tabs[1]:
        ok, aud = core.api_call("GET", "/api/v1/audit/trail", token=core.token(), params={"limit": 50})
        if not ok:
            st.error(aud)
        else:
            if aud["chain_valid"]:
                st.badge("Rantai audit utuh (SHA-256 terverifikasi)", color="green", icon=":material/verified:")
            else:
                st.badge("Rantai audit rusak — ada perubahan tidak sah", color="red", icon=":material/gpp_bad:")
            st.dataframe(pd.DataFrame([
                {"Waktu": core.fmt_time(e["timestamp"]),
                 "Kejadian": EVENT_LABELS.get(e["event_type"], e["event_type"]),
                 "Pelaku": e["actor"],
                 "Detail": json.dumps(e["details"], ensure_ascii=False),
                 "Hash": e["hash"][:12] + "…"}
                for e in aud["entries"]
            ]), hide_index=True)

    with tabs[2]:
        agents = pd.DataFrame(state.get("agent_statuses", []))
        if not agents.empty:
            view = agents.rename(columns={
                "agent_id": "Agen", "enterprise": "Mitra", "domain_model": "Model", "llm_model": "Model bahasa",
                "calls": "Panggilan", "avg_latency_ms": "Latensi (ms)", "cost_usd": "Biaya (USD)",
                "privacy_firewall": "Perlindungan data", "last_action": "Aksi terakhir"})
            st.dataframe(view[["Agen", "Mitra", "Model", "Model bahasa", "Panggilan", "Latensi (ms)", "Biaya (USD)",
                               "Perlindungan data", "Aksi terakhir"]], hide_index=True)

    with tabs[3]:
        st.caption("Pesan teknis yang dipertukarkan agen (FIPA-ACL / GS1 EPCIS). Untuk keperluan audit teknis.")
        msgs = state.get("messages", [])
        if msgs:
            st.dataframe(pd.DataFrame([
                {"Waktu": core.fmt_time(m["timestamp"]), "Dari": m["sender"], "Ke": m["receiver"],
                 "Jenis": m["performative"], "Protokol": m["protocol"], "Putaran": m["negotiation_round"]}
                for m in msgs
            ]), hide_index=True)
            idx = st.selectbox("Lihat isi pesan", range(len(msgs)),
                               format_func=lambda i: f"#{i + 1} {msgs[i]['sender']} → {msgs[i]['receiver']} ({msgs[i]['performative']})")
            st.json({"payload": msgs[idx]["payload"], "epcis_event": msgs[idx].get("epcis_event")}, expanded=False)
