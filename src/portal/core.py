"""Shared data layer for the stakeholder portal.

Everything that talks to the FastAPI gateway, keeps per-user session state, or turns
internal status codes into plain Indonesian lives here, so page code stays readable.
"""
from __future__ import annotations

import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx
import streamlit as st

from config.settings import settings

# ---------------------------------------------------------------------------
# Roles (demo accounts — tokens are verified server-side by FastAPI)
# ---------------------------------------------------------------------------
ROLES: Dict[str, Dict[str, str]] = {
    "global": {
        "title": "Operator pusat kendali",
        "org": "AgriChain Control Center",
        "person": "Operator Global",
        "email": "ops.global@agrichain.id",
        "token": "tok_orchestrator_global_scope_v1",
        "icon": ":material/hub:",
        "summary": "Memantau seluruh rantai pasok dan menyetujui keputusan penting.",
    },
    "agrofarm": {
        "title": "Manajer kebun",
        "org": "AgroFarm",
        "person": "Farm Manager",
        "email": "farm.manager@agrofarm.co.id",
        "token": "tok_agrofarm_local_v1",
        "icon": ":material/agriculture:",
        "summary": "Memantau kondisi lahan dan perkiraan hasil panen.",
    },
    "koperasi": {
        "title": "Manajer koperasi",
        "org": "Koperasi Tani",
        "person": "Cooperative Manager",
        "email": "coop.manager@koperasitani.id",
        "token": "tok_koperasi_local_v1",
        "icon": ":material/handshake:",
        "summary": "Menetapkan harga jual dan menilai penawaran pembeli.",
    },
    "freshfood": {
        "title": "Manajer mutu & produksi",
        "org": "FreshFood Processing",
        "person": "QC & Production Manager",
        "email": "qc.prod@freshfood.co.id",
        "token": "tok_freshfood_local_v1",
        "icon": ":material/factory:",
        "summary": "Memeriksa mutu tomat dan mengatur jadwal produksi.",
    },
    "coldchain": {
        "title": "Manajer armada",
        "org": "ColdChain Logistics",
        "person": "Fleet Manager",
        "email": "fleet.coldchain@coldchain.co.id",
        "token": "tok_coldchain_local_v1",
        "icon": ":material/local_shipping:",
        "summary": "Mengatur rute pengiriman dan menjaga suhu 7–12 °C.",
    },
    "supermart": {
        "title": "Manajer pembelian",
        "org": "SuperMart",
        "person": "Purchasing Manager",
        "email": "purchasing@supermart.co.id",
        "token": "tok_supermart_local_v1",
        "icon": ":material/storefront:",
        "summary": "Memperkirakan permintaan dan mengelola pesanan pembelian.",
    },
}

ENTERPRISES = ["agrofarm", "koperasi", "freshfood", "coldchain", "supermart"]

# ---------------------------------------------------------------------------
# Simulated operating conditions (the orchestrator's trigger modes)
# ---------------------------------------------------------------------------
SCENARIOS: Dict[str, Tuple[str, str]] = {
    "NORMAL": ("Operasi normal", "Tidak ada gangguan. Semua mitra berjalan sesuai rencana harian."),
    "COLD_STORAGE_FAILURE": ("Gudang dingin bermasalah", "Kompresor rusak: kapasitas gudang dingin turun dari 3.000 kg menjadi 1.000 kg."),
    "EXTREME_RAIN": ("Hujan ekstrem di kebun", "Curah hujan 96 mm di blok BLK-11, panen perlu dimajukan 2 hari."),
    "SENSOR_OUTAGE": ("Sensor lahan mati", "Sensor blok BLK-11 offline 3 hari; perkiraan panen memakai data historis."),
    "DEMAND_SURGE": ("Lonjakan permintaan", "Permintaan SuperMart naik dari 2.000 kg menjadi 2.800 kg."),
    "FOOD_SAFETY_FAIL": ("Gagal uji keamanan pangan", "Lot H003 gagal uji mikroba/pestisida dan harus diblokir dari jalur pangan."),
    "COMPOUND": ("Gangguan ganda", "Gudang dingin bermasalah sekaligus lonjakan permintaan SuperMart."),
    "DEADLOCK": ("Negosiasi harga buntu", "Tawaran pembeli di bawah harga minimum selama 3 putaran."),
}

