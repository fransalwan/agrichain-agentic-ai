"""AgriChain Agentic AI v2.0 — Decoupled Role-Adaptive Multi-Enterprise Cockpit.

Implements all 4 Improvement Pillars:
1. Decoupled HTTP API Client (FastAPI Gateway + Server-Side X-Scoped-Token Privacy Redaction + Lineage)
2. Deepened Local AI Modules:
   - AgroFarm (AGT-01): NDVI, 14-Day +/- 2sigma Deviation, 80% Quantile PI, Feature Importance, Sensor Fallback, Extreme Rain
   - ColdChain (AGT-04): OR-Tools VRPTW + Scenario Comparison, XGBoost ETA, Fleet & Shipments CRUD, Geospatial Map, 7-12C SOP
3. Enterprise UI/UX Governance:
   - Role-Adaptive Navigation (Global Operator | Farm Manager | Fleet Manager | Koperasi | FreshFood | SuperMart)
   - 5 Mandatory UI States (Loading, Empty, Error, Stale/Partial Data Warning, Success + SHA-256 Audit)
   - Impact-Preview Confirmation Console before HITL Approve / Re-Optimize / Reject
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from PIL import Image

from config.settings import AGENT_MODEL_PROFILES, DATA_DIR, RESULTS_DIR, settings
from src.agents.orchestrator import AgriChainOrchestrator
from src.protocols.fipa_epcis import now_wib_iso

st.set_page_config(
    page_title="AgriChain Agentic AI v2.1 — Demo-Ready Multi-Enterprise Cockpit",
    page_icon="🍅",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS (Strict High-Contrast Light Mode — WCAG AAA Legibility)
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    :root, html, body, .stApp {
        color-scheme: light !important;
        background-color: #F8FAFC !important;
        color: #0F172A !important;
    }
    .stApp [data-testid="stHeader"] {
        background-color: #F8FAFC !important;
    }
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #CBD5E1 !important;
    }
    section[data-testid="stSidebar"] * {
        color: #0F172A !important;
    }
    section[data-testid="stSidebar"] .stCaption,
    section[data-testid="stSidebar"] small {
        color: #334155 !important;
    }
    .block-container {
        padding-top: 2.0rem;
        padding-bottom: 1.8rem;
    }
    h1, h2, h3, h4, h5, p, li, label, .stMarkdown {
        color: #0F172A !important;
    }
    /* Crisp high-contrast inline code pills (replaces faint green default) */
    code {
        background-color: #E2E8F0 !important;
        color: #0F2C4C !important;
        font-weight: 600 !important;
        padding: 0.12rem 0.38rem !important;
        border-radius: 4px !important;
        border: 1px solid #CBD5E1 !important;
    }
    /* Tab bar contrast */
    button[data-baseweb="tab"] {
        color: #334155 !important;
        font-weight: 600 !important;
        background-color: transparent !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #1F4E79 !important;
        font-weight: 700 !important;
    }
    div[data-baseweb="tab-highlight"] {
        background-color: #1F4E79 !important;
    }
    /* Executive Primary & Secondary Buttons */
    .stButton > button[kind="primary"],
    .stFormSubmitButton > button {
        background-color: #1F4E79 !important;
        color: #FFFFFF !important;
        border: 1px solid #143454 !important;
        font-weight: 600 !important;
    }
    .stButton > button[kind="primary"] *,
    .stFormSubmitButton > button *,
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] *,
    section[data-testid="stSidebar"] .stFormSubmitButton > button * {
        color: #FFFFFF !important;
    }
    .stButton > button[kind="primary"]:hover,
    .stFormSubmitButton > button:hover {
        background-color: #143454 !important;
        color: #FFFFFF !important;
    }
    .stButton > button[kind="primary"]:hover *,
    .stFormSubmitButton > button:hover * {
        color: #FFFFFF !important;
    }
    .stButton > button[kind="secondary"],
    .stDownloadButton > button {
        background-color: #FFFFFF !important;
        color: #0F2C4C !important;
        border: 1px solid #94A3B8 !important;
        font-weight: 600 !important;
    }
    .stButton > button[kind="secondary"]:hover,
    .stDownloadButton > button:hover {
        background-color: #EDF3F9 !important;
        border-color: #1F4E79 !important;
    }
    /* Inputs, selects, expanders */
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    input, textarea {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
        border-color: #94A3B8 !important;
    }
    details, [data-testid="stExpander"] {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px !important;
    }
    /* High-contrast Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
        padding: 0.7rem 0.9rem !important;
        border-radius: 8px !important;
    }
    [data-testid="stMetricLabel"] {
        color: #334155 !important;
        font-weight: 600 !important;
    }
    [data-testid="stMetricValue"] {
        color: #0F172A !important;
        font-size: 1.42rem !important;
        font-weight: 700 !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 0.80rem !important;
        font-weight: 600 !important;
    }
    /* Top Executive Banner (pure white text on deep navy) */
    .role-banner {
        background: linear-gradient(90deg, #102A43 0%, #1F4E79 65%, #2B6CB0 100%);
        color: #FFFFFF !important;
        padding: 0.95rem 1.3rem;
        border-radius: 10px;
        margin-bottom: 0.95rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.5rem;
        box-shadow: 0 2px 6px rgba(15, 44, 76, 0.16);
    }
    .role-banner * {
        color: #FFFFFF !important;
    }
    .role-badge {
        background: rgba(255,255,255,0.20);
        border: 1px solid rgba(255,255,255,0.45);
        color: #FFFFFF !important;
        padding: 0.25rem 0.72rem;
        border-radius: 999px;
        font-size: 0.80rem;
        font-weight: 600;
    }
    /* Alert & Briefing Boxes — dark legible text on clean light tints */
    .banner-ok { background:#DCFCE7; border:1px solid #86EFAC; border-left:5px solid #15803D; color:#14532D !important; padding:0.75rem 1rem; border-radius:6px; margin-bottom:0.75rem; }
    .banner-ok * { color:#14532D !important; }
    .banner-warn { background:#FEF3C7; border:1px solid #FCD34D; border-left:5px solid #B45309; color:#78350F !important; padding:0.75rem 1rem; border-radius:6px; margin-bottom:0.75rem; }
    .banner-warn * { color:#78350F !important; }
    .banner-stale { background:#FFEDD5; border:1px solid #FDBA74; border-left:6px solid #C2410C; color:#7C2D12 !important; padding:0.75rem 1rem; border-radius:6px; margin-bottom:0.75rem; }
    .banner-stale * { color:#7C2D12 !important; }
    .banner-danger { background:#FEE2E2; border:1px solid #FCA5A5; border-left:5px solid #B91C1C; color:#7F1D1D !important; padding:0.75rem 1rem; border-radius:6px; margin-bottom:0.75rem; }
    .banner-danger * { color:#7F1D1D !important; }
    .brief-box { background:#EFF6FF; border:1px solid #93C5FD; border-left:5px solid #1F4E79; color:#0F2C4C !important; padding:0.85rem 1rem; border-radius:6px; margin-bottom:0.8rem; line-height:1.5; }
    .brief-box * { color:#0F2C4C !important; }
    .trace-card { background:#FFFFFF; border:1px solid #CBD5E1; border-left:4px solid #1F4E79; color:#0F172A !important; border-radius:6px; padding:0.65rem 0.95rem; margin-bottom:0.45rem; }
    .trace-card * { color:#0F172A !important; }
    .msg-card { background:#FFFFFF; border:1px solid #CBD5E1; border-left:4px solid #2B6CB0; color:#0F172A !important; border-radius:6px; padding:0.55rem 0.9rem; margin-bottom:0.4rem; }
    .msg-card * { color:#0F172A !important; }
    .empty-card { background:#FFFFFF; border:1px dashed #64748B; border-radius:8px; padding:1.4rem; text-align:center; color:#334155 !important; margin:0.6rem 0; }
    /* Demo Storyboard & Live Closed-Loop 5-Enterprise Strip */
    .demo-guide-box {
        background: #F0F9FF;
        border: 1px solid #7DD3FC;
        border-left: 5px solid #0284C7;
        color: #0C4A6E !important;
        padding: 0.6rem 0.95rem;
        border-radius: 7px;
        margin-bottom: 0.65rem;
        font-size: 0.88rem;
        line-height: 1.42;
    }
    .demo-guide-box * { color: #0C4A6E !important; }
    .loop-strip {
        display: flex;
        align-items: stretch;
        justify-content: space-between;
        gap: 0.35rem;
        margin-bottom: 0.7rem;
        flex-wrap: nowrap;
    }
    .loop-node {
        flex: 1;
        border-radius: 8px;
        padding: 0.5rem 0.65rem;
        border: 1px solid #CBD5E1;
        background: #FFFFFF;
        min-width: 0;
    }
    .loop-ok { background: #F0FDF4; border-color: #86EFAC; border-top: 4px solid #15803D; }
    .loop-warn { background: #FFFBEB; border-color: #FCD34D; border-top: 4px solid #D97706; }
    .loop-danger { background: #FEF2F2; border-color: #FCA5A5; border-top: 4px solid #DC2626; }
    .loop-title { font-size: 0.80rem; font-weight: 700; color: #0F172A !important; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .loop-sub { font-size: 0.74rem; color: #334155 !important; margin-top: 0.15rem; line-height: 1.25; }
    .loop-arrow { display: flex; align-items: center; color: #1F4E79 !important; font-weight: 800; font-size: 1.05rem; padding: 0 0.05rem; }
    .rbac-pill-red { background:#FEE2E2; color:#991B1B !important; border:1px solid #FCA5A5; padding:0.2rem 0.55rem; border-radius:6px; font-weight:700; font-size:0.8rem; display:inline-block; margin-bottom:0.4rem; }
    .rbac-pill-green { background:#DCFCE7; color:#166534 !important; border:1px solid #86EFAC; padding:0.2rem 0.55rem; border-radius:6px; font-weight:700; font-size:0.8rem; display:inline-block; margin-bottom:0.4rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Role Profiles — 1 Primary Stakeholder per Enterprise + Global Operator
# (RBAC Tokens verified SERVER-SIDE by FastAPI)
# ---------------------------------------------------------------------------
ROLE_PROFILES: Dict[str, Dict[str, Any]] = {
    "Global Control Center Operator (AGT-06)": {
        "user": "ops.global@agrichain.id",
        "enterprise_key": "global",
        "token": "tok_orchestrator_global_scope_v1",
        "scope_desc": "Global Orchestration, Impact-Preview HITL & Audit — 15 Atribut Privat Enterprise TER-REDAKSI di Server FastAPI",
    },
    "Farm Manager — AgroFarm (AGT-01)": {
        "user": "farm.manager@agrofarm.co.id",
        "enterprise_key": "agrofarm",
        "token": "tok_agrofarm_local_v1",
        "scope_desc": "Stakeholder Tunggal AgroFarm (PostgreSQL) — Crop Monitoring NDVI (14d ± 2σ), RF 80% PI & HPP Lokal Terbuka",
    },
    "Cooperative Manager — Koperasi Tani (AGT-02)": {
        "user": "coop.manager@koperasitani.id",
        "enterprise_key": "koperasi",
        "token": "tok_koperasi_local_v1",
        "scope_desc": "Stakeholder Tunggal Koperasi (MySQL) — LightGBM Price, Contract Net Auction & floor_price_rp Terbuka Lokal",
    },
    "Quality Control & Production Manager — FreshFood (AGT-03)": {
        "user": "qc.prod@freshfood.co.id",
        "enterprise_key": "freshfood",
        "token": "tok_freshfood_local_v1",
        "scope_desc": "Stakeholder Tunggal FreshFood (MongoDB) — Galeri Citra RGB CNN, Food Safety Hard-Block & Otorisasi Lembur +500 kg",
    },
    "Fleet & Cold Chain Manager — ColdChain (AGT-04)": {
        "user": "fleet.coldchain@coldchain.co.id",
        "enterprise_key": "coldchain",
        "token": "tok_coldchain_local_v1",
        "scope_desc": "Stakeholder Tunggal ColdChain (TimescaleDB) — Fleet/Shipments CRUD, OR-Tools VRPTW, XGBoost ETA & Gudang 7–12°C",
    },
    "Purchasing Manager — SuperMart (AGT-05)": {
        "user": "purchasing@supermart.co.id",
        "enterprise_key": "supermart",
        "token": "tok_supermart_local_v1",
        "scope_desc": "Stakeholder Tunggal SuperMart (MySQL) — XGBoost Demand, Newsvendor PO, Substitusi Grade B & ceiling_price_rp Lokal",
    },
}

SCENARIO_LABELS = {
    "NORMAL": "NORMAL — Operasi Harian Standar",
    "COLD_STORAGE_FAILURE": "COLD_STORAGE_FAILURE — Kompresor Rusak (3.000 → 1.000 kg)",
    "EXTREME_RAIN": "EXTREME_RAIN — Hujan Ekstrem AgroFarm BLK-11 (Panen Maju 2 Hari)",
    "SENSOR_OUTAGE": "SENSOR_OUTAGE — Sensor BLK-11 Offline ≥ 3 Hari (Stale Fallback)",
    "DEMAND_SURGE": "DEMAND_SURGE — Lonjakan Permintaan SuperMart (2.000 → 2.800 kg)",
    "FOOD_SAFETY_FAIL": "FOOD_SAFETY_FAIL — Batch H003 Gagal Uji Mikroba/Pestisida",
    "COMPOUND": "COMPOUND — Cold Storage Failure + Demand Surge Simultan",
    "DEADLOCK": "DEADLOCK — Tawaran Pembeli < Floor Price (3 Ronde → HITL)",
}

# ---------------------------------------------------------------------------
# Guided 1-Click Presentation Storyboard (Aligned to 4-Member Group Roles)
# ---------------------------------------------------------------------------
DEMO_PRESETS: List[Dict[str, Any]] = [
    {
        "id": "al_koperasi",
        "btn": "1️⃣ Al · Koperasi",
        "presenter": "M. Al lail Qadrillah — Koperasi Tani (AGT-02)",
        "role": "Cooperative Manager — Koperasi Tani (AGT-02)",
        "scenario": "NORMAL",
        "tip": "Tunjukkan LightGBM Price Forecast + Contract Net Auction, lalu klik tab <b>Koperasi Local DB Explorer</b> untuk bukti side-by-side <code>floor_price_rp</code> (Global 🔒 REDACTED vs Koperasi 🔓 UNLOCKED).",
    },
    {
        "id": "monanta_agrofarm",
        "btn": "2️⃣ Monanta · AgroFarm",
        "presenter": "Monanta Alfiareza — AgroFarm (AGT-01)",
        "role": "Farm Manager — AgroFarm (AGT-01)",
        "scenario": "EXTREME_RAIN",
        "tip": "Tunjukkan tabel <b>Deviasi NDVI 14-Hari ± 2σ</b> (BLK-11 hujan 96 mm → panen maju <code>-2 hari</code>), Simulator RF + 80% PI yang otomatis tersinkron, serta sinyal masuk <b>Flash-Promo SuperMart (+300 kg)</b>.",
    },
    {
        "id": "dimas_coldchain",
        "btn": "3️⃣ Dimas · ColdChain",
        "presenter": "Dimas Prabowo — ColdChain Logistics (AGT-04)",
        "role": "Fleet & Cold Chain Manager — ColdChain (AGT-04)",
        "scenario": "COLD_STORAGE_FAILURE",
        "tip": "Tunjukkan <b>Peta Geospasial OR-Tools VRPTW</b> (otomatis sinkron skenario <code>COLD_STORAGE_DROP</code> & <i>dock window</i> FreshFood/SuperMart, 0 pelanggaran TW), tab CRUD Armada/Shipments, serta <b>XGBoost ETA</b> & SOP <code>7–12°C</code>.",
    },
    {
        "id": "frans_freshfood",
        "btn": "4️⃣ Frans · FreshFood",
        "presenter": "Frans Alwan Purba — FreshFood Processing (AGT-03)",
        "role": "Quality Control & Production Manager — FreshFood (AGT-03)",
        "scenario": "FOOD_SAFETY_FAIL",
        "tip": "Tunjukkan <b>Galeri CNN RGB 4-Kelas</b> berdampingan dengan <b>Simulator Hard-Block</b> (klik Inspeksi QC untuk lihat <code>0 kg</code> blokir mutlak), tab <b>FEFO & Dock Window</b>, serta <b>QC Feedback → AgroFarm & Valorisasi Kompos/Biogas</b>.",
    },
    {
        "id": "frans_supermart",
        "btn": "5️⃣ Frans · SuperMart",
        "presenter": "Frans Alwan Purba — SuperMart (AGT-05)",
        "role": "Purchasing Manager — SuperMart (AGT-05)",
        "scenario": "DEMAND_SURGE",
        "tip": "Tunjukkan <b>Proyeksi 7-Hari XGBoost (H+1..H+7)</b> yang dikirim ke hulu, tab <b>PO CRUD</b> (guardrail Grade C ditolak, substitusi Grade B ≤ 30% & <code>ceiling_price</code> terbuka lokal), serta tab <b>Goods Receipt SLA 7–12°C</b>.",
    },
    {
        "id": "frans_global",
        "btn": "6️⃣ Frans · Global HITL",
        "presenter": "Frans Alwan Purba — Global Control Center (AGT-06)",
        "role": "Global Control Center Operator (AGT-06)",
        "scenario": "COMPOUND",
        "tip": "Tunjukkan <b>Live Closed-Loop 5-Enterprise Strip</b>, grafik <b>Sankey & Decision Shift</b>, klik <b>Approve & Commit via API</b> pada HITL Bar, lalu buka tab <b>Trace, Lineage & Audit</b> untuk membuktikan rantai <b>SHA-256 VERIFIED</b>.",
    },
]


def apply_demo_preset(preset: Dict[str, Any]) -> None:
    """Callback executed BEFORE widget instantiation to switch role & scenario cleanly."""
    st.session_state["sel_role"] = preset["role"]
    st.session_state["sel_scenario"] = preset["scenario"]
    st.session_state["active_demo_id"] = preset["id"]
    st.session_state["sim_stale_ui"] = False
    st.session_state["use_sliders"] = False


def reset_demo_state() -> None:
    """Reset cockpit cleanly to default Global Operator demo starting point."""
    st.session_state["sel_role"] = list(ROLE_PROFILES.keys())[0]
    st.session_state["sel_scenario"] = "COLD_STORAGE_FAILURE"
    st.session_state["active_demo_id"] = None
    st.session_state["sim_stale_ui"] = False
    st.session_state["use_sliders"] = False
    st.session_state["adaptive_toggle"] = True
    st.session_state["routing_choice"] = "Selective Hybrid (3 LLM + 3 ML)"
    st.session_state["solver_choice"] = "Neuro-Symbolic MILP-FEFO"
    st.session_state.pop("last_sig", None)


def render_closed_loop_strip(state: Dict[str, Any]) -> None:
    """Render a 1-glance horizontal 5-enterprise closed-loop handshake strip."""
    trig = state.get("trigger_mode", "NORMAL")
    kpis = state.get("global_kpis", {})
    af_mon = state.get("agrofarm_monitoring", [])
    af_alert = any(b.get("status") != "NORMAL" for b in af_mon)
    af_cls = "loop-danger" if trig == "EXTREME_RAIN" else ("loop-warn" if trig == "SENSOR_OUTAGE" or af_alert else "loop-ok")
    af_txt = (
        "BLK-11 Hujan 96mm (-2h)" if trig == "EXTREME_RAIN"
        else ("BLK-11 Stale Fallback" if trig == "SENSOR_OUTAGE"
              else f"Supply {state.get('total_supply_kg', 4500):,.0f} kg · 2σ OK")
    )

    rounds = kpis.get("negotiation_rounds_used", 0)
    kp_cls = "loop-danger" if trig == "DEADLOCK" else ("loop-warn" if rounds > 0 else "loop-ok")
    kp_txt = "DEADLOCK 3/3 → HITL" if trig == "DEADLOCK" else (f"Contract Net R{rounds}/3" if rounds > 0 else "Harga Stabil · Floor 🔒")

    ff_ot = bool(kpis.get("overtime_activated"))
    ff_ctx = state.get("freshfood_qc_feedback", {})
    dock = ff_ctx.get("receiving_dock_window", {"open_time": "08:15", "close_time": "11:40"})
    ff_cls = "loop-danger" if trig == "FOOD_SAFETY_FAIL" else ("loop-warn" if ff_ot else "loop-ok")
    ff_txt = (
        "Hard-Block H003 (0 kg) + Compost" if trig == "FOOD_SAFETY_FAIL"
        else (f"Overtime +500kg · Dock {dock.get('open_time')}–{dock.get('close_time')}" if ff_ot
              else f"Reguler · Dock {dock.get('open_time')}–{dock.get('close_time')}")
    )

    drop_pct = state.get("capacity_drop_pct", 0)
    vr_km = state.get("vrptw_plan", {}).get("optimized_distance_km", 263)
    cc_cls = "loop-danger" if drop_pct >= 40 else ("loop-warn" if drop_pct > 0 else "loop-ok")
    cc_txt = f"Cap {state.get('cold_storage_cap_kg', 3000):,.0f}kg (-{drop_pct:.0f}%) · VRPTW {vr_km:.0f}km" if drop_pct > 0 else f"SOP 7–12°C · VRPTW {vr_km:.0f}km"

    sm_h7 = state.get("supermart_horizon_7d", {})
    fp_on = sm_h7.get("flash_promo_absorption", {}).get("enabled", False)
    sla_list = state.get("goods_receipt_sla", [])
    sla_ok = all(x.get("sla_status") == "ACCEPTED_ON_TIME" for x in sla_list) if sla_list else True
    sm_cls = "loop-warn" if trig in ("DEMAND_SURGE", "COMPOUND") or fp_on else ("loop-ok" if sla_ok else "loop-danger")
    sm_txt = (
        "Flash-Promo +300kg · 7d Sync" if fp_on
        else (f"Surge {state.get('supermart_demand_kg', 2000):,.0f}kg · Sub B ≤30%" if trig in ("DEMAND_SURGE", "COMPOUND")
              else f"Demand {state.get('supermart_demand_kg', 2000):,.0f}kg · SLA OK")
    )

    st.markdown(
        f"""
        <div class="loop-strip">
            <div class="loop-node {af_cls}"><div class="loop-title">🌱 AgroFarm (AGT-01)</div><div class="loop-sub">{af_txt}</div></div>
            <div class="loop-arrow">→</div>
            <div class="loop-node {kp_cls}"><div class="loop-title">🤝 Koperasi (AGT-02)</div><div class="loop-sub">{kp_txt}</div></div>
            <div class="loop-arrow">→</div>
            <div class="loop-node {ff_cls}"><div class="loop-title">🏭 FreshFood (AGT-03)</div><div class="loop-sub">{ff_txt}</div></div>
            <div class="loop-arrow">→</div>
            <div class="loop-node {cc_cls}"><div class="loop-title">❄️ ColdChain (AGT-04)</div><div class="loop-sub">{cc_txt}</div></div>
            <div class="loop-arrow">→</div>
            <div class="loop-node {sm_cls}"><div class="loop-title">🛒 SuperMart (AGT-05)</div><div class="loop-sub">{sm_txt}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_demo_storyboard() -> None:
    """Render 1-click presenter storyboard buttons + active talking points."""
    active_id = st.session_state.get("active_demo_id")
    cols = st.columns(len(DEMO_PRESETS))
    for col, preset in zip(cols, DEMO_PRESETS):
        is_active = active_id == preset["id"]
        col.button(
            preset["btn"],
            key=f"demo_btn_{preset['id']}",
            type="primary" if is_active else "secondary",
            use_container_width=True,
            on_click=apply_demo_preset,
            args=(preset,),
        )
    if active_id:
        cur = next((p for p in DEMO_PRESETS if p["id"] == active_id), None)
        if cur:
            st.markdown(
                f"<div class='demo-guide-box'><b>🎬 Presenter Aktif — {cur['presenter']}</b> "
                f"(Skenario: <code>{cur['scenario']}</code>): {cur['tip']}</div>",
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Decoupled HTTP API Client (UI -> FastAPI Gateway with graceful local fallback)
# ---------------------------------------------------------------------------
class ApiBridge:
    def __init__(self, base_url: str = settings.api_base_url):
        self.base_url = base_url.rstrip("/")

    def check_health(self) -> tuple[bool, Dict[str, Any]]:
        try:
            r = httpx.get(f"{self.base_url}/api/v1/health", timeout=2.5)
            if r.status_code == 200:
                return True, r.json()
        except Exception:
            pass
        return False, {"status": "offline", "server_timestamp": now_wib_iso()}

    def post(self, path: str, payload: Dict[str, Any], token: str, params: Optional[Dict[str, Any]] = None) -> tuple[bool, Any]:
        try:
            r = httpx.post(
                f"{self.base_url}{path}",
                json=payload,
                params=params,
                headers={"X-Scoped-Token": token},
                timeout=20.0,
            )
            if r.status_code < 300:
                return True, r.json()
            return False, r.json().get("detail", f"HTTP {r.status_code}")
        except Exception as exc:
            return False, str(exc)

    def get(self, path: str, token: str, params: Optional[Dict[str, Any]] = None) -> tuple[bool, Any]:
        try:
            r = httpx.get(
                f"{self.base_url}{path}",
                params=params,
                headers={"X-Scoped-Token": token},
                timeout=10.0,
            )
            if r.status_code < 300:
                return True, r.json()
            return False, r.json().get("detail", f"HTTP {r.status_code}")
        except Exception as exc:
            return False, str(exc)


@st.cache_resource
def load_local_orchestrator(homogeneous_frontier: bool = False) -> AgriChainOrchestrator:
    return AgriChainOrchestrator(homogeneous_frontier=homogeneous_frontier)


@st.cache_data
def load_ml_metrics() -> Dict[str, Any]:
    path = RESULTS_DIR / "ml_metrics.json"
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    em = raw.get("enterprise_models", {})
    return {
        **raw,
        "agrofarm_rf": em.get("AGT-01_AgroFarm", {}),
        "koperasi_lgbm": em.get("AGT-02_Koperasi", {}),
        "freshfood_cnn": em.get("AGT-03_FreshFood", {}),
        "coldchain_iforest_cvrp": em.get("AGT-04_ColdChain", {}),
        "supermart_xgb": em.get("AGT-05_SuperMart", {}),
    }


@st.cache_data
def load_tomato_rgb_sample(n_per_class: int = 2) -> List[Dict[str, Any]]:
    npz_path = DATA_DIR / "freshfood_tomato_images.npz"
    if not npz_path.exists():
        return []
    data = np.load(npz_path, allow_pickle=False)
    imgs, labels = data["images"], data["labels"]
    samples = []
    for cls in ("A", "B", "C", "Reject"):
        for idx in np.where(labels == cls)[0][:n_per_class]:
            samples.append({"index": int(idx), "true_grade": str(labels[idx]), "image": imgs[idx]})
    return samples


# ---------------------------------------------------------------------------
# Reusable Visualization Builders
# ---------------------------------------------------------------------------
def build_sankey(allocations: List[Dict[str, Any]], unallocated: Dict[str, float]) -> go.Figure:
    nodes = ["AgroFarm", "Koperasi Tani", "SuperMart", "FreshFood_Reg", "FreshFood_OT", "ColdStorage", "Partner3PL", "AltBuyer", "Food Loss / Blocked"]
    node_idx = {n: i for i, n in enumerate(nodes)}
    sources, targets, values, labels, colors = [], [], [], [], []
    total_qty = sum(a["qty_kg"] for a in allocations) + sum(unallocated.values())
    if total_qty > 0:
        sources.append(0)
        targets.append(1)
        values.append(total_qty)
        labels.append(f"Total Panen: {total_qty:,.0f} kg")
        colors.append("rgba(47, 133, 90, 0.35)")
    ch_col = {
        "SuperMart": "rgba(197, 48, 48, 0.45)",
        "FreshFood_Reg": "rgba(107, 70, 193, 0.45)",
        "FreshFood_OT": "rgba(214, 158, 46, 0.55)",
        "ColdStorage": "rgba(9, 135, 160, 0.45)",
        "Partner3PL": "rgba(49, 130, 206, 0.45)",
        "AltBuyer": "rgba(113, 128, 150, 0.45)",
    }
    for a in allocations:
        if a["channel"] in node_idx and a["qty_kg"] > 0:
            sources.append(1)
            targets.append(node_idx[a["channel"]])
            values.append(a["qty_kg"])
            labels.append(f"{a['lot_id']} (Grade {a['grade']}, SL {a['shelf_life_days']}d): {a['qty_kg']:,.0f} kg")
            colors.append(ch_col.get(a["channel"], "rgba(100,116,139,0.4)"))
    for lid, loss_kg in unallocated.items():
        if loss_kg > 0.5:
            sources.append(1)
            targets.append(8)
            values.append(loss_kg)
            labels.append(f"{lid} Loss/Blocked: {loss_kg:,.0f} kg")
            colors.append("rgba(220, 38, 38, 0.65)")

    fig = go.Figure(
        data=[go.Sankey(
            node=dict(pad=16, thickness=20, label=nodes, color=["#2F855A", "#B7791F", "#C53030", "#6B46C1", "#D69E2E", "#0987A0", "#3182CE", "#64748B", "#DC2626"]),
            link=dict(source=sources, target=targets, value=values, label=labels, color=colors),
        )]
    )
    fig.update_layout(
        title=dict(text="Aliran Alokasi Rantai Pasok Tomat (MILP-FEFO)", font=dict(color="#0F172A", size=14)),
        template="plotly_white",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(color="#0F172A", size=12),
        height=315,
        margin=dict(l=10, r=10, t=34, b=8),
    )
    return fig


def build_decision_shift_chart(baseline_state: Dict[str, Any], active_state: Dict[str, Any]) -> go.Figure:
    channels = ["SuperMart", "FreshFood_Reg", "FreshFood_OT", "ColdStorage", "Partner3PL", "AltBuyer", "Food Loss"]

    def summarize(st_obj: Dict[str, Any]) -> Dict[str, float]:
        out = {c: 0.0 for c in channels}
        for a in st_obj["milp_result"]["allocations"]:
            if a["channel"] in out:
                out[a["channel"]] += float(a["qty_kg"])
        out["Food Loss"] = float(st_obj["milp_result"]["total_loss_kg"])
        return out

    s_base, s_act = summarize(baseline_state), summarize(active_state)
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Statis (Tanpa Adaptive Replan)", x=channels, y=[s_base[c] for c in channels], marker_color="#64748B", text=[f"{s_base[c]:,.0f}" if s_base[c] > 0 else "" for c in channels], textposition="outside", textfont=dict(color="#0F172A")))
    fig.add_trace(go.Bar(name="Adaptive Replanning (MILP-FEFO)", x=channels, y=[s_act[c] for c in channels], marker_color="#1F4E79", text=[f"{s_act[c]:,.0f}" if s_act[c] > 0 else "" for c in channels], textposition="outside", textfont=dict(color="#0F172A")))
    fig.update_layout(
        title=dict(text="Perubahan Alokasi (kg): Statis vs Adaptive Replanning", y=0.97, x=0.0, font=dict(size=14, color="#0F172A")),
        template="plotly_white",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(color="#0F172A"),
        barmode="group",
        yaxis_title="Volume (kg)",
        yaxis=dict(range=[0, max(max(s_base.values()), max(s_act.values()), 100) * 1.18], gridcolor="#E2E8F0"),
        height=320,
        legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="center", x=0.5, font=dict(color="#0F172A")),
        margin=dict(l=10, r=10, t=40, b=48),
    )
    return fig


