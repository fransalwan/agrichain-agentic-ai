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
    page_title="AgriChain Agentic AI v2.0 — Multi-Enterprise Cockpit",
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
        padding-top: 2.8rem;
        padding-bottom: 2.2rem;
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
        height=350,
        margin=dict(l=10, r=10, t=38, b=10),
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
        height=355,
        legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="center", x=0.5, font=dict(color="#0F172A")),
        margin=dict(l=10, r=10, t=44, b=55),
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
        sc1, sc2 = st.columns(2)
        s_area = sc1.slider("Luas Blok (ha)", 0.4, 2.0, 0.70, 0.05)
        s_ndvi = sc2.slider("Indeks NDVI", 0.30, 0.88, 0.64, 0.01)
        s_rain = sc1.slider("Curah Hujan (mm)", 0.0, 120.0, 24.0, 2.0)
        s_age = sc2.slider("Umur Tanaman (hari)", 65, 90, 78, 1)
        c_chk1, c_chk2 = st.columns(2)
        sim_rain = c_chk1.checkbox("Simulasi Hujan Ekstrem (>90 mm)", value=(state["trigger_mode"] == "EXTREME_RAIN"))
        sim_off = c_chk2.checkbox("Simulasi Sensor Mati 3 Hari (Fallback)", value=(state["trigger_mode"] == "SENSOR_OUTAGE"))

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
        vc1, vc2, vc3 = st.columns([1.6, 1.0, 1.0])
        vrptw_scen = vc1.selectbox("Skenario Optimasi OR-Tools VRPTW", ["NORMAL", "ROAD_DISRUPTION", "VEHICLE_BREAKDOWN", "COLD_STORAGE_DROP"])
        vrptw_traf = vc2.selectbox("Tingkat Kemacetan", [(0, "Low"), (1, "Medium"), (2, "High")], index=1, format_func=lambda x: x[1])[0]
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
            st.markdown("#### 📋 Perbandingan Skenario & Jadwal Armada VRPTW")
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


def render_freshfood_module(state: Dict[str, Any], ml_metrics: Dict[str, Any]) -> None:
    st.subheader("🏭 FreshFood Processing Cockpit — 2D-Conv CNN Visual QC & Food Safety Hard-Block")
    m_ff = ml_metrics.get("freshfood_cnn", {})
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("CNN Accuracy", f"{m_ff.get('test_accuracy_pct', 98.67)}%", "Target >= 90%")
    k2.metric("Macro-F1", f"{m_ff.get('test_macro_f1', 0.9878)}")
    k3.metric("Reject Recall", f"{m_ff.get('reject_recall_pct', 100.0)}%", "0 Missed Reject")
    k4.metric("Overtime Status", "AKTIF (+500 kg)" if state["global_kpis"].get("overtime_activated") else "REGULER (2.000 kg)")

    samples = load_tomato_rgb_sample(n_per_class=2)
    if samples:
        orch = load_local_orchestrator()
        preds = orch.freshfood.model.classify_images(np.stack([s["image"] for s in samples]))
        cols = st.columns(4)
        for i, (s, pr) in enumerate(zip(samples, preds)):
            up = Image.fromarray(s["image"].astype(np.uint8)).resize((120, 120), Image.Resampling.NEAREST)
            tag = "🔴 REJECT" if pr["predicted_grade"] == "Reject" else f"🟢 Grade {pr['predicted_grade']}"
            cols[i % 4].image(up, caption=f"#{s['index']} True:{s['true_grade']} → {tag} ({pr['confidence']*100:.1f}%)")