CHANNEL_LABELS = {
    "SuperMart": "SuperMart (ritel)",
    "FreshFood_Reg": "FreshFood – reguler",
    "FreshFood_OT": "FreshFood – lembur",
    "ColdStorage": "Gudang dingin",
    "Partner3PL": "Gudang mitra (3PL)",
    "AltBuyer": "Pembeli alternatif",
}

QC_LABELS = {
    "PH_OUT_OF_SAFE_RANGE": "pH di luar batas aman (4,0–4,6)",
    "PESTICIDE_EXCEEDS_MRL": "Residu pestisida melebihi batas 0,05 ppm",
    "MICROBIAL_CONTAMINATION": "Tidak lolos uji mikroba",
    "DEFECT_RATIO_EXCEEDS_20PCT": "Cacat permukaan lebih dari 20%",
}

SLA_LABELS = {
    "ACCEPTED_ON_TIME": ("Diterima tepat waktu", "green"),
    "ACCEPTED_WITH_DELAY_CLAIM": ("Diterima, terlambat (ada klaim)", "orange"),
    "REJECTED_TEMP_BREACH": ("Ditolak, suhu tidak sesuai", "red"),
}

HITL_STATUS = {
    "PENDING_APPROVAL": ("Menunggu persetujuan", "orange", ":material/pending_actions:"),
    "HUMAN_APPROVED": ("Disetujui", "green", ":material/check_circle:"),
    "HUMAN_REJECTED": ("Ditolak", "red", ":material/cancel:"),
    "AUTO_APPROVED": ("Disetujui otomatis", "green", ":material/check_circle:"),
}


# ---------------------------------------------------------------------------
# Formatting helpers (Indonesian number style)
# ---------------------------------------------------------------------------
def fmt_num(x: float, decimals: int = 0) -> str:
    s = f"{x:,.{decimals}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def fmt_kg(x: float) -> str:
    return f"{fmt_num(x)} kg"


def fmt_rp(x: float) -> str:
    return f"Rp{fmt_num(x)}"


def fmt_rp_short(x: float) -> str:
    if abs(x) >= 1e9:
        return f"Rp{fmt_num(x / 1e9, 2)} M"
    if abs(x) >= 1e6:
        return f"Rp{fmt_num(x / 1e6, 1)} jt"
    return fmt_rp(x)


def fmt_pct(x: float, decimals: int = 1) -> str:
    return f"{fmt_num(x, decimals)}%"