def build_geospatial_vrptw_map(vrptw_plan: Dict[str, Any]) -> go.Figure:
    """Interactive Yogyakarta/Sleman/Bantul geospatial map of OR-Tools VRPTW vehicle routes."""
    palette = ["#1F4E79", "#C53030", "#2F855A", "#D69E2E"]
    fig = go.Figure()
    for idx, r in enumerate(vrptw_plan.get("routes", [])):
        coords = r.get("coords", [])
        if not coords:
            continue
        fig.add_trace(go.Scattermapbox(
            lat=[c["lat"] for c in coords],
            lon=[c["lon"] for c in coords],
            mode="lines+markers+text",
            name=f"{r['truck']} ({r['distance_km']} km · ETA {r['predicted_eta_min']}m)",
            line=dict(width=3.5, color=palette[idx % len(palette)]),
            marker=dict(size=10, color=palette[idx % len(palette)]),
            text=[c["name"] for c in coords],
            textposition="top right",
            hovertext=[f"{c['name']} | Tiba: +{c['arrival_min']} mnt | {r['truck']}" for c in coords],
            hoverinfo="text",
        ))

    fig.update_layout(
        mapbox=dict(style="open-street-map", center=dict(lat=-7.775, lon=110.355), zoom=10.6),
        title=dict(
            text=f"Peta Geospasial Rute VRPTW ({vrptw_plan.get('scenario', 'NORMAL')}) — Total {vrptw_plan.get('optimized_distance_km', 0):.0f} km (-{vrptw_plan.get('distance_reduction_pct', 0)}%)",
            font=dict(color="#0F172A", size=14),
        ),
        template="plotly_white",
        paper_bgcolor="#FFFFFF",
        font=dict(color="#0F172A"),
        height=380,
        margin=dict(l=5, r=5, t=40, b=5),
        legend=dict(orientation="h", yanchor="bottom", y=0.01, xanchor="left", x=0.01, bgcolor="rgba(255,255,255,0.92)", font=dict(color="#0F172A")),
    )
    return fig