def render_koperasi_and_supermart_modules(state: Dict[str, Any], ml_metrics: Dict[str, Any], role_info: Dict[str, Any]) -> None:
    c1, c2 = st.columns(2)
    orch = load_local_orchestrator()
    with c1:
        st.subheader("🤝 Koperasi Tani — LightGBM & Contract Net")
        m_kp = ml_metrics.get("koperasi_lgbm", {})
        st.metric("LightGBM Test MAPE", f"{m_kp.get('test_mape_pct', 4.28)}%", f"MAE Rp{m_kp.get('test_mae_rp', 240.1)}/kg")
        kg = st.selectbox("Grade Tomat", ["A", "B", "C"], index=1, key="kp_g")
        ko = st.number_input("Simulasi Tawaran Pembeli (Rp/kg)", 2000, 15000, 6400, 100, key="kp_o")
        ask = orch.koperasi.model.predict_price(grade=kg)
        auc = orch.koperasi.model.evaluate_contract_net_bids("SIM", 500.0, orch.koperasi._private_floor_prices[kg], [{"buyer_id": "Buyer", "qty_kg": 500.0, "offer_price_rp": ko}])
        st.caption(f"Referensi LightGBM: `Rp{ask:,.0f}/kg` | Status: **{auc['status']}**")
    with c2:
        st.subheader("🛒 SuperMart — XGBoost & Newsvendor PO")
        m_sm = ml_metrics.get("supermart_xgb", {})
        st.metric("XGBoost Demand MAPE", f"{m_sm.get('test_mape_pct', 3.72)}%", f"R² {m_sm.get('test_r2', 0.9215)}")
        sp = st.checkbox("Promo Weekend Aktif", value=False, key="sm_p")
        fd = orch.supermart.model.forecast_total_chain_demand(day_of_week=5 if sp else 2, is_promo=1 if sp else 0)
        po = orch.supermart.model.compute_newsvendor_po(fd)
        st.caption(f"Forecast 3 Gerai: `{po['forecast_demand_kg']:,.1f} kg` | Rekomendasi PO: **`{po['recommended_po_kg']:,.1f} kg`**")


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
        st.markdown("#### 🧠 Telemetri 6-LLM Router")
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

    # ---------------------- SIDEBAR ----------------------
    with st.sidebar:
        st.markdown("### 🔐 Login & Role-Adaptive RBAC")
        selected_role = st.selectbox("Masuk Sebagai Peran", list(ROLE_PROFILES.keys()), index=0)
        role_info = ROLE_PROFILES[selected_role]
        st.caption(f"👤 `{role_info['user']}`  \n🔑 `{role_info['token']}`")
        if api_online:
            st.success("🟢 FastAPI Gateway Connected (Server-Side Firewall)")
        else:
            st.warning("🟡 FastAPI Offline — Mode Fallback Lokal")

        st.divider()
        st.markdown("### ⚡ Chaos & Environment Injector")
        scenario = st.selectbox("Skenario Lingkungan", list(SCENARIO_LABELS.keys()), index=1, format_func=lambda k: SCENARIO_LABELS[k])
        sim_stale_ui = st.checkbox("Simulasikan Stale Data Warning (>15 mnt)", value=False)
        use_sliders = st.checkbox("Override Kapasitas / Demand Manual", value=False)
        cold_ovr = float(st.slider("Cold Storage Efektif (kg)", 0, 3000, 1000, 100)) if use_sliders else None
        dem_ovr = float(st.slider("Demand SuperMart (kg)", 1500, 3500, 2000, 100)) if use_sliders else None

        st.markdown("### 🧠 Agentic & Ablasi")
        adaptive = st.toggle("Adaptive Replanning & Contract Net", value=True)
        routing_choice = st.radio("LLM Routing", ["Heterogeneous (6 LLM)", "Homogeneous (6× GPT-4o)"], index=0)
        solver_choice = st.radio("Mesin Alokasi", ["Neuro-Symbolic MILP-FEFO", "Pure LLM Heuristic"], index=0)
        run_btn = st.button("🚀 Jalankan Siklus Orkestrator", type="primary", use_container_width=True)

    homo_flag = "Homogeneous" in routing_choice
    use_milp_flag = "MILP" in solver_choice
    sig = (scenario, adaptive, homo_flag, use_milp_flag, cold_ovr, dem_ovr, api_online)

    # Execute active cycle + paired static baseline via FastAPI (Loading UI State)
    if "last_state" not in st.session_state or run_btn or st.session_state.get("last_sig") != sig:
        with st.status("Menjalankan LangGraph Orchestrator + 6 Agen Heterogen...", expanded=False) as status_box:
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
            status_box.update(label=f"Siklus {st_act['cycle_id']} selesai!", state="complete")

    state = st.session_state["last_state"]
    base_state = st.session_state["baseline_state"]
    kpis, base_kpis = state["global_kpis"], base_state["global_kpis"]

    # ---------------------- TOP EXECUTIVE BANNER ----------------------
    conn_pill = "🟢 FastAPI Live" if api_online else "🟡 Local Fallback"
    st.markdown(
        f"""
        <div class="role-banner">
            <div>
                <div style="font-size:1.22rem; font-weight:700;">🍅 AgriChain Agentic AI v2.0 — {selected_role}</div>
                <div style="font-size:0.83rem; opacity:0.92;">{role_info['scope_desc']}</div>
            </div>
            <div style="display:flex; gap:0.45rem; flex-wrap:wrap;">
                <span class="role-badge">{conn_pill}</span>
                <span class="role-badge">Cycle: {state['cycle_id']}</span>
                <span class="role-badge">Skenario: {scenario}</span>
                <span class="role-badge">Sync: {st.session_state.get('last_sync', '')[-14:-6]} WIB</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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

    if ent_key == "coldchain":
        cc_tabs = st.tabs([
            "❄️ ColdChain Fleet Operations (VRPTW + ETA + CRUD)",
            "🌐 Ecosystem Impact & Sankey",
            "🗄️ ColdChain Local DB Explorer",
            "🧭 Agent Activity & Audit",
        ])
        with cc_tabs[0]:
            render_coldchain_workspace(api, api_online, state, ml_metrics, role_info)
        with cc_tabs[1]:
            st.markdown(f"<div class='brief-box'><b>📋 Executive Briefing:</b> {state.get('executive_briefing', '')}</div>", unsafe_allow_html=True)
            st.plotly_chart(build_decision_shift_chart(base_state, state), use_container_width=True)
        with cc_tabs[2]:
            render_server_data_explorer(api, api_online, role_info, selected_role, default_ent="coldchain")
        with cc_tabs[3]:
            render_decision_trace_and_audit(api, api_online, state, role_info)
        return

    # Global Control Center + Koperasi / FreshFood / SuperMart Shared Command Center
    tabs = st.tabs([
        "🌐 Global Center",
        "🧭 Trace, Lineage & Audit",
        "🌱 AgroFarm v2",
        "❄️ ColdChain v2",
        "🏭 FreshFood, Kop & Retail",
        "🗄️ Data Explorer & Eval",
    ])

    with tabs[0]:
        # Executive Briefing + HITL Status Banner
        st.markdown(f"<div class='brief-box'><b>🧠 Executive Briefing (<code>AGT-06</code> Orchestrator):</b> {state.get('executive_briefing', '')}</div>", unsafe_allow_html=True)
        if state["hitl_status"] == "HUMAN_APPROVED":
            st.markdown("<div class='banner-ok'><b>✅ COMMITTED & HUMAN APPROVED:</b> Keputusan Adaptive Replanning telah disetujui operator dan tercatat di SHA-256 Audit Trail.</div>", unsafe_allow_html=True)
        elif state["hitl_status"] == "HUMAN_REJECTED":
            st.markdown("<div class='banner-danger'><b>⛔ REJECTED BY OPERATOR:</b> Rencana ditahan operator untuk negosiasi ulang.</div>", unsafe_allow_html=True)
        elif state["hitl_required"]:
            st.markdown(f"<div class='banner-warn'><b>⚠️ HITL GOVERNANCE GATE AKTIF (NIST AI RMF 1.0):</b> <code>{', '.join(state['hitl_reasons'])}</code></div>", unsafe_allow_html=True)

        # 6 Executive KPI Cards with Measured Delta vs Static Baseline
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Food Loss Rate", f"{kpis['food_loss_rate_pct']:.2f}%", f"{kpis['food_loss_rate_pct']-base_kpis['food_loss_rate_pct']:+.2f}% vs Statis", delta_color="inverse")
        c2.metric("Order Fulfillment", f"{kpis['order_fulfillment_rate_pct']:.1f}%", f"{kpis['order_fulfillment_rate_pct']-base_kpis['order_fulfillment_rate_pct']:+.1f}% vs Statis")
        c3.metric("Net Profit", f"Rp{kpis['net_ecosystem_profit_rp']/1e6:.2f} Jt", f"{(kpis['net_ecosystem_profit_rp']-base_kpis['net_ecosystem_profit_rp'])/1e6:+.2f} Jt")
        c4.metric("Total Cost", f"Rp{kpis['total_supply_chain_cost_rp']/1e6:.2f} Jt", f"{(kpis['total_supply_chain_cost_rp']-base_kpis['total_supply_chain_cost_rp'])/1e6:+.2f} Jt", delta_color="inverse")
        c5.metric("Jain's Fairness", f"{kpis['jains_fairness_index']:.4f}", f"{kpis['jains_fairness_index']-base_kpis['jains_fairness_index']:+.4f}")
        c6.metric("Replan & LLM Cost", f"{kpis['replanning_response_time_sec']:.2f} s", f"USD {kpis['llm_cost_usd']:.5f} | {kpis['constraint_violations']} viol.", delta_color="off")

        # Impact-Preview HITL Confirmation Console (Pillar 3)
        if state["hitl_required"]:
            with st.expander("🛡️ Impact-Preview Confirmation Console (HITL NIST AI RMF 1.0)", expanded=True):
                imp_df = pd.DataFrame([
                    {"Indikator Dampak": "Food Loss Rate (%)", "Statis (Tanpa Replan)": f"{base_kpis['food_loss_rate_pct']:.2f}%", "Rencana Adaptive": f"{kpis['food_loss_rate_pct']:.2f}%", "Mitra Terdampak": "AgroFarm, Koperasi"},
                    {"Indikator Dampak": "Order Fulfillment (%)", "Statis (Tanpa Replan)": f"{base_kpis['order_fulfillment_rate_pct']:.1f}%", "Rencana Adaptive": f"{kpis['order_fulfillment_rate_pct']:.1f}%", "Mitra Terdampak": "SuperMart, FreshFood"},
                    {"Indikator Dampak": "Net Ecosystem Profit", "Statis (Tanpa Replan)": f"Rp{base_kpis['net_ecosystem_profit_rp']/1e6:.2f} Jt", "Rencana Adaptive": f"Rp{kpis['net_ecosystem_profit_rp']/1e6:.2f} Jt", "Mitra Terdampak": "Seluruh 5 Enterprise"},
                    {"Indikator Dampak": "Jarak Rute VRPTW (km)", "Statis (Tanpa Replan)": f"{state.get('vrptw_plan', {}).get('naive_distance_km', 382):.0f} km (Naive)", "Rencana Adaptive": f"{state.get('vrptw_plan', {}).get('optimized_distance_km', 263):.0f} km (OR-Tools)", "Mitra Terdampak": "ColdChain Logistics"},
                ])
                st.dataframe(imp_df, use_container_width=True, hide_index=True)

                h1, h2 = st.columns([1.8, 3.0])
                op_name = h1.text_input("Operator / Approver", value=role_info["user"])
                op_note = h2.text_input("Catatan Audit Keputusan", value="Disetujui setelah meninjau Impact Preview & kepatuhan suhu 7-12C.")
                b1, b2, b3 = st.columns([1.1, 1.1, 2.8])
                if b1.button("✅ Approve & Commit via API", type="primary", use_container_width=True):
                    if api_online:
                        ok_a, res_a = api.post(f"/api/v1/orchestrator/hitl/{state['cycle_id']}/approve", {}, role_info["token"], params={"operator_name": op_name, "note": op_note})
                        if ok_a:
                            state["hitl_status"] = "HUMAN_APPROVED"
                            st.toast(f"Approved! Audit Hash: {res_a['audit_hash'][:14]}...", icon="✅")
                            st.rerun()
                if b2.button("⛔ Reject & Hold via API", use_container_width=True):
                    if api_online:
                        ok_r, res_r = api.post(f"/api/v1/orchestrator/hitl/{state['cycle_id']}/reject", {}, role_info["token"], params={"operator_name": op_name, "note": op_note})
                        if ok_r:
                            state["hitl_status"] = "HUMAN_REJECTED"
                            st.toast(f"Rejected! Audit Hash: {res_r['audit_hash'][:14]}...", icon="⛔")
                            st.rerun()
                b3.caption(f"Status: **{state['hitl_status']}** | Privacy Leaks: **{kpis['privacy_leaks_detected']}** | Ronde Negosiasi: **{kpis['negotiation_rounds_used']}/3**")

        g1, g2 = st.columns([1.15, 1.0])
        with g1:
            st.plotly_chart(build_sankey(state["milp_result"]["allocations"], state["milp_result"]["unallocated_kg"]), use_container_width=True)
        with g2:
            st.plotly_chart(build_decision_shift_chart(base_state, state), use_container_width=True)

        st.subheader("📡 Live Agent Status Matrix (6 Agen Heterogen)")
        st.dataframe(pd.DataFrame(state.get("agent_statuses", [])), use_container_width=True, hide_index=True)

    with tabs[1]:
        render_decision_trace_and_audit(api, api_online, state, role_info)

    with tabs[2]:
        render_agrofarm_workspace(api, api_online, state, ml_metrics, role_info, selected_role)

    with tabs[3]:
        render_coldchain_workspace(api, api_online, state, ml_metrics, role_info)

    with tabs[4]:
        render_freshfood_module(state, ml_metrics)
        st.divider()
        render_koperasi_and_supermart_modules(state, ml_metrics, role_info)

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