def fmt_time(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%d %b %Y, %H:%M")
    except Exception:
        return iso or "-"


def minutes_to_clock(minutes_from_0800: float) -> str:
    total = 8 * 60 + int(minutes_from_0800)
    return f"{total // 60:02d}:{total % 60:02d}"


# ---------------------------------------------------------------------------
# Plain-language translation of internal codes
# ---------------------------------------------------------------------------
def humanize_reason(code: str) -> str:
    m = re.match(r"CAPACITY_DROP_([\d.]+)%_EXCEEDS_(\d+)%", code)
    if m:
        return f"Kapasitas gudang dingin turun {fmt_num(float(m.group(1)), 1)}% (batas otomatis {m.group(2)}%)"
    m = re.match(r"FLR_([\d.]+)%_EXCEEDS_(\d+)%", code)
    if m:
        return f"Tingkat susut pangan {fmt_num(float(m.group(1)), 1)}% melebihi batas {m.group(2)}%"
    m = re.match(r"SURFACE_DEFECT_(\d+)PCT", code)
    if m:
        return f"Cacat permukaan {m.group(1)}%, di atas normal untuk grade-nya"
    m = re.match(r"GRADE_DOWNGRADE_(\w+)_TO_(\w+)", code)
    if m:
        return f"Kamera menilai Grade {m.group(2)}, lebih rendah dari Grade {m.group(1)} yang dilaporkan"
    known = {
        "RETAIL_GRADE_B_SUBSTITUTION_REQUIRES_APPROVAL": "SuperMart akan menerima tomat Grade B sebagai pengganti (maks. 30%)",
        "NEGOTIATION_DEADLOCK_AFTER_3_ROUNDS": "Negosiasi harga buntu setelah 3 putaran",
        "EXCEEDS_AUTONOMOUS_DEFERRAL_LIMIT": "Penundaan panen melebihi batas keputusan otomatis",
        "FOOD_SAFETY_HARD_BLOCK_TRIGGERED": "Ada lot yang diblokir karena gagal uji keamanan pangan",
        "UNSOLD_INVENTORY_EXCEEDS_5PCT": "Stok yang tidak terserap melebihi 5%",
        "BELOW_MINIMUM_VIABILITY_THRESHOLD": "Harga di bawah batas kelayakan minimum",
        "BELOW_FARMER_VIABILITY_THRESHOLD": "Harga di bawah batas kelayakan petani",
        "AGROFARM_SENSOR_OFFLINE_FALLBACK_ACTIVE": "Sensor lahan mati; perkiraan memakai data historis",
        "AGROFARM_HARVEST_WINDOW_SHIFTED_2_DAYS": "Jadwal panen dimajukan 2 hari",
        "COLD_STORAGE_MITIGATION_NEEDED": "Gudang dingin perlu langkah mitigasi",
        **QC_LABELS,
    }
    return known.get(code, code.replace("_", " ").capitalize())


def channel_label(ch: str) -> str:
    return CHANNEL_LABELS.get(ch, ch)


def id_text(text: str) -> str:
    """Convert English number separators in backend free text to Indonesian (4,500.5 → 4.500,5)."""
    if not isinstance(text, str):
        return text
    return re.sub(r"(?<=\d)([.,])(?=\d)", lambda m: "," if m.group(1) == "." else ".", text)


# ---------------------------------------------------------------------------
# Friendly labels for technical identifiers (activity log, data tables)
# ---------------------------------------------------------------------------
AGENT_NAMES = {
    "AGT-01": "AgroFarm", "AGT-02": "Koperasi Tani", "AGT-03": "FreshFood",
    "AGT-04": "ColdChain", "AGT-05": "SuperMart", "AGT-06": "Pusat Kendali",
}
PERFORMATIVE_LABELS = {
    "CFP": "Permintaan penawaran", "PROPOSE": "Penawaran", "ACCEPT_PROPOSAL": "Penawaran diterima",
    "REJECT_PROPOSAL": "Penawaran ditolak", "COUNTER_PROPOSE": "Tawaran balik", "INFORM": "Kirim data",
    "REQUEST": "Permintaan", "AGREE": "Setuju", "REFUSE": "Menolak",
}
PROTOCOL_LABELS = {"FIPA-CONTRACT-NET": "Lelang (Contract Net)", "A2A-EPCIS-2.0": "Pertukaran data (GS1 EPCIS)"}


def actor_label(actor: str) -> str:
    """'AGT-02:KoperasiTani' / 'AGT-06 (GPT-4o + MILP)' / 'HUMAN_SUPERVISOR' → readable names."""
    if not isinstance(actor, str):
        return actor
    text = re.sub(r"\s*\([^)]*\)", "", actor)
    text = re.sub(r"AGT-0([1-6])(?::\w+)?", lambda m: AGENT_NAMES[f"AGT-0{m.group(1)}"], text)
    text = text.replace("HUMAN_SUPERVISOR", "Supervisor manusia").replace("AltBuyer", "Pembeli alternatif")
    text = text.replace("Audit Trail SHA-256", "log audit")
    return text.replace("..", "–")


COLUMN_LABELS = {
    "lot_id": "Lot", "harvest_date": "Tanggal panen", "plot_id": "Petak", "area_ha": "Luas (ha)",
    "avg_temp_c": "Suhu rata-rata (°C)", "soil_moisture_pct": "Kelembapan tanah (%)", "rainfall_mm": "Curah hujan (mm)",
    "fertilizer_kg_ha": "Pupuk (kg/ha)", "crop_age_days": "Umur tanaman (hari)", "actual_yield_kg": "Hasil panen (kg)",
    "grade": "Grade", "shelf_life_days": "Umur simpan (hari)", "predicted_grade_mix": "Perkiraan campuran grade",
    "production_cost_per_kg": "Biaya produksi (Rp/kg)", "farmer_personal_id": "ID petani", "plot_gps_private": "Koordinat petak",
    "tx_id": "Transaksi", "tx_date": "Tanggal", "season": "Musim", "month": "Bulan",
    "regional_supply_ton": "Pasokan regional (ton)", "qty_kg": "Volume (kg)", "market_ref_price_rp": "Harga acuan pasar (Rp/kg)",
    "floor_price_rp": "Harga minimum (Rp/kg)", "buyer_id": "Pembeli", "initial_bid_rp": "Tawaran awal (Rp/kg)",
    "final_agreed_rp": "Harga sepakat (Rp/kg)", "rounds": "Putaran", "status": "Status",
    "inspection_id": "Inspeksi", "timestamp": "Waktu", "image_index": "No. foto",
    "estimated_shelf_life_days": "Perkiraan umur simpan (hari)", "recommended_route": "Rekomendasi tujuan",
    "visual_metrics.avg_diameter_mm": "Diameter rata-rata (mm)", "visual_metrics.color_ripeness_idx": "Indeks kematangan warna",
    "visual_metrics.surface_defect_ratio": "Rasio cacat permukaan", "visual_metrics.ground_truth_grade": "Grade sebenarnya",
    "food_safety_lab.ph_level": "pH", "food_safety_lab.brix_pct": "Brix (%)",
    "food_safety_lab.pesticide_residue_ppm": "Residu pestisida (ppm)", "food_safety_lab.microbial_pass": "Lolos uji mikroba",
    "food_safety_lab.food_safety_approved": "Lolos keamanan pangan",
    "ts": "Waktu", "facility_id": "Fasilitas", "zone_id": "Zona", "temp_c": "Suhu (°C)", "humidity_pct": "Kelembapan (%)",
    "power_kw": "Daya (kW)", "usable_cap_kg": "Kapasitas pakai (kg)", "used_cap_kg": "Terpakai (kg)",
    "is_anomaly": "Anomali", "event_note": "Catatan",
    "route_id": "Rute", "origin_node": "Asal", "dest_node": "Tujuan", "distance_km": "Jarak (km)",
    "est_duration_min": "Perkiraan durasi (menit)", "truck_id": "Truk", "truck_cap_kg": "Kapasitas truk (kg)",
    "cost_per_km_rp": "Biaya per km (Rp)", "reefer_temp_c": "Suhu reefer (°C)",
    "sales_date": "Tanggal", "store_id": "Toko", "sku_grade": "Grade", "day_of_week": "Hari ke-", "price_rp": "Harga (Rp/kg)",
    "is_promo": "Promo", "is_weekend": "Akhir pekan", "season_flag": "Musim", "opening_stock_kg": "Stok awal (kg)",
    "demand_sold_kg": "Terjual (kg)", "stockout_kg": "Kekurangan stok (kg)", "spoilage_kg": "Busuk (kg)",
}


def column_label(col: str) -> str:
    if col in COLUMN_LABELS:
        return COLUMN_LABELS[col]
    return col.split(".")[-1].replace("_", " ").capitalize()


def _join(items: List[str]) -> str:
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " dan " + items[-1]


_PROPER_NOUNS = ("SuperMart", "FreshFood", "AgroFarm", "Koperasi", "ColdChain", "Lot", "Grade")
_REASON_CLAUSES = {
    "RETAIL_GRADE_B_SUBSTITUTION_REQUIRES_APPROVAL": "SuperMart perlu menerima Grade B sebagai pengganti",
    "AGROFARM_SENSOR_OFFLINE_FALLBACK_ACTIVE": "sensor lahan mati sehingga perkiraan panen memakai data historis",
    "FOOD_SAFETY_HARD_BLOCK_TRIGGERED": "ada lot yang diblokir karena gagal uji keamanan pangan",
}


def _reason_clause(code: str) -> str:
    """An approval reason phrased to follow 'Karena …' mid-sentence."""
    text = _REASON_CLAUSES.get(code) or humanize_reason(code)
    return text if text.startswith(_PROPER_NOUNS) else text[:1].lower() + text[1:]


def plain_briefing(state: Dict[str, Any]) -> str:
    """Plain-language summary of a planning cycle for stakeholders.

    Built from the same cycle data as the backend's technical executive_briefing, but
    without jargon (MILP-FEFO, Jain's index, NIST codes).
    """
    k = state.get("global_kpis", {})
    milp = state.get("milp_result", {})
    supply = float(milp.get("total_supply_kg", 0))
    loss = float(milp.get("total_loss_kg", 0))
    parts: List[str] = []

    if loss < 0.5:
        parts.append(f"Semua {fmt_kg(supply)} tomat sudah dibagi ke mitra tanpa ada yang terbuang.")
    else:
        parts.append(f"{fmt_kg(supply - loss)} dari {fmt_kg(supply)} tomat sudah dibagi ke mitra; "
                     f"{fmt_kg(loss)} ({fmt_pct(k.get('food_loss_rate_pct', 0), 1)}) terbuang atau diblokir.")

    ofr = f"{fmt_pct(k.get('order_fulfillment_rate_pct', 0))} pesanan SuperMart terpenuhi"
    if state.get("allow_grade_b_to_supermart"):
        ofr += ", sebagian dengan tomat Grade B sebagai pengganti (maks. 30%) karena permintaan melonjak"
    parts.append(ofr + ".")

    if k.get("overtime_activated"):
        parts.append("FreshFood menambah shift lembur (+500 kg) agar tidak ada tomat yang terbuang.")
    if k.get("third_pl_activated"):
        parts.append("Sebagian tomat dititipkan ke gudang mitra (3PL).")
    reasons = state.get("hitl_reasons", []) if state.get("hitl_status") == "PENDING_APPROVAL" else []
    drop = float(state.get("capacity_drop_pct") or 0)
    if drop > 0 and not any(r.startswith("CAPACITY_DROP") for r in reasons):
        parts.append(f"Kapasitas gudang dingin turun {fmt_num(drop, 0)}%.")
    for v in state.get("freshfood_qc_feedback", {}).get("waste_valorization_plan", []):
        parts.append(f"Lot {v.get('lot_id')} ({fmt_kg(v.get('blocked_qty_kg', 0))}) gagal uji keamanan pangan "
                     "dan dialihkan ke kompos/biogas.")
    if state.get("data_freshness_warning") and "AGROFARM_SENSOR_OFFLINE_FALLBACK_ACTIVE" not in reasons:
        parts.append("Sebagian data sensor lahan sudah lama, jadi angka panen di blok terkait masih perkiraan kasar.")

    fair = float(k.get("jains_fairness_index", 0))
    spread = "merata" if fair >= 0.9 else ("cukup merata" if fair >= 0.8 else "kurang merata")
    parts.append(f"Keuntungan gabungan kelima mitra {fmt_rp_short(k.get('net_ecosystem_profit_rp', 0))}, "
                 f"dengan pembagian yang {spread} antar-mitra.")

    status = state.get("hitl_status")
    if status == "PENDING_APPROVAL":
        who = "Anda" if st.session_state.get("role") == "global" else "pusat kendali"
        parts.append(f"Karena {_join([_reason_clause(r) for r in reasons])}, rencana ini menunggu persetujuan {who}.")
    elif status == "HUMAN_APPROVED":
        parts.append("Rencana ini sudah disetujui operator.")
    elif status == "HUMAN_REJECTED":
        parts.append("Rencana ini ditolak operator dan akan disusun ulang.")
    else:
        parts.append("Tidak ada risiko yang melewati batas, jadi rencana dijalankan otomatis.")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------
API_BASE = settings.api_base_url.rstrip("/")


def _error_text(r: httpx.Response) -> str:
    try:
        body = r.json()
        detail = body.get("detail", body) if isinstance(body, dict) else body
        return f"{detail}"
    except ValueError:
        return f"Server mengembalikan galat HTTP {r.status_code}."


def api_call(method: str, path: str, *, token: str, json: Optional[dict] = None,
             params: Optional[dict] = None, timeout: float = 60.0) -> Tuple[bool, Any]:
    """Returns (ok, data). On failure `data` is a short, human-readable message."""
    try:
        r = httpx.request(method, f"{API_BASE}{path}", json=json, params=params,
                          headers={"X-Scoped-Token": token}, timeout=timeout)
    except httpx.ConnectError:
        return False, "Layanan API tidak dapat dihubungi. Pastikan server FastAPI berjalan di port 8000."
    except httpx.TimeoutException:
        return False, "Layanan API terlalu lama merespons. Coba lagi sebentar lagi."
    except Exception as exc:  # pragma: no cover - defensive
        return False, str(exc)
    if r.status_code >= 300:
        return False, _error_text(r)
    try:
        return True, r.json()
    except ValueError:
        return False, "Respons server tidak dapat dibaca."


class _ApiError(Exception):
    pass


@st.cache_data(ttl=300, max_entries=200, show_spinner=False)
def _cached_call(method: str, path: str, token: str, json: Optional[dict], params: Optional[dict]) -> Any:
    ok, data = api_call(method, path, token=token, json=json, params=params)
    if not ok:
        raise _ApiError(data)  # errors are not cached
    return data


def api_read(method: str, path: str, *, json: Optional[dict] = None, params: Optional[dict] = None,
             spinner: str = "Memuat data…") -> Tuple[bool, Any]:
    """Cached call for side-effect-free requests (forecasts, route plans, schedules)."""
    try:
        with st.spinner(spinner):
            return True, _cached_call(method, path, token(), json, params)
    except _ApiError as exc:
        return False, str(exc)


@st.cache_data(ttl=15, show_spinner=False)
def api_online() -> bool:
    return _api_healthy()


def _api_healthy() -> bool:
    try:
        return httpx.get(f"{API_BASE}/api/v1/health", timeout=2.5).status_code == 200
    except Exception:
        return False


@st.cache_resource(show_spinner=False)
def ensure_api() -> bool:
    """Start the FastAPI gateway inside this process when none is reachable locally.

    Hosts that run a single Streamlit process (e.g. Streamlit Community Cloud) have no
    separate API server, so the gateway is served from a daemon thread on API_BASE.
    When an API is already running (local development with uvicorn), nothing is started.
    Set AGRICHAIN_EMBED_API=0 to disable.
    """
    if _api_healthy():
        return True
    url = httpx.URL(API_BASE)
    if os.environ.get("AGRICHAIN_EMBED_API", "1") == "0" or url.host not in ("127.0.0.1", "localhost"):
        return False

    import uvicorn

    from src.api.main import app as api_app

    server = uvicorn.Server(uvicorn.Config(api_app, host=url.host, port=url.port or 8000, log_level="warning"))
    threading.Thread(target=server.run, name="agrichain-api", daemon=True).start()
    for _ in range(120):  # models load at startup
        if _api_healthy():
            api_online.clear()
            return True
        time.sleep(0.5)
    return False


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------
def init_session() -> None:
    ss = st.session_state
    ss.setdefault("role", None)
    ss.setdefault("scenario", "NORMAL")
    ss.setdefault("cycles", {})
    ss.setdefault("baselines", {})


def role_key() -> str:
    return st.session_state["role"]


def role() -> Dict[str, str]:
    return ROLES[role_key()]


def token() -> str:
    return role()["token"]


def is_owner(enterprise: str) -> bool:
    return role_key() == enterprise


def clear_cycles() -> None:
    st.session_state["cycles"] = {}
    st.session_state["baselines"] = {}


def _cycle_request(scenario: str, adaptive: bool) -> dict:
    return {
        "trigger_mode": scenario,
        "adaptive_replanning": adaptive,
        "use_milp": True,
        "homogeneous_frontier": False,
        "auto_approve_hitl": not adaptive,
    }


def cycle_loaded() -> bool:
    return st.session_state["scenario"] in st.session_state["cycles"]


def get_cycle() -> Optional[Dict[str, Any]]:
    """Current planning cycle for the selected scenario (run once, then reused).

    The no-replanning baseline (used for "vs tanpa penyesuaian" comparisons on every overview)
    is fetched in parallel.
    """
    scenario = st.session_state["scenario"]
    cycles = st.session_state["cycles"]
    if scenario not in cycles:
        tok = token()
        want_base = scenario not in st.session_state["baselines"]
        with st.spinner("Agen sedang menyusun rencana rantai pasok…"):
            with ThreadPoolExecutor(max_workers=2) as pool:
                fut = pool.submit(api_call, "POST", "/api/v1/orchestrator/run-cycle", token=tok,
                                  json=_cycle_request(scenario, adaptive=True), timeout=240)
                fut_b = pool.submit(api_call, "POST", "/api/v1/orchestrator/run-cycle", token=tok,
                                    json=_cycle_request(scenario, adaptive=False), timeout=240) if want_base else None
                ok, data = fut.result()
                if fut_b is not None:
                    ok_b, base = fut_b.result()
                    if ok_b:
                        st.session_state["baselines"][scenario] = base
        if not ok:
            st.session_state["cycle_error"] = data
            return None
        data["_synced_at"] = datetime.now().isoformat(timespec="seconds")
        cycles[scenario] = data
        st.session_state.pop("cycle_error", None)
    return cycles[scenario]


def get_baseline() -> Optional[Dict[str, Any]]:
    """Same scenario without adaptive replanning, used for 'before vs after' comparisons."""
    scenario = st.session_state["scenario"]
    base = st.session_state["baselines"]
    if scenario not in base:
        ok, data = api_call("POST", "/api/v1/orchestrator/run-cycle", token=token(),
                            json=_cycle_request(scenario, adaptive=False), timeout=240)
        if not ok:
            return None
        base[scenario] = data
    return base[scenario]


# ---------------------------------------------------------------------------
# Derived status per enterprise (used by the partner status strip and alerts)
# ---------------------------------------------------------------------------
def enterprise_health(state: Dict[str, Any]) -> Dict[str, Tuple[str, str]]:
    """Return {enterprise: (level, plain sentence)} where level is ok | warn | alert."""
    trig = state.get("trigger_mode", "NORMAL")
    kpis = state.get("global_kpis", {})
    out: Dict[str, Tuple[str, str]] = {}

    blocks = state.get("agrofarm_monitoring", [])
    flagged = [b["block_id"] for b in blocks if b.get("status") != "NORMAL"]
    if trig == "EXTREME_RAIN":
        out["agrofarm"] = ("alert", "Hujan ekstrem di BLK-11, panen dimajukan 2 hari")
    elif trig == "SENSOR_OUTAGE" or any(b.get("stale_data") for b in blocks):
        out["agrofarm"] = ("warn", "Sensor BLK-11 mati, memakai data historis")
    elif flagged:
        out["agrofarm"] = ("warn", f"{len(flagged)} blok perlu dicek: {', '.join(flagged)}")
    else:
        out["agrofarm"] = ("ok", f"Pasokan {fmt_kg(state.get('milp_result', {}).get('total_supply_kg', 0))}, lahan normal")

    rounds = kpis.get("negotiation_rounds_used", 0)
    if trig == "DEADLOCK":
        out["koperasi"] = ("alert", "Negosiasi buntu setelah 3 putaran")
    elif rounds > 0:
        out["koperasi"] = ("warn", f"Negosiasi berjalan, putaran {rounds} dari 3")
    else:
        out["koperasi"] = ("ok", "Harga stabil, tidak ada negosiasi ulang")

    ff = state.get("freshfood_qc_feedback", {})
    dock = ff.get("receiving_dock_window", {})
    dock_txt = f"dok {dock.get('open_time', '08:15')}–{dock.get('close_time', '11:40')}"
    if trig == "FOOD_SAFETY_FAIL" or ff.get("waste_valorization_plan"):
        out["freshfood"] = ("alert", "Lot H003 diblokir, dialihkan ke kompos")
    elif kpis.get("overtime_activated"):
        out["freshfood"] = ("warn", f"Shift lembur aktif, {dock_txt}")
    else:
        out["freshfood"] = ("ok", f"Produksi reguler, {dock_txt}")

    drop = state.get("capacity_drop_pct", 0) or 0
    km = state.get("vrptw_plan", {}).get("optimized_distance_km", 0)
    if drop >= 40:
        out["coldchain"] = ("alert", f"Kapasitas gudang turun {fmt_num(drop, 0)}%")
    elif drop > 0:
        out["coldchain"] = ("warn", f"Kapasitas gudang turun {fmt_num(drop, 0)}%")
    else:
        out["coldchain"] = ("ok", f"Suhu aman, rute {fmt_num(km)} km")

    sla = state.get("goods_receipt_sla", [])
    sla_bad = [x for x in sla if x.get("sla_status") != "ACCEPTED_ON_TIME"]
    fp = state.get("supermart_horizon_7d", {}).get("flash_promo_absorption", {})
    if sla_bad:
        out["supermart"] = ("alert", f"{len(sla_bad)} penerimaan barang bermasalah")
    elif trig in ("DEMAND_SURGE", "COMPOUND"):
        out["supermart"] = ("warn", "Permintaan melonjak, Grade B sebagai pengganti")
    elif fp.get("enabled"):
        out["supermart"] = ("warn", f"Promo kilat siap serap +{fmt_kg(fp.get('extra_absorption_cap_kg', 0))}")
    else:
        out["supermart"] = ("ok", f"Pemenuhan pesanan {fmt_pct(kpis.get('order_fulfillment_rate_pct', 0))}")
    return out


LEVEL_STYLE = {
    "ok": ("Normal", "green", ":material/check_circle:"),
    "warn": ("Perhatian", "orange", ":material/warning:"),
    "alert": ("Kritis", "red", ":material/error:"),
}