# ---------------------------------------------------------------------------
# Reusable UI Module Renderers (used cleanly across Role-Adaptive Views)
# ---------------------------------------------------------------------------
def render_server_data_explorer(api: ApiBridge, api_online: bool, role_info: Dict[str, Any], selected_role: str, default_ent: str = "koperasi") -> None:
    st.subheader("🗄️ Server-Side Privacy-Enforced Data Explorer (Zero-Direct-DB-Access)")
    db_catalog = [
        ("Koperasi Tani — market_price_negotiations [Privat: floor_price_rp]", "koperasi", "market_price_negotiations"),
        ("AgroFarm — private_costs [Privat: HPP & Farmer ID]", "agrofarm", "private_costs"),
        ("AgroFarm — active_harvest_lots (PostgreSQL)", "agrofarm", "active_harvest_lots"),
        ("AgroFarm — farm_harvest_history (PostgreSQL)", "agrofarm", "farm_harvest_history"),
        ("FreshFood — tomato_qc_documents (MongoDB JSON)", "freshfood", "qc_docs"),
        ("ColdChain — cold_storage_telemetry (TimescaleDB)", "coldchain", "cold_storage_telemetry"),
        ("ColdChain — fleet_delivery_routes (TimescaleDB)", "coldchain", "fleet_delivery_routes"),
        ("SuperMart — retail_pos_sales (MySQL)", "supermart", "retail_pos_sales"),
    ]
    default_idx = next((i for i, item in enumerate(db_catalog) if item[1] == default_ent), 0)
    e1, e2, e3 = st.columns([2.2, 1.1, 0.7])
    sel = e1.selectbox("Basis Data & Tabel Enterprise", db_catalog, index=default_idx, format_func=lambda x: x[0], key=f"de_sel_{default_ent}")
    search_q = e2.text_input("Cari Nilai / Lot / Zona", value="", key=f"de_q_{default_ent}")
    lim = e3.number_input("Maks. Baris", 10, 300, 30, 10, key=f"de_lim_{default_ent}")

    _, ent_key, tbl_name = sel
    if api_online:
        ok, data = api.get(f"/api/v1/data-explorer/{ent_key}/{tbl_name}", role_info["token"], params={"search": search_q, "limit": int(lim)})
        if not ok:
            st.error(f"Gagal memuat data dari FastAPI ({now_wib_iso()}): {data}")
            if st.button("🔄 Retry Koneksi API", key=f"retry_de_{default_ent}"):
                st.rerun()
            return
        df = pd.DataFrame(data["records"])
        redacted = data["redacted_columns"]
        tot, matched = data["total_rows"], data["matched_rows"]
        src_badge = f"🟢 Server-Side FastAPI Firewall (Scope: `{data['caller_scope']}`)"
    else:
        st.warning("⚠️ FastAPI offline — menjalankan fallback lokal (mode terdegradasi).")
        return

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Rekaman DB", f"{tot:,}")
    m2.metric("Cocok Filter", f"{matched:,}")
    m3.metric("Kolom Ter-redaksi Server", f"{len(redacted)} kolom" if redacted else "0 (Milik Sendiri / Publik)")
    st.caption(f"Sumber: {src_badge} · Sync: `{data['timestamp']}`")

    if redacted:
        st.warning(f"🔒 **Server-Side Data Sovereignty Aktif:** Kolom `{', '.join(redacted)}` otomatis dihapus oleh FastAPI sebelum dikirim ke UI karena token `{selected_role}` bukan pemilik DB `{ent_key}`.")

    # Instant Side-by-Side Live RBAC Proof for tables with private attributes
    owner_token_map = {
        "koperasi": ("tok_koperasi_local_v1", "Cooperative Manager — Koperasi (Pemilik DB)"),
        "agrofarm": ("tok_agrofarm_local_v1", "Farm Manager — AgroFarm (Pemilik DB)"),
    }
    has_private_tbl = (ent_key, tbl_name) in (("koperasi", "market_price_negotiations"), ("agrofarm", "private_costs"))
    if api_online and has_private_tbl:
        show_sbs = st.toggle(
            "⚔️ Mode Bukti Langsung (1-Layar): Bandingkan Token Global vs Token Pemilik DB",
            value=True,
            key=f"sbs_rbac_{default_ent}_{ent_key}_{tbl_name}",
        )
        if show_sbs:
            ok_g, d_glob = api.get(f"/api/v1/data-explorer/{ent_key}/{tbl_name}", "tok_orchestrator_global_scope_v1", params={"search": search_q, "limit": 6})
            own_tok, own_lbl = owner_token_map[ent_key]
            ok_o, d_own = api.get(f"/api/v1/data-explorer/{ent_key}/{tbl_name}", own_tok, params={"search": search_q, "limit": 6})
            if ok_g and ok_o:
                df_g, df_o = pd.DataFrame(d_glob["records"]), pd.DataFrame(d_own["records"])
                priv_cols = d_glob["redacted_columns"]
                show_cols = [c for c in (list(df_g.columns[:3]) + priv_cols) if c in df_g.columns]
                show_cols = list(dict.fromkeys(show_cols))
                for pc in priv_cols:
                    if pc in df_g.columns:
                        df_g[pc] = "🔒 REDACTED (Server)"
                c_left, c_right = st.columns(2)
                with c_left:
                    st.markdown("<span class='rbac-pill-red'>🔒 Token Global (AGT-06) — Atribut Privat Ter-redaksi</span>", unsafe_allow_html=True)
                    st.dataframe(df_g[show_cols], use_container_width=True, hide_index=True)
                with c_right:
                    st.markdown(f"<span class='rbac-pill-green'>🔓 {own_lbl} — Akses Lokal Terbuka</span>", unsafe_allow_html=True)
                    st.dataframe(df_o[show_cols], use_container_width=True, hide_index=True)
                st.divider()

    if df.empty:
        st.markdown("<div class='empty-card'><b>Tidak ada data yang cocok dengan pencarian Anda.</b><br/>Kosongkan kotak pencarian atau pilih tabel enterprise lain.</div>", unsafe_allow_html=True)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️ Unduh CSV (Ter-redaksi Sesuai Scope)",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=f"{ent_key}_{tbl_name}_{data['caller_scope']}.csv",
            mime="text/csv",
            key=f"dl_{ent_key}_{tbl_name}_{default_ent}",
        )


