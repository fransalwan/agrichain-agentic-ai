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
        return f"Cacat permukaan {m.group(1)}%"
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

    The global operator also needs the no-replanning baseline, so both requests run in parallel.
    """
    scenario = st.session_state["scenario"]
    cycles = st.session_state["cycles"]
    if scenario not in cycles:
        tok = token()
        want_base = role_key() == "global" and scenario not in st.session_state["baselines"]
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