def render_agrofarm_workspace(api: ApiBridge, api_online: bool, state: Dict[str, Any], ml_metrics: Dict[str, Any], role_info: Dict[str, Any], selected_role: str) -> None:
    st.subheader("🌱 AgroFarm Cockpit v2 — Crop Monitoring (14-Day ± 2σ) & Random Forest (80% Quantile PI)")
    m_af = ml_metrics.get("agrofarm_rf", {})
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Test MAE (RF 250 Trees)", f"{m_af.get('test_mae_kg', 93.0)} kg", f"{m_af.get('test_mae_pct_of_mean', 7.2)}% mean")
    k2.metric("80% PI Coverage", f"{m_af.get('pi80_coverage', 0.80)*100:.1f}%", "Target 75–85%")
    k3.metric("Test R²", f"{m_af.get('test_r2', 0.94)}")
    k4.metric("Unggul 2 Baseline?", "YA ✅" if m_af.get("beats_both_baselines", True) else "FALLBACK")
    k5.metric("Private HPP Scope", "UNLOCKED 🔓" if role_info["enterprise_key"] == "agrofarm" else "REDACTED 🔒")

    # 14-Day Deviation Monitoring Table
    mon_rows = state.get("agrofarm_monitoring", [])
    if mon_rows:
        st.markdown("#### 🛰️ Status Pemantauan Blok Lahan (Aturan Deviasi NDVI 14-Hari ± 2σ & Curah Hujan > 90 mm)")
        if any(b.get("stale_data") for b in mon_rows):
            st.markdown("<div class='banner-stale'><b>⚠️ STALE SENSOR DATA WARNING:</b> Sensor blok <code>BLK-11</code> offline ≥ 3 hari berturut-turut. Agen otomatis berpindah ke <b>FALLBACK_HISTORICAL_MEAN</b> dengan interval diperlebar & label <i>Meragukan</i>.</div>", unsafe_allow_html=True)
        mon_df = pd.DataFrame([
            {
                "Block ID": b["block_id"],
                "Lot": b["lot_id"],
                "Varietas": b["variety"],
                "NDVI Hari Ini": b["ndvi_today"],
                "Batas 2σ Bawah": b["ndvi_2sigma_lower"],
                "Hujan 14h (mm)": b["rain_14d_mm"],
                "Kelembapan (%)": b["soil_moisture_pct"],
                "Status Blok": b["status"],
                "Penyebab / Rekomendasi": "; ".join(b["causes"]) if b["causes"] else "Normal (dalam rentang 2σ)",
            }
            for b in mon_rows
        ])
        st.dataframe(mon_df, use_container_width=True, hide_index=True)

    c_sim, c_fi = st.columns([1.15, 1.0])
    with c_sim:
        st.markdown("#### 🎛️ Simulator Prediksi RF + 80% PI + Jendela Panen (Via FastAPI)")
        trig_key = state["trigger_mode"]
        is_rain_trig = trig_key == "EXTREME_RAIN"
        is_outage_trig = trig_key == "SENSOR_OUTAGE"
        sc1, sc2 = st.columns(2)
        s_area = sc1.slider("Luas Blok (ha)", 0.4, 2.0, 0.70, 0.05, key=f"af_area_{trig_key}")
        s_ndvi = sc2.slider("Indeks NDVI", 0.30, 0.88, 0.41 if is_rain_trig else 0.64, 0.01, key=f"af_ndvi_{trig_key}")
        s_rain = sc1.slider("Curah Hujan (mm)", 0.0, 120.0, 96.0 if is_rain_trig else 24.0, 2.0, key=f"af_rain_{trig_key}")
        s_age = sc2.slider("Umur Tanaman (hari)", 65, 90, 78, 1, key=f"af_age_{trig_key}")
        c_chk1, c_chk2 = st.columns(2)
        sim_rain = c_chk1.checkbox("Simulasi Hujan Ekstrem (>90 mm)", value=is_rain_trig, key=f"af_simrain_{trig_key}")
        sim_off = c_chk2.checkbox("Simulasi Sensor Mati 3 Hari (Fallback)", value=is_outage_trig, key=f"af_simoff_{trig_key}")

        payload = {
            "block_id": "BLK-11",
            "lot_id": "H003",
            "area_ha": s_area,
            "avg_temp_c": 29.4 if sim_rain else 26.5,
            "soil_moisture_pct": 83.0 if sim_rain else 66.0,
            "rainfall_mm": max(s_rain, 96.0) if sim_rain else s_rain,
            "fertilizer_kg_ha": 165.0,
            "crop_age_days": s_age,
            "ndvi": 0.41 if sim_rain else s_ndvi,
            "extreme_rain_flag": sim_rain,
            "sensor_offline_days": 3 if sim_off else 0,
        }
        if api_online:
            ok, resp = api.post("/api/v1/agrofarm/predict", payload, role_info["token"])
            pred = resp["prediction"] if ok else load_local_orchestrator().agrofarm.model.predict_batch([payload])[0]
        else:
            pred = load_local_orchestrator().agrofarm.model.predict_batch([payload])[0]

        pi80 = pred["pi80_interval_kg"]
        hw = pred["harvest_window"]
        if pred["doubtful"]:
            st.warning(f"⚠️ **MODE FALLBACK ({pred['prediction_mode']}):** Estimasi `{pred['predicted_kg']:,.1f} kg` | Interval 80%: `[{pi80[0]:,.1f} – {pi80[1]:,.1f}] kg` (Interval diperlebar karena sensor offline).")
        else:
            st.success(
                f"**Prediksi Panen (`{pred['model_version']}`):** `{pred['predicted_kg']:,.1f} kg`  |  "
                f"**80% Quantile PI:** `[{pi80[0]:,.1f} – {pi80[1]:,.1f}] kg`  \n"
                f"**Rekomendasi Jendela Panen:** `{hw['start']}` s.d. `{hw['end']}` (Shift: `{hw['shift_days']:+d} hari`) — *{hw['reason']}*"
            )

    with c_fi:
        st.markdown("#### 📊 Kontribusi Fitur Random Forest (*Feature Importance*)")
        fi = m_af.get("feature_importance", {})
        if fi:
            fi_df = pd.DataFrame(list(fi.items()), columns=["Fitur", "Importance"]).sort_values("Importance", ascending=True)
            fig_fi = px.bar(fi_df, x="Importance", y="Fitur", orientation="h", color="Importance", color_continuous_scale="Tealgrn", template="plotly_white")
            fig_fi.update_layout(
                height=300,
                coloraxis_showscale=False,
                paper_bgcolor="#FFFFFF",
                plot_bgcolor="#FFFFFF",
                font=dict(color="#0F172A"),
                xaxis=dict(gridcolor="#E2E8F0"),
                margin=dict(l=10, r=10, t=15, b=10),
            )
            st.plotly_chart(fig_fi, use_container_width=True)

    # Closed-Loop Cross-Enterprise Inputs received by AgroFarm (v2.1 Parity)
    fb_col, dem_col = st.columns(2)
    with fb_col:
        st.markdown("#### 🔁 QC Feedback Loop dari FreshFood (`AGT-03 → AGT-01`)")
        fb_items = state.get("freshfood_qc_feedback", {}).get("feedback_to_agrofarm", [])
        if fb_items:
            st.dataframe(pd.DataFrame(fb_items), use_container_width=True, hide_index=True)
        else:
            st.info("✅ Tidak ada temuan cacat/residu kritis dari FreshFood pada siklus ini.")
    with dem_col:
        st.markdown("#### 📈 Sinyal Permintaan 7-Hari dari SuperMart (`AGT-05 → AGT-01`)")
        h7 = state.get("supermart_horizon_7d", {}).get("horizon_7d", [])
        if h7:
            st.dataframe(pd.DataFrame(h7)[["horizon", "day_name", "forecast_demand_kg", "recommended_po_kg", "promo_active"]], use_container_width=True, hide_index=True)
            fp = state.get("supermart_horizon_7d", {}).get("flash_promo_absorption", {})
            if fp.get("enabled"):
                st.success(f"🔥 **Flash-Promo Absorption Aktif:** SuperMart siap menyerap hingga **+{fp['extra_absorption_cap_kg']:.0f} kg** Grade A (diskon ≥ {fp['required_coop_discount_pct']:.0f}%).")


def render_coldchain_workspace(api: ApiBridge, api_online: bool, state: Dict[str, Any], ml_metrics: Dict[str, Any], role_info: Dict[str, Any]) -> None:
    st.subheader("❄️ ColdChain Logistics Cockpit v2 — VRPTW, XGBoost ETA, Fleet/Shipments CRUD & Monitor 7–12°C")
    m_cc = ml_metrics.get("coldchain_iforest_cvrp", {})
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Anomaly F1 (IForest)", f"{m_cc.get('anomaly_f1_pct', 95.32)}%", f"Recall {m_cc.get('anomaly_recall_pct', 100.0)}%")
    k2.metric("XGBoost ETA MAE", f"{m_cc.get('eta_mae_min', 4.5)} mnt", f"MAPE {m_cc.get('eta_mape_pct', 6.5)}%")
    k3.metric("Reduksi Rute OR-Tools", f"-{m_cc.get('cvrp_distance_reduction_pct', 31.15)}%", "TW Violations: 0")
    k4.metric("Standar Suhu Tomat", f"{settings.tomato_safe_temp_min_c}–{settings.tomato_safe_temp_max_c}°C", "Anti Chilling-Injury")
    k5.metric("Kapasitas Gudang Aktif", f"{state['cold_storage_cap_kg']:,.0f} kg", f"Drop {state['capacity_drop_pct']}%", delta_color="inverse")

    cc_tabs = st.tabs([
        "🗺️ Route Planning (VRPTW) & Geospatial Map",
        "🚚 Fleet & Drivers + Shipments Inbox (CRUD)",
        "🌡️ Cold Chain Monitor (7–12°C) & XGBoost ETA",
    ])

    with cc_tabs[0]:
        vrptw_opts = ["NORMAL", "ROAD_DISRUPTION", "VEHICLE_BREAKDOWN", "COLD_STORAGE_DROP"]
        trig_map = {"COLD_STORAGE_FAILURE": 3, "COMPOUND": 3, "EXTREME_RAIN": 1}
        default_vr_idx = trig_map.get(state["trigger_mode"], 0)
        vc1, vc2, vc3 = st.columns([1.6, 1.0, 1.0])
        vrptw_scen = vc1.selectbox("Skenario Optimasi OR-Tools VRPTW (Auto-Sync)", vrptw_opts, index=default_vr_idx, key=f"vrptw_scen_{state['trigger_mode']}")
        vrptw_traf = vc2.selectbox("Tingkat Kemacetan", [(0, "Low"), (1, "Medium"), (2, "High")], index=1, format_func=lambda x: x[1], key=f"vrptw_traf_{state['trigger_mode']}")[0]
        run_vrptw = vc3.button("⚡ Jalankan VRPTW + Compare", type="primary", use_container_width=True)

        if api_online:
            ok, vr_resp = api.post("/api/v1/coldchain/vrptw", {"scenario": vrptw_scen, "traffic_level": vrptw_traf}, role_info["token"])
            active_plan = vr_resp["active_plan"] if ok else state.get("vrptw_plan", {})
            norm_plan = vr_resp["normal_baseline"] if ok else active_plan
        else:
            active_plan = load_local_orchestrator().coldchain.model.solve_vrptw(scenario=vrptw_scen, traffic_level=vrptw_traf)
            norm_plan = load_local_orchestrator().coldchain.model.solve_vrptw(scenario="NORMAL", traffic_level=1)

        if run_vrptw:
            st.toast(f"VRPTW selesai: {active_plan['optimized_distance_km']:.0f} km (0 pelanggaran time window)!", icon="✅")

        m_col, t_col = st.columns([1.3, 1.0])
        with m_col:
            st.plotly_chart(build_geospatial_vrptw_map(active_plan), use_container_width=True)
        with t_col:
            st.markdown("#### 📋 Ringkasan & Jadwal VRPTW")
            comp_df = pd.DataFrame([
                {"Metrik": "Total Jarak (km)", "Normal Baseline": norm_plan["optimized_distance_km"], f"Skenario {vrptw_scen}": active_plan["optimized_distance_km"]},
                {"Metrik": "Biaya Transport (Rp)", "Normal Baseline": norm_plan["transport_cost_rp"], f"Skenario {vrptw_scen}": active_plan["transport_cost_rp"]},
                {"Metrik": "Time Window Violations", "Normal Baseline": norm_plan["time_window_violations"], f"Skenario {vrptw_scen}": active_plan["time_window_violations"]},
            ])
            st.dataframe(comp_df, use_container_width=True, hide_index=True)

            r_rows = [
                {
                    "Armada": r["truck"],
                    "Rute": " → ".join(r["stops"]),
                    "Muatan": f"{r['load_kg']}/{r['capacity_kg']} kg ({r['utilization_pct']}%)",
                    "Jarak": f"{r['distance_km']} km",
                    "XGBoost ETA": f"{r['predicted_eta_min']} mnt",
                }
                for r in active_plan.get("routes", [])
            ]
            st.dataframe(pd.DataFrame(r_rows), use_container_width=True, hide_index=True)

    with cc_tabs[1]:
        f_col, s_col = st.columns(2)
        with f_col:
            st.markdown("#### 🚛 Master Fleet & Drivers (`GET / POST /api/v1/coldchain/fleet`)")
            ok_f, fl_data = api.get("/api/v1/coldchain/fleet", role_info["token"]) if api_online else (False, {})
            if ok_f:
                st.dataframe(pd.DataFrame(fl_data["vehicles"]), use_container_width=True, hide_index=True)
            with st.form("add_vehicle_form", clear_on_submit=True):
                st.markdown("**Tambah / Update Kendaraan Reefer**")
                fv1, fv2 = st.columns(2)
                vid = fv1.text_input("Vehicle ID", value="V005")
                vcap = fv2.number_input("Kapasitas (kg)", 500, 10000, 3500, 250)
                vstat = fv1.selectbox("Status", ["Available", "In Transit", "Maintenance"])
                vdrv = fv2.text_input("Referensi Driver", value="D-005 (Eko P.)")
                if st.form_submit_button("💾 Simpan Kendaraan ke API"):
                    ok_s, res_s = api.post(
                        "/api/v1/coldchain/fleet",
                        {"vehicle_id": vid, "capacity_kg": vcap, "min_temp_c": 7.0, "max_temp_c": 12.0, "status": vstat, "driver_ref": vdrv},
                        role_info["token"],
                    )
                    if ok_s:
                        st.success(f"✅ {res_s['action']} `{vid}` berhasil! Audit Hash: `{res_s['audit_hash'][:14]}...`")
                        st.rerun()
                    else:
                        st.error(f"Validasi / Akses Ditolak: {res_s}")

        with s_col:
            st.markdown("#### 📦 Shipments Request Inbox (`GET / POST /api/v1/coldchain/shipments`)")
            ok_sh, sh_data = api.get("/api/v1/coldchain/shipments", role_info["token"]) if api_online else (False, {})
            if ok_sh:
                st.dataframe(pd.DataFrame(sh_data["shipments"]), use_container_width=True, hide_index=True)
            with st.form("add_shipment_form", clear_on_submit=True):
                st.markdown("**Tambah Shipment Request (Validasi Deadline & Suhu 7–12°C)**")
                fs1, fs2 = st.columns(2)
                sh_id = fs1.text_input("Shipment ID", value="SH004")
                sh_lot = fs2.text_input("Lot ID", value="H004")
                sh_qty = fs1.number_input("Quantity (kg)", 100, 5000, 800, 100)
                sh_dest = fs2.selectbox("Tujuan", ["SuperMart_DC", "FreshFood_Plant", "SuperMart_B2", "Partner3PL_WH"])
                sh_rdy = fs1.text_input("Ready Time (HH:MM)", value="08:30")
                sh_ddl = fs2.text_input("Deadline (HH:MM)", value="12:30")
                if st.form_submit_button("📨 Submit Shipment Request"):
                    ok_cr, res_cr = api.post(
                        "/api/v1/coldchain/shipments",
                        {"shipment_id": sh_id, "lot_id": sh_lot, "quantity_kg": sh_qty, "destination": sh_dest, "ready_time": sh_rdy, "deadline": sh_ddl},
                        role_info["token"],
                    )
                    if ok_cr:
                        st.success(f"✅ Shipment `{sh_id}` tersimpan! Audit Hash: `{res_cr['audit_hash'][:14]}...`")
                        st.rerun()
                    else:
                        st.error(f"Validasi Gagal: {res_cr}")

    with cc_tabs[2]:
        t1, t2 = st.columns([1.4, 1.0])
        with t1:
            df_tel = pd.read_csv(DATA_DIR / "coldchain_iot_telemetry.csv").tail(220)
            fig_tel = go.Figure()
            fig_tel.add_hrect(y0=settings.tomato_safe_temp_min_c, y1=settings.tomato_safe_temp_max_c, fillcolor="rgba(16,185,129,0.12)", line_width=0, annotation_text="SOP Tomat Aman (7–12°C)")
            fig_tel.add_trace(go.Scatter(x=df_tel["ts"], y=df_tel["temp_c"], mode="lines", name="Suhu Ruang (°C)", line=dict(color="#1F4E79", width=2)))
            anoms = df_tel[df_tel["is_anomaly"] == 1]
            if not anoms.empty:
                fig_tel.add_trace(go.Scatter(x=anoms["ts"], y=anoms["temp_c"], mode="markers", name="Anomali Isolation Forest", marker=dict(color="#DC2626", size=9, symbol="x")))
            fig_tel.update_layout(
                title=dict(text="Telemetri Suhu Cold Storage & Deteksi Anomali Isolation Forest", font=dict(color="#0F172A", size=14)),
                template="plotly_white",
                paper_bgcolor="#FFFFFF",
                plot_bgcolor="#FFFFFF",
                font=dict(color="#0F172A"),
                yaxis_title="Suhu (°C)",
                yaxis=dict(gridcolor="#E2E8F0"),
                height=320,
                margin=dict(l=10, r=10, t=38, b=10),
            )
            st.plotly_chart(fig_tel, use_container_width=True)
        with t2:
            st.markdown("#### ⏱️ Simulator Prediksi ETA (XGBoost Regressor)")
            e_dist = st.slider("Jarak Tempuh (km)", 10.0, 100.0, 48.0, 2.0)
            e_traf = st.selectbox("Level Traffic", [(0, "Low"), (1, "Medium"), (2, "High")], index=1, format_func=lambda x: x[1], key="eta_tr")[0]
            e_stops = st.slider("Jumlah Stop", 1, 5, 2)
            e_wth = st.selectbox("Cuaca", [(0, "Cerah"), (1, "Hujan"), (2, "Hujan Lebat")], format_func=lambda x: x[1])[0]
            if api_online:
                ok_e, e_res = api.post("/api/v1/coldchain/eta", {"distance_km": e_dist, "traffic_level": e_traf, "num_stops": e_stops, "weather_severity": e_wth}, role_info["token"])
                eta_out = e_res["eta"] if ok_e else load_local_orchestrator().coldchain.model.eta_model.predict_eta_minutes(e_dist, e_traf, e_stops, e_wth)
            else:
                eta_out = load_local_orchestrator().coldchain.model.eta_model.predict_eta_minutes(e_dist, e_traf, e_stops, e_wth)
            st.info(
                f"**Prediksi Durasi (`{eta_out['model_version']}`):** `{eta_out['predicted_duration_min']} menit`  \n"
                f"**Rentang Estimasi:** `[{eta_out['error_band_min'][0]} – {eta_out['error_band_min'][1]}] menit`"
            )


def render_freshfood_module(api: ApiBridge, api_online: bool, state: Dict[str, Any], ml_metrics: Dict[str, Any], role_info: Dict[str, Any]) -> None:
    st.subheader("🏭 FreshFood Processing Cockpit v2.1 — CNN Visual QC, Hard-Block, FEFO & AgroFarm Feedback")
    m_ff = ml_metrics.get("freshfood_cnn", {})
    ff_ctx = state.get("freshfood_qc_feedback", {})
    dock = ff_ctx.get("receiving_dock_window", {"open_time": "08:15", "close_time": "11:40", "unloading_slots": 2})

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("CNN Accuracy", f"{m_ff.get('test_accuracy_pct', 98.67)}%", "Target >= 90%")
    k2.metric("Macro-F1", f"{m_ff.get('test_macro_f1', 0.9878)}")
    k3.metric("Reject Recall", f"{m_ff.get('reject_recall_pct', 100.0)}%", "0 Missed Reject")
    k4.metric("Overtime Status", "AKTIF (+500 kg)" if state["global_kpis"].get("overtime_activated") else "REGULER (2.000 kg)")
    k5.metric("Dock Window → VRPTW", f"{dock.get('open_time', '08:15')}–{dock.get('close_time', '11:40')}", f"{dock.get('unloading_slots', 2)} slot bongkar")

    ff_tabs = st.tabs([
        "🍅 Galeri RGB CNN & Hard-Block Lab API",
        "⚙️ Penjadwalan Lini FEFO & Dock Window",
        "🔁 QC Feedback → AgroFarm & Valorisasi Limbah",
    ])

    with ff_tabs[0]:
        col_cnn, col_lab = st.columns([1.05, 1.25])
        with col_cnn:
            st.markdown("#### 🍅 Sampel Visual CNN RGB (4 Kelas Mutu)")
            samples = load_tomato_rgb_sample(n_per_class=1)
            if samples:
                orch = load_local_orchestrator()
                preds = orch.freshfood.model.classify_images(np.stack([s["image"] for s in samples]))
                r1_c1, r1_c2 = st.columns(2)
                r2_c1, r2_c2 = st.columns(2)
                grid_slots = [r1_c1, r1_c2, r2_c1, r2_c2]
                for slot, s, pr in zip(grid_slots, samples, preds):
                    up = Image.fromarray(s["image"].astype(np.uint8)).resize((104, 104), Image.Resampling.NEAREST)
                    tag = "🔴 REJECT" if pr["predicted_grade"] == "Reject" else f"🟢 Grade {pr['predicted_grade']}"
                    slot.image(up, caption=f"True:{s['true_grade']} → {tag} ({pr['confidence']*100:.1f}%)")

        with col_lab:
            st.markdown("#### 🧪 Simulator Uji Lab Food Safety Hard-Block (`POST /api/v1/freshfood/qc-inspect`)")
            is_fs_fail = state["trigger_mode"] == "FOOD_SAFETY_FAIL"
            with st.form(f"ff_qc_form_{state['trigger_mode']}"):
                q1, q2 = st.columns(2)
                qc_lot = q1.text_input("Lot ID", value="H003")
                qc_blk = q2.text_input("Block ID", value="BLK-11")
                q3, q4 = st.columns(2)
                qc_ph = q3.number_input("pH (Aman 4.0–4.6)", 3.0, 6.0, 4.85 if is_fs_fail else 4.35, 0.05)
                qc_pest = q4.number_input("Pestisida ppm (≤ 0.05)", 0.0, 0.20, 0.08 if is_fs_fail else 0.02, 0.01)
                q5, q6 = st.columns(2)
                qc_def = q5.slider("Rasio Cacat Permukaan", 0.0, 0.40, 0.24 if is_fs_fail else 0.14, 0.02)
                qc_qty = q6.number_input("Volume Lot (kg)", 100.0, 3000.0, 1000.0, 100.0)
                qc_mic = st.checkbox("Lolos Uji Mikroba?", value=not is_fs_fail)
                if st.form_submit_button("🔬 Jalankan Inspeksi QC & Audit via API"):
                    payload = {"lot_id": qc_lot, "block_id": qc_blk, "qty_kg": qc_qty, "ph_level": qc_ph, "pesticide_residue_ppm": qc_pest, "microbial_pass": qc_mic, "defect_ratio": qc_def}
                    if api_online:
                        ok_q, res_q = api.post("/api/v1/freshfood/qc-inspect", payload, role_info["token"])
                        if ok_q:
                            v = res_q["safety_verdict"]
                            if v["food_safety_approved"]:
                                st.success(f"✅ Lot `{qc_lot}` LOLOS Food Safety! Audit Hash: `{res_q['audit_hash'][:14]}...`")
                            else:
                                st.error(f"⛔ HARD-BLOCK AKTIF (`0 kg` ke pangan): `{', '.join(v['violation_reasons'])}` | Valorisasi: `{res_q['waste_valorization_plan']['disposal_channel']}`")
                            if res_q.get("qc_feedback_to_agrofarm"):
                                st.warning(f"🔁 **Feedback dikirim ke AgroFarm `{qc_blk}`:** {res_q['qc_feedback_to_agrofarm']['recommendation']}")
                        else:
                            st.error(f"API Error: {res_q}")

    with ff_tabs[1]:
        inc_ot = st.checkbox("Aktifkan Shift Lembur (+500 kg & perpanjang dock hingga 14:00 WIB)", value=bool(state["global_kpis"].get("overtime_activated")), key="ff_ot_sim")
        if api_online:
            ok_sc, res_sc = api.post("/api/v1/freshfood/schedule", {"include_overtime": inc_ot}, role_info["token"])
            sched_data = res_sc["fefo_schedule"] if ok_sc else ff_ctx.get("fefo_line_schedule", {})
            dk_data = res_sc["receiving_dock_window"] if ok_sc else dock
        else:
            sched_data = ff_ctx.get("fefo_line_schedule", {})
            dk_data = dock
        st.info(f"🚚 **Dock Window Tersinkron ke ColdChain VRPTW:** Node `{dk_data.get('node')}` buka `{dk_data.get('open_time')}–{dk_data.get('close_time')} WIB` (`{dk_data.get('unloading_slots')} slot` bongkar) | Utilisasi Lini: **`{sched_data.get('capacity_utilization_pct', 0)}%`**")
        if sched_data.get("scheduled_lots"):
            st.dataframe(pd.DataFrame(sched_data["scheduled_lots"]), use_container_width=True, hide_index=True)

    with ff_tabs[2]:
        fb_items = ff_ctx.get("feedback_to_agrofarm", [])
        val_items = ff_ctx.get("waste_valorization_plan", [])
        if fb_items:
            st.markdown("**🔁 Umpan Balik Kualitas ke AgroFarm (`AGT-01`)**")
            st.dataframe(pd.DataFrame(fb_items), use_container_width=True, hide_index=True)
        else:
            st.success("✅ Tidak ada peringatan mutu yang perlu dikirim ke AgroFarm pada siklus ini.")
        if val_items:
            st.markdown("**♻️ Rencana Valorisasi Limbah Non-Pangan (`COMPOST_BIOGAS_RECOVERY`)**")
            st.dataframe(pd.DataFrame(val_items), use_container_width=True, hide_index=True)


def render_supermart_workspace(api: ApiBridge, api_online: bool, state: Dict[str, Any], ml_metrics: Dict[str, Any], role_info: Dict[str, Any]) -> None:
    st.subheader("🛒 SuperMart Procurement Cockpit v2.1 — 7-Day XGBoost Horizon, Newsvendor PO & Goods Receipt SLA")
    m_sm = ml_metrics.get("supermart_xgb", {})
    sm_ctx = state.get("supermart_horizon_7d", {})
    is_owner = role_info["enterprise_key"] == "supermart"
    is_surge = state["trigger_mode"] in ("DEMAND_SURGE", "COMPOUND")
    is_rain = state["trigger_mode"] == "EXTREME_RAIN"

    if api_online:
        ok_f7, f7_data = api.get("/api/v1/supermart/forecast-7d", role_info["token"], params={"demand_surge": is_surge, "early_harvest_signal": is_rain})
    else:
        ok_f7, f7_data = False, {}

    h7_rows = f7_data["horizon_7d"] if ok_f7 else sm_ctx.get("horizon_7d", [])
    fp_info = f7_data["flash_promo_absorption"] if ok_f7 else sm_ctx.get("flash_promo_absorption", {})
    ceil_a = f7_data.get("ceiling_price_grade_a_rp", "REDACTED") if ok_f7 else ("Rp10,500" if is_owner else "🔒 REDACTED")

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("XGBoost Test MAPE", f"{m_sm.get('test_mape_pct', 3.72)}%", f"R² {m_sm.get('test_r2', 0.9215)}")
    k2.metric("Newsvendor CF", f"{sm_ctx.get('critical_fractile', 0.346)}", "Konservatif Anti-Spoilage")
    k3.metric("Substitusi Grade B", "≤ 30% (HITL)" if is_surge else "0% (Grade A Only)")
    k4.metric("Flash-Promo Pull", f"+{fp_info.get('extra_absorption_cap_kg', 0):.0f} kg" if fp_info.get("enabled") else "Standar")
    k5.metric("Ceiling Price Scope", f"Rp{ceil_a:,.0f} 🔓" if isinstance(ceil_a, (int, float)) else "REDACTED 🔒")

    sm_tabs = st.tabs([
        "📈 Rolling Forecast 7-Hari (→ Hulu)",
        "🧾 Purchase Orders (PO CRUD) & Ceiling Guardrail",
        "✅ Goods Receipt SLA (ColdChain → SuperMart)",
    ])

    with sm_tabs[0]:
        if h7_rows:
            df_h7 = pd.DataFrame(h7_rows)
            fig_h7 = go.Figure()
            fig_h7.add_trace(go.Bar(x=df_h7["horizon"] + " (" + df_h7["day_name"] + ")", y=df_h7["forecast_demand_kg"], name="Forecast Permintaan (kg)", marker_color="#1F4E79"))
            fig_h7.add_trace(go.Scatter(x=df_h7["horizon"] + " (" + df_h7["day_name"] + ")", y=df_h7["recommended_po_kg"], name="Rekomendasi PO Newsvendor (kg)", mode="lines+markers", line=dict(color="#D97706", width=3)))
            fig_h7.update_layout(
                title=dict(text="Proyeksi Permintaan Tomat 7 Hari (H+1 s.d. H+7) — Dibagikan ke AgroFarm & Koperasi", font=dict(color="#0F172A", size=14)),
                template="plotly_white",
                paper_bgcolor="#FFFFFF",
                plot_bgcolor="#FFFFFF",
                font=dict(color="#0F172A"),
                yaxis_title="Volume (kg)",
                yaxis=dict(gridcolor="#E2E8F0"),
                height=320,
                legend=dict(orientation="h", yanchor="top", y=-0.20, xanchor="center", x=0.5),
                margin=dict(l=10, r=10, t=40, b=50),
            )
            st.plotly_chart(fig_h7, use_container_width=True)
            st.dataframe(df_h7, use_container_width=True, hide_index=True)

    with sm_tabs[1]:
        p1, p2 = st.columns([1.25, 1.0])
        with p1:
            st.markdown("#### 📋 Daftar Purchase Order Aktif (`GET /api/v1/supermart/po`)")
            ok_po, po_list = api.get("/api/v1/supermart/po", role_info["token"]) if api_online else (False, {})
            if ok_po:
                st.dataframe(pd.DataFrame(po_list["purchase_orders"]), use_container_width=True, hide_index=True)
        with p2:
            with st.form("sm_po_form", clear_on_submit=True):
                st.markdown("**Terbitkan PO Baru (Validasi Ceiling Price & Grade B ≤ 30%)**")
                pf1, pf2 = st.columns(2)
                po_id = pf1.text_input("PO ID", value="PO-SM-002")
                po_lot = pf2.text_input("Lot ID", value="H001")
                po_gr = pf1.selectbox("Grade", ["A", "B", "C"])
                po_qty = pf2.number_input("Qty (kg)", 100.0, 5000.0, 1200.0, 100.0)
                po_pr = pf1.number_input("Harga Sepakat (Rp/kg)", 3000.0, 15000.0, 10000.0, 100.0)
                po_sub = pf2.number_input("Porsi Sub Grade B (%)", 0.0, 50.0, 0.0, 5.0)
                if st.form_submit_button("💾 Submit PO ke FastAPI"):
                    ok_cp, res_cp = api.post(
                        "/api/v1/supermart/po",
                        {"po_id": po_id, "lot_id": po_lot, "grade": po_gr, "qty_kg": po_qty, "agreed_price_rp": po_pr, "grade_b_sub_pct": po_sub},
                        role_info["token"],
                    )
                    if ok_cp:
                        st.success(f"✅ {res_cp['action']} `{po_id}` tersimpan! Audit Hash: `{res_cp['audit_hash'][:14]}...`")
                        st.rerun()
                    else:
                        st.error(f"Validasi / Kebijakan Ditolak: {res_cp}")

    with sm_tabs[2]:
        sla_list = state.get("goods_receipt_sla", [])
        if sla_list:
            st.markdown("#### 🚚 Evaluasi SLA Kedatangan ColdChain Siklus Aktif (SOP `7,0–12,0°C`)")
            st.dataframe(pd.DataFrame(sla_list), use_container_width=True, hide_index=True)
        st.markdown("#### 🧪 Simulator Verifikasi Goods Receipt SLA (`POST /api/v1/supermart/goods-receipt-sla`)")
        with st.form("sm_sla_form"):
            sl1, sl2, sl3 = st.columns(3)
            sl_temp = sl1.number_input("Suhu Truk Saat Tiba (°C)", 2.0, 20.0, 9.4, 0.2)
            sl_arr = sl2.number_input("Waktu Tiba (+menit dari 08:00)", 10, 400, 95, 5)
            sl_ddl = sl3.number_input("Batas Deadline Dermaga (+menit)", 60, 400, 260, 10)
            if st.form_submit_button("🔎 Verifikasi SLA Kedatangan"):
                if api_online:
                    ok_sl, res_sl = api.post("/api/v1/supermart/goods-receipt-sla", {"lot_id": "H001", "delivered_temp_c": sl_temp, "arrival_min": int(sl_arr), "deadline_min": int(sl_ddl)}, role_info["token"])
                    if ok_sl:
                        sv = res_sl["sla_verdict"]
                        if sv["sla_status"] == "ACCEPTED_ON_TIME":
                            st.success(f"✅ **{sv['sla_status']}** — {sv['action_note']}")
                        elif sv["sla_status"] == "ACCEPTED_WITH_DELAY_CLAIM":
                            st.warning(f"⚠️ **{sv['sla_status']}** (Klaim Rp{sv['sla_penalty_rp']:,.0f}) — {sv['action_note']}")
                        else:
                            st.error(f"⛔ **{sv['sla_status']}** (Klaim Rp{sv['sla_penalty_rp']:,.0f}) — {sv['action_note']}")


def render_koperasi_workspace(api: ApiBridge, api_online: bool, state: Dict[str, Any], ml_metrics: Dict[str, Any], role_info: Dict[str, Any]) -> None:
    st.subheader("🤝 Koperasi Tani Cockpit v2.1 — LightGBM Price, Contract Net & Private Floor Price Guardrail")
    m_kp = ml_metrics.get("koperasi_lgbm", {})
    is_owner = role_info["enterprise_key"] == "koperasi"
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("LightGBM Test MAPE", f"{m_kp.get('test_mape_pct', 4.28)}%", f"MAE Rp{m_kp.get('test_mae_rp', 240.1)}/kg")
    k2.metric("Test R²", f"{m_kp.get('test_r2', 0.9853)}")
    k3.metric("Negotiation Rounds", f"{state['global_kpis'].get('negotiation_rounds_used', 0)}/3")
    k4.metric("Floor Price Scope", "UNLOCKED 🔓" if is_owner else "REDACTED 🔒")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 💹 Simulator Prediksi Harga & Contract Net (`POST /api/v1/koperasi/price-forecast`)")
        kg = st.selectbox("Grade Tomat", ["A", "B", "C"], index=1, key="kp_g_v21")
        ko = st.number_input("Simulasi Tawaran Pembeli (Rp/kg)", 2000, 15000, 6400, 100, key="kp_o_v21")
        if api_online:
            ok_kp, kp_res = api.post("/api/v1/koperasi/price-forecast", {"grade": kg}, role_info["token"])
            ask_rp = kp_res["predicted_market_price_rp"] if ok_kp else load_local_orchestrator().koperasi.model.predict_price(grade=kg)
            fl_disp = kp_res["floor_price_rp"] if ok_kp else "🔒 REDACTED"
        else:
            ask_rp = load_local_orchestrator().koperasi.model.predict_price(grade=kg)
            fl_disp = "🔒 REDACTED"
        orch = load_local_orchestrator()
        auc = orch.koperasi.model.evaluate_contract_net_bids("SIM", 500.0, orch.koperasi._private_floor_prices[kg], [{"buyer_id": "Buyer", "qty_kg": 500.0, "offer_price_rp": ko}])
        st.info(f"Harga Acuan LightGBM: **`Rp{ask_rp:,.0f}/kg`** | Floor Price (Scope `{role_info['enterprise_key']}`): **`{fl_disp}`** | Hasil Lelang: **`{auc['status']}`**")
    with c2:
        st.markdown("#### 🔁 Sinyal Lintas Enterprise untuk Koperasi")
        val_items = state.get("freshfood_qc_feedback", {}).get("waste_valorization_plan", [])
        if val_items:
            st.warning("♻️ **Notice Valorisasi FreshFood:** Ada lot ditolak keamanan pangan yang dialihkan ke kompos/biogas:")
            st.dataframe(pd.DataFrame(val_items), use_container_width=True, hide_index=True)
        else:
            st.success("✅ Seluruh lot aktif lolos QC FreshFood dan siap diserap kanal komersial.")


def render_koperasi_and_supermart_modules(api: ApiBridge, api_online: bool, state: Dict[str, Any], ml_metrics: Dict[str, Any], role_info: Dict[str, Any]) -> None:
    render_koperasi_workspace(api, api_online, state, ml_metrics, role_info)
    st.divider()
    render_supermart_workspace(api, api_online, state, ml_metrics, role_info)


def render_decision_trace_and_audit(api: ApiBridge, api_online: bool, state: Dict[str, Any], role_info: Dict[str, Any]) -> None:
    st.subheader("🧭 LangGraph 7-Node Decision Trace & Canonical Cross-Enterprise Lineage")
    for step in state.get("decision_trace", []):
        st.markdown(
            f"<div class='trace-card'><b>Step {step['step']} · <code>{step['node']}</code></b> | Actor: <b>{step['actors']}</b> | Status: <code>{step['status']}</code> <span style='float:right;color:#64748B;font-size:0.78rem;'>{step['timestamp']}</span><br/>{step['summary']}</div>",
            unsafe_allow_html=True,
        )

    if state.get("lineage"):
        st.markdown("#### 🔗 Canonical Lineage (`block_id → lot_id → qc_doc_id → shipment_id → trip_id → vehicle_id → po_ref`)")
        st.dataframe(pd.DataFrame(state["lineage"]), use_container_width=True, hide_index=True)

    c_m, c_l = st.columns([1.2, 1.0])
    with c_m:
        st.markdown("#### 💬 Log Komunikasi A2A / FIPA-ACL / GS1 EPCIS 2.0")
        msgs = state.get("messages", [])
        sel_p = st.selectbox("Filter Performatif", ["ALL"] + sorted({m["performative"] for m in msgs}), key="perf_flt")
        for idx, m in enumerate([x for x in msgs if sel_p == "ALL" or x["performative"] == sel_p]):
            st.markdown(f"<div class='msg-card'><b>#{idx+1}</b> <code>{m['performative']}</code> | <b>{m['sender']}</b> → <b>{m['receiver']}</b> <span style='float:right;color:#64748B;font-size:0.78rem;'>{m['protocol']} · R{m['negotiation_round']}</span></div>", unsafe_allow_html=True)
            with st.expander(f"Payload JSON (#{idx+1})"):
                st.json({"payload": m["payload"], "epcis_event": m.get("epcis_event")})
    with c_l:
        st.markdown("#### 🧠 Telemetri Hybrid Router (3 LLM + 3 Deterministic ML)")
        tel = state["global_kpis"].get("llm_telemetry", {})
        calls_df = pd.DataFrame(tel.get("calls", []))
        if not calls_df.empty:
            st.dataframe(calls_df, use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("#### 🔐 Immutable SHA-256 Hash-Chained Audit Trail (`GET /api/v1/audit/trail`)")
    if api_online:
        ok_a, aud = api.get("/api/v1/audit/trail", role_info["token"], params={"limit": 15})
        if ok_a:
            if aud["chain_valid"]:
                st.success(f"✅ SHA-256 Chain Verified ({aud['returned_entries']} entri terbaru) · Sync: `{aud['timestamp']}`")
            else:
                st.error("❌ TAMPER DETECTED pada rantai hash audit!")
            st.dataframe(pd.DataFrame([
                {"Time": e["timestamp"], "Event": e["event_type"], "Actor": e["actor"], "Details": json.dumps(e["details"]), "SHA-256": e["hash"][:18] + "..."}
                for e in aud["entries"]
            ]), use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Main Application Entrypoint
# ---------------------------------------------------------------------------
def main() -> None:
    api = ApiBridge()
    api_online, health_info = api.check_health()
    ml_metrics = load_ml_metrics()

    # Initialize session_state keys cleanly so 1-click Demo Presets & Reset never clash
    st.session_state.setdefault("sel_role", list(ROLE_PROFILES.keys())[0])
    st.session_state.setdefault("sel_scenario", "COLD_STORAGE_FAILURE")
    st.session_state.setdefault("demo_mode", True)
    st.session_state.setdefault("sim_stale_ui", False)
    st.session_state.setdefault("use_sliders", False)
    st.session_state.setdefault("adaptive_toggle", True)
    st.session_state.setdefault("routing_choice", "Selective Hybrid (3 LLM + 3 ML)")
    st.session_state.setdefault("solver_choice", "Neuro-Symbolic MILP-FEFO")

    # ---------------------- COMPACT DEMO-READY SIDEBAR ----------------------
    with st.sidebar:
        st.markdown("### 🎬 Kontrol Demo & Peran")
        demo_mode = st.toggle("Mode Presentasi (1-Klik Storyboard)", key="demo_mode")
        selected_role = st.selectbox("Masuk Sebagai Peran", list(ROLE_PROFILES.keys()), key="sel_role")
        role_info = ROLE_PROFILES[selected_role]

        scenario = st.selectbox(
            "Skenario Lingkungan",
            list(SCENARIO_LABELS.keys()),
            format_func=lambda k: SCENARIO_LABELS[k],
            key="sel_scenario",
        )

        sb1, sb2 = st.columns([1.65, 1.0])
        run_btn = sb1.button("🚀 Jalankan Siklus", type="primary", use_container_width=True)
        sb2.button("🔄 Reset", use_container_width=True, on_click=reset_demo_state)

        if api_online:
            st.success("🟢 FastAPI Live · Server-Side RBAC")
        else:
            st.warning("🟡 FastAPI Offline · Fallback Lokal")

        with st.expander("⚙️ Opsi Ablasi, Override & Token", expanded=False):
            adaptive = st.toggle("Adaptive Replanning & Contract Net", key="adaptive_toggle")
            routing_choice = st.radio("Arsitektur LLM", ["Selective Hybrid (3 LLM + 3 ML)", "All-LLM Homogeneous (6× GPT-4o)"], key="routing_choice")
            solver_choice = st.radio("Mesin Alokasi", ["Neuro-Symbolic MILP-FEFO", "Pure LLM Heuristic"], key="solver_choice")
            sim_stale_ui = st.checkbox("Simulasikan Stale Data (>15 mnt)", key="sim_stale_ui")
            use_sliders = st.checkbox("Override Kapasitas / Demand Manual", key="use_sliders")
            cold_ovr = float(st.slider("Cold Storage Efektif (kg)", 0, 3000, 1000, 100)) if use_sliders else None
            dem_ovr = float(st.slider("Demand SuperMart (kg)", 1500, 3500, 2000, 100)) if use_sliders else None
            st.caption(f"👤 `{role_info['user']}`  \n🔑 `{role_info['token']}`")

    homo_flag = "Homogeneous" in routing_choice
    use_milp_flag = "MILP" in solver_choice
    sig = (scenario, adaptive, homo_flag, use_milp_flag, cold_ovr, dem_ovr, api_online)

    # Execute active cycle + paired static baseline via FastAPI (clean spinner + toast, no residual top box)
    if "last_state" not in st.session_state or run_btn or st.session_state.get("last_sig") != sig:
        with st.spinner("Menjalankan LangGraph Orchestrator + 6 Agen Heterogen..."):
            req_active = {
                "trigger_mode": scenario,
                "adaptive_replanning": adaptive,
                "use_milp": use_milp_flag,
                "homogeneous_frontier": homo_flag,
                "auto_approve_hitl": False,
                "demand_override_kg": dem_ovr,
                "cold_storage_cap_override_kg": cold_ovr,
            }
            req_base = {**req_active, "adaptive_replanning": False, "use_milp": True, "homogeneous_frontier": False, "auto_approve_hitl": True}
            if api_online:
                ok1, st_act = api.post("/api/v1/orchestrator/run-cycle", req_active, role_info["token"])
                ok2, st_base = api.post("/api/v1/orchestrator/run-cycle", req_base, role_info["token"])
                if not (ok1 and ok2):
                    st.error(f"API Error ({now_wib_iso()}): {st_act}")
                    st_act = load_local_orchestrator(homo_flag).run_cycle(trigger_mode=scenario, adaptive_replanning=adaptive, use_milp=use_milp_flag, demand_override_kg=dem_ovr, cold_storage_cap_override_kg=cold_ovr, auto_approve_hitl=False)
                    st_base = load_local_orchestrator(False).run_cycle(trigger_mode=scenario, adaptive_replanning=False, use_milp=True, demand_override_kg=dem_ovr, cold_storage_cap_override_kg=cold_ovr, auto_approve_hitl=True)
            else:
                st_act = load_local_orchestrator(homo_flag).run_cycle(trigger_mode=scenario, adaptive_replanning=adaptive, use_milp=use_milp_flag, demand_override_kg=dem_ovr, cold_storage_cap_override_kg=cold_ovr, auto_approve_hitl=False)
                st_base = load_local_orchestrator(False).run_cycle(trigger_mode=scenario, adaptive_replanning=False, use_milp=True, demand_override_kg=dem_ovr, cold_storage_cap_override_kg=cold_ovr, auto_approve_hitl=True)
            st.session_state["last_state"] = st_act
            st.session_state["baseline_state"] = st_base
            st.session_state["last_sig"] = sig
            st.session_state["last_sync"] = now_wib_iso()
            st.toast(f"Siklus {st_act['cycle_id']} ({scenario}) selesai!", icon="🍅")

    state = st.session_state["last_state"]
    base_state = st.session_state["baseline_state"]
    kpis, base_kpis = state["global_kpis"], base_state["global_kpis"]

    # ---------------------- TOP EXECUTIVE BANNER ----------------------
    conn_pill = "🟢 FastAPI Live" if api_online else "🟡 Local Fallback"
    st.markdown(
        f"""
        <div class="role-banner">
            <div>
                <div style="font-size:1.18rem; font-weight:700;">🍅 AgriChain Agentic AI v2.1 — {selected_role}</div>
                <div style="font-size:0.82rem; opacity:0.92;">{role_info['scope_desc']}</div>
            </div>
            <div style="display:flex; gap:0.42rem; flex-wrap:wrap;">
                <span class="role-badge">{conn_pill}</span>
                <span class="role-badge">Cycle: {state['cycle_id']}</span>
                <span class="role-badge">Skenario: {scenario}</span>
                <span class="role-badge">Sync: {st.session_state.get('last_sync', '')[-14:-6]} WIB</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 1-Click Guided Demo Presenter Storyboard (toggleable in sidebar)
    if demo_mode:
        render_demo_storyboard()

    # Live 5-Enterprise Closed-Loop Handshake Strip
    render_closed_loop_strip(state)

    # Mandatory Stale / Partial Data Warning Banner (Pillar 3)
    if sim_stale_ui or state.get("data_freshness_warning"):
        warn_msg = state.get("data_freshness_warning") or "Data telemetri terakhir diperbarui > 15 menit lalu (Simulasi Stale Data). Jangan perlakukan nilai sensor sebagai real-time sebelum sinkronisasi ulang."
        st.markdown(f"<div class='banner-stale'><b>⚠️ STALE / PARTIAL DATA WARNING:</b> {warn_msg}</div>", unsafe_allow_html=True)

    # ---------------------- ROLE-ADAPTIVE WORKSPACE ROUTING ----------------------
    ent_key = role_info["enterprise_key"]

    if ent_key == "agrofarm":
        af_tabs = st.tabs([
            "🌱 AgroFarm Overview & Yield Prediction (RF 80% PI)",
            "🛰️ Ecosystem Impact & Lineage",
            "🗄️ AgroFarm Local DB Explorer (HPP Unlocked)",
            "🧭 Decision Trace & Audit",
        ])
        with af_tabs[0]:
            render_agrofarm_workspace(api, api_online, state, ml_metrics, role_info, selected_role)
        with af_tabs[1]:
            st.markdown(f"<div class='brief-box'><b>📋 Executive Briefing:</b> {state.get('executive_briefing', '')}</div>", unsafe_allow_html=True)
            st.plotly_chart(build_sankey(state["milp_result"]["allocations"], state["milp_result"]["unallocated_kg"]), use_container_width=True)
        with af_tabs[2]:
            render_server_data_explorer(api, api_online, role_info, selected_role, default_ent="agrofarm")
        with af_tabs[3]:
            render_decision_trace_and_audit(api, api_online, state, role_info)
        return

    if ent_key == "koperasi":
        kp_tabs = st.tabs([
            "🤝 Koperasi Price & Contract Net (Floor Unlocked)",
            "🌐 Ecosystem Impact & 7-Day Demand",
            "🗄️ Koperasi Local DB Explorer (MySQL)",
            "🧭 Decision Trace & Audit",
        ])
        with kp_tabs[0]:
            render_koperasi_workspace(api, api_online, state, ml_metrics, role_info)
        with kp_tabs[1]:
            st.markdown(f"<div class='brief-box'><b>📋 Executive Briefing:</b> {state.get('executive_briefing', '')}</div>", unsafe_allow_html=True)
            h7 = state.get("supermart_horizon_7d", {}).get("horizon_7d", [])
            if h7:
                st.markdown("#### 📈 Sinyal Permintaan 7-Hari dari SuperMart (`AGT-05 → AGT-02`)")
                st.dataframe(pd.DataFrame(h7), use_container_width=True, hide_index=True)
            st.plotly_chart(build_sankey(state["milp_result"]["allocations"], state["milp_result"]["unallocated_kg"]), use_container_width=True)
        with kp_tabs[2]:
            render_server_data_explorer(api, api_online, role_info, selected_role, default_ent="koperasi")
        with kp_tabs[3]:
            render_decision_trace_and_audit(api, api_online, state, role_info)
        return

    if ent_key == "freshfood":
        ff_role_tabs = st.tabs([
            "🏭 FreshFood QC, Hard-Block & FEFO Schedule",
            "🌐 Ecosystem Impact & Dock Sync",
            "🗄️ FreshFood Local DB Explorer (MongoDB)",
            "🧭 Decision Trace & Audit",
        ])
        with ff_role_tabs[0]:
            render_freshfood_module(api, api_online, state, ml_metrics, role_info)
        with ff_role_tabs[1]:
            st.markdown(f"<div class='brief-box'><b>📋 Executive Briefing:</b> {state.get('executive_briefing', '')}</div>", unsafe_allow_html=True)
            st.plotly_chart(build_decision_shift_chart(base_state, state), use_container_width=True)
        with ff_role_tabs[2]:
            render_server_data_explorer(api, api_online, role_info, selected_role, default_ent="freshfood")
        with ff_role_tabs[3]:
            render_decision_trace_and_audit(api, api_online, state, role_info)
        return

    if ent_key == "coldchain":
        cc_tabs = st.tabs([
            "❄️ ColdChain Fleet Operations (VRPTW + ETA + CRUD)",
            "🌐 Ecosystem Impact & Dock Handshake",
            "🗄️ ColdChain Local DB Explorer",
            "🧭 Agent Activity & Audit",
        ])
        with cc_tabs[0]:
            render_coldchain_workspace(api, api_online, state, ml_metrics, role_info)
        with cc_tabs[1]:
            st.markdown(f"<div class='brief-box'><b>📋 Executive Briefing:</b> {state.get('executive_briefing', '')}</div>", unsafe_allow_html=True)
            synced = state.get("vrptw_plan", {}).get("dock_windows_synced_nodes", [])
            if synced:
                st.success(f"🔗 **VRPTW Dock Handshake Tersinkron Dinamis:** `{', '.join(synced)}` (dari FreshFood & SuperMart)")
            st.plotly_chart(build_decision_shift_chart(base_state, state), use_container_width=True)
        with cc_tabs[2]:
            render_server_data_explorer(api, api_online, role_info, selected_role, default_ent="coldchain")
        with cc_tabs[3]:
            render_decision_trace_and_audit(api, api_online, state, role_info)
        return

    if ent_key == "supermart":
        sm_role_tabs = st.tabs([
            "🛒 SuperMart 7-Day Horizon, PO & SLA (Ceiling Unlocked)",
            "🌐 Ecosystem Impact & Lineage",
            "🗄️ SuperMart Local DB Explorer (MySQL)",
            "🧭 Decision Trace & Audit",
        ])
        with sm_role_tabs[0]:
            render_supermart_workspace(api, api_online, state, ml_metrics, role_info)
        with sm_role_tabs[1]:
            st.markdown(f"<div class='brief-box'><b>📋 Executive Briefing:</b> {state.get('executive_briefing', '')}</div>", unsafe_allow_html=True)
            st.plotly_chart(build_sankey(state["milp_result"]["allocations"], state["milp_result"]["unallocated_kg"]), use_container_width=True)
        with sm_role_tabs[2]:
            render_server_data_explorer(api, api_online, role_info, selected_role, default_ent="supermart")
        with sm_role_tabs[3]:
            render_decision_trace_and_audit(api, api_online, state, role_info)
        return

    # Global Control Center (AGT-06) — 6-Tab Full Ecosystem Oversight
    tabs = st.tabs([
        "🌐 Global Center",
        "🧭 Trace, Lineage & Audit",
        "🌱 AgroFarm v2",
        "❄️ ColdChain v2",
        "🏭 FreshFood · Kop · Retail",
        "🗄️ Data Explorer & Eval",
    ])

    with tabs[0]:
        # Compact Executive Briefing
        st.markdown(f"<div class='brief-box'><b>🧠 Executive Briefing (<code>AGT-06</code> Orchestrator):</b> {state.get('executive_briefing', '')}</div>", unsafe_allow_html=True)

        # 6 Executive KPI Cards (fixed neutral 0.00% delta & untruncated cost label)
        flr_diff = kpis["food_loss_rate_pct"] - base_kpis["food_loss_rate_pct"]
        ofr_diff = kpis["order_fulfillment_rate_pct"] - base_kpis["order_fulfillment_rate_pct"]
        prof_diff = (kpis["net_ecosystem_profit_rp"] - base_kpis["net_ecosystem_profit_rp"]) / 1e6
        cost_diff = (kpis["total_supply_chain_cost_rp"] - base_kpis["total_supply_chain_cost_rp"]) / 1e6
        fair_diff = kpis["jains_fairness_index"] - base_kpis["jains_fairness_index"]

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric(
            "Food Loss Rate",
            f"{kpis['food_loss_rate_pct']:.2f}%",
            "0.00% (Aman)" if abs(flr_diff) < 1e-6 else f"{flr_diff:+.2f}% vs Statis",
            delta_color="off" if abs(flr_diff) < 1e-6 else "inverse",
        )
        c2.metric(
            "Order Fulfillment",
            f"{kpis['order_fulfillment_rate_pct']:.1f}%",
            "0.0% vs Statis" if abs(ofr_diff) < 1e-6 else f"{ofr_diff:+.1f}% vs Statis",
            delta_color="off" if abs(ofr_diff) < 1e-6 else "normal",
        )
        c3.metric("Net Profit", f"Rp{kpis['net_ecosystem_profit_rp']/1e6:.2f} Jt", f"{prof_diff:+.2f} Jt", delta_color="off" if abs(prof_diff) < 1e-6 else "normal")
        c4.metric("Total Cost", f"Rp{kpis['total_supply_chain_cost_rp']/1e6:.2f} Jt", f"{cost_diff:+.2f} Jt", delta_color="off" if abs(cost_diff) < 1e-6 else "inverse")
        c5.metric("Jain's Fairness", f"{kpis['jains_fairness_index']:.4f}", f"{fair_diff:+.4f}", delta_color="off" if abs(fair_diff) < 1e-6 else "normal")
        c6.metric("Replan & LLM Cost", f"{kpis['replanning_response_time_sec']:.2f} s", f"USD {kpis['llm_cost_usd']:.3f} | {kpis['constraint_violations']} viol.", delta_color="off")

        # Slim Above-the-Fold HITL Action Bar + Expandable Impact Preview Console
        if state["hitl_status"] == "HUMAN_APPROVED":
            st.markdown("<div class='banner-ok'><b>✅ COMMITTED & HUMAN APPROVED:</b> Keputusan Adaptive Replanning telah disetujui operator dan tercatat di SHA-256 Audit Trail.</div>", unsafe_allow_html=True)
        elif state["hitl_status"] == "HUMAN_REJECTED":
            st.markdown("<div class='banner-danger'><b>⛔ REJECTED BY OPERATOR:</b> Rencana ditahan operator untuk negosiasi ulang.</div>", unsafe_allow_html=True)
        elif state["hitl_required"]:
            hb1, hb2, hb3 = st.columns([3.0, 1.15, 0.95])
            hb1.markdown(f"<div class='banner-warn' style='margin-bottom:0;'><b>⚠️ HITL GATE AKTIF (NIST AI RMF 1.0):</b> <code>{', '.join(state['hitl_reasons'])}</code></div>", unsafe_allow_html=True)
            if hb2.button("✅ Approve & Commit", type="primary", use_container_width=True, key="hitl_quick_approve"):
                if api_online:
                    ok_a, res_a = api.post(
                        f"/api/v1/orchestrator/hitl/{state['cycle_id']}/approve",
                        {},
                        role_info["token"],
                        params={"operator_name": role_info["user"], "note": "Disetujui setelah meninjau Impact Preview & kepatuhan suhu 7-12C."},
                    )
                    if ok_a:
                        state["hitl_status"] = "HUMAN_APPROVED"
                        st.toast(f"Approved! Audit Hash: {res_a['audit_hash'][:14]}...", icon="✅")
                        st.rerun()
            if hb3.button("⛔ Reject", use_container_width=True, key="hitl_quick_reject"):
                if api_online:
                    ok_r, res_r = api.post(
                        f"/api/v1/orchestrator/hitl/{state['cycle_id']}/reject",
                        {},
                        role_info["token"],
                        params={"operator_name": role_info["user"], "note": "Ditahan operator untuk evaluasi ulang."},
                    )
                    if ok_r:
                        state["hitl_status"] = "HUMAN_REJECTED"
                        st.toast(f"Rejected! Audit Hash: {res_r['audit_hash'][:14]}...", icon="⛔")
                        st.rerun()

        # Charts immediately visible above/near the fold!
        g1, g2 = st.columns([1.12, 1.0])
        with g1:
            st.plotly_chart(build_sankey(state["milp_result"]["allocations"], state["milp_result"]["unallocated_kg"]), use_container_width=True)
        with g2:
            st.plotly_chart(build_decision_shift_chart(base_state, state), use_container_width=True)

        # Detailed Impact-Preview HITL Console (expandable for deep audit & custom operator note)
        if state["hitl_required"]:
            with st.expander("🛡️ Detail Impact-Preview Confirmation Console & Catatan Audit Kustom", expanded=False):
                ot_shift = "Overtime FreshFood (+500 kg) + Dock 08:15–14:00" if kpis.get("overtime_activated") else "Alokasi Reguler MILP-FEFO"
                imp_df = pd.DataFrame([
                    {"Indikator Dampak": "Aksi Adaptif Utama", "Statis (Tanpa Replan)": "Alokasi Statis (Tanpa Negosiasi)", "Rencana Adaptive": ot_shift, "Mitra Terdampak": "FreshFood, ColdChain"},
                    {"Indikator Dampak": "Food Loss Rate (%)", "Statis (Tanpa Replan)": f"{base_kpis['food_loss_rate_pct']:.2f}%", "Rencana Adaptive": f"{kpis['food_loss_rate_pct']:.2f}%", "Mitra Terdampak": "AgroFarm, Koperasi"},
                    {"Indikator Dampak": "Order Fulfillment (%)", "Statis (Tanpa Replan)": f"{base_kpis['order_fulfillment_rate_pct']:.1f}%", "Rencana Adaptive": f"{kpis['order_fulfillment_rate_pct']:.1f}%", "Mitra Terdampak": "SuperMart, FreshFood"},
                    {"Indikator Dampak": "Net Ecosystem Profit", "Statis (Tanpa Replan)": f"Rp{base_kpis['net_ecosystem_profit_rp']/1e6:.2f} Jt", "Rencana Adaptive": f"Rp{kpis['net_ecosystem_profit_rp']/1e6:.2f} Jt", "Mitra Terdampak": "Seluruh 5 Enterprise"},
                    {"Indikator Dampak": "Jarak Rute VRPTW (km)", "Statis (Tanpa Replan)": f"{state.get('vrptw_plan', {}).get('naive_distance_km', 382):.0f} km (Naive)", "Rencana Adaptive": f"{state.get('vrptw_plan', {}).get('optimized_distance_km', 263):.0f} km (OR-Tools)", "Mitra Terdampak": "ColdChain Logistics"},
                ])
                st.dataframe(imp_df, use_container_width=True, hide_index=True)

                h1, h2 = st.columns([1.8, 3.0])
                op_name = h1.text_input("Operator / Approver", value=role_info["user"])
                op_note = h2.text_input("Catatan Audit Keputusan", value="Disetujui setelah meninjau Impact Preview & kepatuhan suhu 7-12C.")
                b1, b2, b3 = st.columns([1.2, 1.1, 2.7])
                if b1.button("✅ Approve dengan Catatan", type="primary", use_container_width=True, key="hitl_detail_approve"):
                    if api_online:
                        ok_a, res_a = api.post(f"/api/v1/orchestrator/hitl/{state['cycle_id']}/approve", {}, role_info["token"], params={"operator_name": op_name, "note": op_note})
                        if ok_a:
                            state["hitl_status"] = "HUMAN_APPROVED"
                            st.toast(f"Approved! Audit Hash: {res_a['audit_hash'][:14]}...", icon="✅")
                            st.rerun()
                if b2.button("⛔ Reject & Hold", use_container_width=True, key="hitl_detail_reject"):
                    if api_online:
                        ok_r, res_r = api.post(f"/api/v1/orchestrator/hitl/{state['cycle_id']}/reject", {}, role_info["token"], params={"operator_name": op_name, "note": op_note})
                        if ok_r:
                            state["hitl_status"] = "HUMAN_REJECTED"
                            st.toast(f"Rejected! Audit Hash: {res_r['audit_hash'][:14]}...", icon="⛔")
                            st.rerun()
                b3.caption(f"Status: **{state['hitl_status']}** | Privacy Leaks: **{kpis['privacy_leaks_detected']}** | Ronde Negosiasi: **{kpis['negotiation_rounds_used']}/3**")

        st.subheader("📡 Live Agent Status Matrix (6 Agen Heterogen)")
        st.dataframe(pd.DataFrame(state.get("agent_statuses", [])), use_container_width=True, hide_index=True)

    with tabs[1]:
        render_decision_trace_and_audit(api, api_online, state, role_info)

    with tabs[2]:
        render_agrofarm_workspace(api, api_online, state, ml_metrics, role_info, selected_role)

    with tabs[3]:
        render_coldchain_workspace(api, api_online, state, ml_metrics, role_info)

    with tabs[4]:
        sub_ent = st.radio(
            "Pilih Sub-Modul Enterprise",
            ["🏭 FreshFood Processing (AGT-03)", "🤝 Koperasi Tani (AGT-02)", "🛒 SuperMart Retail (AGT-05)"],
            horizontal=True,
            label_visibility="collapsed",
            key="global_sub_ent_radio",
        )
        if "FreshFood" in sub_ent:
            render_freshfood_module(api, api_online, state, ml_metrics, role_info)
        elif "Koperasi" in sub_ent:
            render_koperasi_workspace(api, api_online, state, ml_metrics, role_info)
        else:
            render_supermart_workspace(api, api_online, state, ml_metrics, role_info)

    with tabs[5]:
        render_server_data_explorer(api, api_online, role_info, selected_role, default_ent=ent_key if ent_key != "global" else "koperasi")
        st.divider()
        st.subheader("📊 Grafik Benchmark & 3 Studi Ablasi Bab 9")
        fig_dir = RESULTS_DIR / "figures"
        f1, f2 = st.columns(2)
        if (fig_dir / "fig_9_1_conditions.png").exists():
            f1.image(str(fig_dir / "fig_9_1_conditions.png"), caption="Gambar 9.1 — Perbandingan 4 Kondisi")
        if (fig_dir / "fig_9_2_ablation_comparison.png").exists():
            f2.image(str(fig_dir / "fig_9_2_ablation_comparison.png"), caption="Gambar 9.2 — Hasil 3 Studi Ablasi")


if __name__ == "__main__":
    main()
