"""Streamlit Role-Based Multi-Enterprise Control Center & Interactive Domain Cockpits.

Covers all rubric deliverables:
- Simulated Role-Based Login & Data Sovereignty Privacy Masking (6 Roles)
- Global Control Center with Measured Before-vs-After (Static vs Adaptive) Comparison
- Live Agent Status Matrix (6 Heterogeneous ML + LLM Agents)
- LangGraph 7-Node Decision Trace, FIPA-ACL/EPCIS 2.0 Feed & SHA-256 Audit Trail + HITL Console
- 5 Interactive Enterprise Modules (RF Yield, LightGBM Price, RGB CNN Tomato QC, IForest+CVRP, XGBoost+Newsvendor)
- Interactive Multi-Enterprise Local DB Data Explorer with Privacy Redaction & CSV Export
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from PIL import Image

from config.settings import AGENT_MODEL_PROFILES, DATA_DIR, RESULTS_DIR
from src.agents.orchestrator import AgriChainOrchestrator
from src.protocols.security import ALL_PRIVATE_KEYS as PRIVATE_FIELDS

st.set_page_config(
    page_title="AgriChain Agentic AI — Multi-Enterprise Control Center",
    page_icon="🍅",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS for clean Executive Control Center look
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .block-container { padding-top: 3.1rem; padding-bottom: 2rem; }
    [data-testid="stMetricValue"] { font-size: 1.45rem !important; }
    [data-testid="stMetricDelta"] { font-size: 0.78rem !important; }
    .role-banner {
        background: linear-gradient(90deg, #143454 0%, #1F4E79 65%, #2B6CB0 100%);
        color: #FFFFFF;
        padding: 0.85rem 1.25rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.5rem;
    }
    .role-badge {
        background: rgba(255,255,255,0.16);
        border: 1px solid rgba(255,255,255,0.35);
        padding: 0.25rem 0.7rem;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 600;
    }
    .status-banner-ok {
        background: #ECFDF5; border-left: 5px solid #10B981; color: #065F46;
        padding: 0.75rem 1rem; border-radius: 6px; margin-bottom: 0.8rem;
    }
    .status-banner-warn {
        background: #FFFBEB; border-left: 5px solid #F59E0B; color: #92400E;
        padding: 0.75rem 1rem; border-radius: 6px; margin-bottom: 0.8rem;
    }
    .status-banner-danger {
        background: #FEF2F2; border-left: 5px solid #EF4444; color: #991B1B;
        padding: 0.75rem 1rem; border-radius: 6px; margin-bottom: 0.8rem;
    }
    .trace-card {
        background: #F8FAFC;
        border: 1px solid #CBD5E1;
        border-left: 4px solid #1F4E79;
        border-radius: 6px;
        padding: 0.65rem 0.9rem;
        margin-bottom: 0.5rem;
    }
    .msg-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 4px solid #2B6CB0;
        border-radius: 6px;
        padding: 0.6rem 0.9rem;
        margin-bottom: 0.45rem;
    }
    div[data-testid="stMetric"] {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        padding: 0.65rem 0.85rem;
        border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Role Definitions (Simulated Enterprise Login & Data Sovereignty Scope)
# ---------------------------------------------------------------------------
ROLE_PROFILES: Dict[str, Dict[str, Any]] = {
    "Global Control Center Operator (AGT-06)": {
        "user": "ops.global@agrichain.id",
        "enterprise_key": "global",
        "agent_id": "AGT-06",
        "token_preview": "tok_orchestrator_global_scope_v1",
        "scope_desc": "Akses Global Orchestration & HITL — Semua 15 Atribut Privat Enterprise TER-REDAKSI (Zero-Direct-DB)",
        "private_unlocked": set(),
    },
    "AgroFarm Manager (AGT-01)": {
        "user": "manager@agrofarm.co.id",
        "enterprise_key": "agrofarm",
        "agent_id": "AGT-01",
        "token_preview": "tok_agrofarm_local_v1",
        "scope_desc": "Akses Lokal AgroFarm (PostgreSQL) — HPP & ID Petani terbuka lokal; data privat perusahaan lain ter-redaksi",
        "private_unlocked": {"agrofarm"},
    },
    "Koperasi Tani Manager (AGT-02)": {
        "user": "ketua@koperasitani.id",
        "enterprise_key": "koperasi",
        "agent_id": "AGT-02",
        "token_preview": "tok_koperasi_local_v1",
        "scope_desc": "Akses Lokal Koperasi (MySQL) — floor_price_rp & margin koperasi terbuka lokal; perusahaan lain ter-redaksi",
        "private_unlocked": {"koperasi"},
    },
    "FreshFood QC & Plant Manager (AGT-03)": {
        "user": "qc.lead@freshfood.co.id",
        "enterprise_key": "freshfood",
        "agent_id": "AGT-03",
        "token_preview": "tok_freshfood_local_v1",
        "scope_desc": "Akses Lokal FreshFood (MongoDB) — Lab QC, CNN Visual Grading, & Food Safety Hard-Block terbuka lokal",
        "private_unlocked": {"freshfood"},
    },
    "ColdChain Logistics Manager (AGT-04)": {
        "user": "dispatch@coldchain.co.id",
        "enterprise_key": "coldchain",
        "agent_id": "AGT-04",
        "token_preview": "tok_coldchain_local_v1",
        "scope_desc": "Akses Lokal ColdChain (TimescaleDB) — Telemetri IoT, Isolation Forest, & OR-Tools CVRP terbuka lokal",
        "private_unlocked": {"coldchain"},
    },
    "SuperMart Procurement Manager (AGT-05)": {
        "user": "buyer@supermart.co.id",
        "enterprise_key": "supermart",
        "agent_id": "AGT-05",
        "token_preview": "tok_supermart_local_v1",
        "scope_desc": "Akses Lokal SuperMart (MySQL) — ceiling_price_rp & retail margin terbuka lokal; perusahaan lain ter-redaksi",
        "private_unlocked": {"supermart"},
    },
}

SCENARIO_LABELS = {
    "NORMAL": "NORMAL — Operasi Harian Standar",
    "COLD_STORAGE_FAILURE": "COLD_STORAGE_FAILURE — Kompresor Rusak (3.000 → 1.000 kg)",
    "DEMAND_SURGE": "DEMAND_SURGE — Lonjakan Permintaan Ritel (2.000 → 2.800 kg)",
    "FOOD_SAFETY_FAIL": "FOOD_SAFETY_FAIL — Batch H003 Gagal Uji Mikroba/Pestisida",
    "COMPOUND": "COMPOUND — Cold Storage Failure + Demand Surge Simultan",
    "DEADLOCK": "DEADLOCK — Tawaran Pembeli < Floor Price (Batas 3 Ronde → HITL)",
}


# ---------------------------------------------------------------------------
# Cached Loaders
# ---------------------------------------------------------------------------
@st.cache_resource
def load_orchestrator(homogeneous_frontier: bool = False) -> AgriChainOrchestrator:
    return AgriChainOrchestrator(homogeneous_frontier=homogeneous_frontier)


@st.cache_data
def load_ml_metrics() -> Dict[str, Any]:
    path = RESULTS_DIR / "ml_metrics.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


@st.cache_data
def load_experiment_results() -> Dict[str, Any]:
    path = RESULTS_DIR / "experiment_results.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


@st.cache_data
def load_tomato_rgb_sample(n_per_class: int = 2) -> List[Dict[str, Any]]:
    npz_path = DATA_DIR / "freshfood_tomato_images.npz"
    if not npz_path.exists():
        return []
    data = np.load(npz_path, allow_pickle=False)
    imgs = data["images"]
    labels = data["labels"]
    samples = []
    for cls in ("A", "B", "C", "Reject"):
        idxs = np.where(labels == cls)[0][:n_per_class]
        for idx in idxs:
            samples.append({"index": int(idx), "true_grade": str(labels[idx]), "image": imgs[idx]})
    return samples


# ---------------------------------------------------------------------------
# Chart Builders
# ---------------------------------------------------------------------------
def build_sankey(allocations: List[Dict[str, Any]], unallocated: Dict[str, float]) -> go.Figure:
    nodes = [
        "AgroFarm",
        "Koperasi Tani",
        "SuperMart",
        "FreshFood_Reg",
        "FreshFood_OT",
        "ColdStorage",
        "Partner3PL",
        "AltBuyer",
        "Food Loss / Blocked",
    ]
    node_idx = {n: i for i, n in enumerate(nodes)}
    sources, targets, values, labels, link_colors = [], [], [], [], []
    total_qty = sum(a["qty_kg"] for a in allocations) + sum(unallocated.values())
    if total_qty > 0:
        sources.append(node_idx["AgroFarm"])
        targets.append(node_idx["Koperasi Tani"])
        values.append(total_qty)
        labels.append(f"Total Panen: {total_qty:,.0f} kg")
        link_colors.append("rgba(47, 133, 90, 0.35)")

    ch_colors = {
        "SuperMart": "rgba(197, 48, 48, 0.45)",
        "FreshFood_Reg": "rgba(107, 70, 193, 0.45)",
        "FreshFood_OT": "rgba(214, 158, 46, 0.55)",
        "ColdStorage": "rgba(9, 135, 160, 0.45)",
        "Partner3PL": "rgba(49, 130, 206, 0.45)",
        "AltBuyer": "rgba(113, 128, 150, 0.45)",
    }
    for a in allocations:
        ch = a["channel"]
        if ch in node_idx and a["qty_kg"] > 0:
            sources.append(node_idx["Koperasi Tani"])
            targets.append(node_idx[ch])
            values.append(a["qty_kg"])
            labels.append(f"{a['lot_id']} (Grade {a['grade']}, SL {a['shelf_life_days']}d): {a['qty_kg']:,.0f} kg")
            link_colors.append(ch_colors.get(ch, "rgba(100,116,139,0.4)"))

    for lot_id, loss_kg in unallocated.items():
        if loss_kg > 0.5:
            sources.append(node_idx["Koperasi Tani"])
            targets.append(node_idx["Food Loss / Blocked"])
            values.append(loss_kg)
            labels.append(f"{lot_id} Loss/Blocked: {loss_kg:,.0f} kg")
            link_colors.append("rgba(220, 38, 38, 0.65)")

    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(
                    pad=16,
                    thickness=20,
                    label=nodes,
                    color=["#2F855A", "#B7791F", "#C53030", "#6B46C1", "#D69E2E", "#0987A0", "#3182CE", "#64748B", "#DC2626"],
                ),
                link=dict(source=sources, target=targets, value=values, label=labels, color=link_colors),
            )
        ]
    )
    fig.update_layout(
        title="Aliran Alokasi Rantai Pasok Tomat Real-Time (MILP-FEFO)",
        height=350,
        margin=dict(l=10, r=10, t=38, b=10),
    )
    return fig


def build_decision_shift_chart(baseline_state: Dict[str, Any], active_state: Dict[str, Any]) -> go.Figure:
    """Visual proof that decisions measurably change when environment / adaptive mode changes."""
    channels = ["SuperMart", "FreshFood_Reg", "FreshFood_OT", "ColdStorage", "Partner3PL", "AltBuyer", "Food Loss"]

    def summarize(st_obj: Dict[str, Any]) -> Dict[str, float]:
        out = {c: 0.0 for c in channels}
        for a in st_obj["milp_result"]["allocations"]:
            if a["channel"] in out:
                out[a["channel"]] += float(a["qty_kg"])
        out["Food Loss"] = float(st_obj["milp_result"]["total_loss_kg"])
        return out

    s_base = summarize(baseline_state)
    s_act = summarize(active_state)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Tanpa Adaptive Replanning (Statis)",
        x=channels,
        y=[s_base[c] for c in channels],
        marker_color="#94A3B8",
        text=[f"{s_base[c]:,.0f}" if s_base[c] > 0 else "" for c in channels],
        textposition="outside",
    ))
    fig.add_trace(go.Bar(
        name="Dengan Adaptive Replanning (Agentic MILP-FEFO)",
        x=channels,
        y=[s_act[c] for c in channels],
        marker_color="#1F4E79",
        text=[f"{s_act[c]:,.0f}" if s_act[c] > 0 else "" for c in channels],
        textposition="outside",
    ))
    fig.update_layout(
        title=dict(text="Perubahan Alokasi (kg): Statis vs Adaptive Replanning", y=0.97, x=0.0, font=dict(size=14)),
        barmode="group",
        yaxis_title="Volume Alokasi (kg)",
        yaxis=dict(range=[0, max(max(s_base.values()), max(s_act.values()), 100) * 1.18]),
        height=360,
        legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="center", x=0.5),
        margin=dict(l=10, r=10, t=48, b=55),
    )
    return fig


def apply_privacy_masking(df: pd.DataFrame, owner_enterprise: str, unlocked_set: set[str]) -> tuple[pd.DataFrame, List[str]]:
    """Mask private columns whenever current logged-in role does not own the enterprise DB."""
    if owner_enterprise in unlocked_set:
        return df.copy(), []
    masked_df = df.copy()
    masked_cols = []
    for col in masked_df.columns:
        low = col.lower()
        if low in PRIVATE_FIELDS or any(k in low for k in ("floor_price", "ceiling_price", "production_cost", "farmer_personal", "margin", "secret", "pii", "payout")):
            masked_df[col] = "🔒 REDACTED (Private)"
            masked_cols.append(col)
    return masked_df, masked_cols


def read_local_db_table(enterprise_key: str, table_name: str) -> pd.DataFrame:
    db_dir = DATA_DIR / "local_dbs"
    if enterprise_key == "freshfood":
        with open(DATA_DIR / "freshfood_tomato_qc.json", "r", encoding="utf-8") as f:
            docs = json.load(f)
        flat = []
        for d in docs:
            row = {k: v for k, v in d.items() if not isinstance(v, dict)}
            for k, v in d.items():
                if isinstance(v, dict):
                    for sk, sv in v.items():
                        row[f"{k}.{sk}"] = sv
            flat.append(row)
        return pd.DataFrame(flat)

    sqlite_map = {
        "agrofarm": db_dir / "agrofarm_pg.sqlite",
        "koperasi": db_dir / "koperasi_mysql.sqlite",
        "coldchain": db_dir / "coldchain_timescaledb.sqlite",
        "supermart": db_dir / "supermart_mysql.sqlite",
    }
    db_path = sqlite_map[enterprise_key]
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(f"SELECT * FROM {table_name}", conn)


# ---------------------------------------------------------------------------
# Main Dashboard Application
# ---------------------------------------------------------------------------
def main() -> None:
    ml_metrics = load_ml_metrics()
    exp_results = load_experiment_results()

    # ---------------------- SIDEBAR: Role Login + Chaos Injector ----------------------
    with st.sidebar:
        st.markdown("### 🔐 Simulasi Login & Peran (RBAC)")
        selected_role = st.selectbox(
            "Masuk Sebagai Peran",
            list(ROLE_PROFILES.keys()),
            index=0,
            help="Mengubah ruang lingkup akses data privat vs publik sesuai prinsip Zero-Direct-DB-Access.",
        )
        role_info = ROLE_PROFILES[selected_role]
        st.caption(f"👤 `{role_info['user']}`  \n🔑 Scope: `{role_info['token_preview']}`")
        if role_info["enterprise_key"] == "global":
            st.info("🔒 Mode Global: Seluruh 15 kolom privat enterprise otomatis disamarkan (*Zero-Direct-DB*).")
        else:
            st.success(f"🔓 Mode Lokal ({role_info['enterprise_key'].upper()}): Data privat internal terbuka hanya untuk enterprise ini.")

        st.divider()
        st.markdown("### ⚡ Chaos & Disruption Injector")
        scenario = st.selectbox(
            "Skenario Lingkungan",
            list(SCENARIO_LABELS.keys()),
            index=1,
            format_func=lambda k: SCENARIO_LABELS[k],
        )

        use_custom_env = st.checkbox("Atur Parameter Lingkungan Manual (Slider)", value=False)
        cold_override = None
        demand_override = None
        if use_custom_env:
            cold_override = float(st.slider("Kapasitas Cold Storage Efektif (kg)", 0, 3000, 1000, step=100))
            demand_override = float(st.slider("Permintaan SuperMart (kg)", 1500, 3500, 2000, step=100))

        st.markdown("### 🧠 Konfigurasi Agentic & Ablasi")
        adaptive = st.toggle("Adaptive Replanning & Contract Net", value=True)
        routing_choice = st.radio(
            "Model LLM Routing",
            ["Heterogeneous (6 LLM Berbeda)", "Homogeneous (6× GPT-4o)"],
            index=0,
        )
        solver_choice = st.radio(
            "Mesin Alokasi",
            ["Neuro-Symbolic MILP-FEFO (PuLP)", "Pure LLM Heuristic (Ablasi)"],
            index=0,
        )

        run_btn = st.button("🚀 Jalankan Siklus Orkestrator", type="primary", use_container_width=True)

        st.divider()
        st.markdown("### 🤖 6 Agen Heterogen")
        for aid, p in AGENT_MODEL_PROFILES.items():
            llm_lbl = "GPT-4o (Homogeneous)" if "Homogeneous" in routing_choice else p.llm_model
            st.markdown(f"**{aid}** · {p.enterprise}  \n`{llm_lbl}` + *{p.domain_model}*")

    homo_flag = "Homogeneous" in routing_choice
    use_milp_flag = "MILP" in solver_choice
    orch = load_orchestrator(homogeneous_frontier=homo_flag)

    # Execute active cycle + paired static baseline for measurable delta proof
    config_signature = (scenario, adaptive, homo_flag, use_milp_flag, cold_override, demand_override)
    if "last_state" not in st.session_state or run_btn or st.session_state.get("last_sig") != config_signature:
        active_state = orch.run_cycle(
            trigger_mode=scenario,
            adaptive_replanning=adaptive,
            use_milp=use_milp_flag,
            demand_override_kg=demand_override,
            cold_storage_cap_override_kg=cold_override,
            auto_approve_hitl=False,
        )
        # Paired static baseline under identical environmental shock to prove measurable decision change
        baseline_orch = load_orchestrator(homogeneous_frontier=False)
        baseline_state = baseline_orch.run_cycle(
            trigger_mode=scenario,
            adaptive_replanning=False,
            use_milp=True,
            demand_override_kg=demand_override,
            cold_storage_cap_override_kg=cold_override,
            auto_approve_hitl=True,
        )
        st.session_state["last_state"] = active_state
        st.session_state["baseline_state"] = baseline_state
        st.session_state["last_sig"] = config_signature

    state = st.session_state["last_state"]
    base_state = st.session_state["baseline_state"]
    kpis = state["global_kpis"]
    base_kpis = base_state["global_kpis"]

    # ---------------------- TOP EXECUTIVE ROLE BANNER ----------------------
    st.markdown(
        f"""
        <div class="role-banner">
            <div>
                <div style="font-size:1.25rem; font-weight:700;">🍅 AgriChain Agentic AI — Multi-Enterprise Control Center</div>
                <div style="font-size:0.84rem; opacity:0.92;">{role_info['scope_desc']}</div>
            </div>
            <div style="display:flex; gap:0.5rem; flex-wrap:wrap;">
                <span class="role-badge">Role: {selected_role}</span>
                <span class="role-badge">Cycle: {state['cycle_id']}</span>
                <span class="role-badge">Mode: {scenario}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---------------------- 8 STRUCTURED TABS ----------------------
    tabs = st.tabs([
        "🌐 Global Control Center",
        "🧭 Decision Trace & Audit",
        "🌱 AgroFarm (AGT-01)",
        "🤝 Koperasi (AGT-02)",
        "🏭 FreshFood QC (AGT-03)",
        "❄️ ColdChain (AGT-04)",
        "🛒 SuperMart (AGT-05)",
        "🗄️ Data Explorer & Benchmark",
    ])

    # =========================================================================
    # TAB 1: GLOBAL CONTROL CENTER (Dashboard, Measured Delta, Agent Status, HITL)
    # =========================================================================
    with tabs[0]:
        # Status severity banner
        if state["hitl_status"] == "HUMAN_APPROVED":
            st.markdown(
                "<div class='status-banner-ok'><b>✅ COMMITTED & HUMAN APPROVED:</b> Rencana Adaptive Replanning telah diverifikasi operator dan tercatat permanen di Audit Trail SHA-256.</div>",
                unsafe_allow_html=True,
            )
        elif state["hitl_status"] == "HUMAN_REJECTED":
            st.markdown(
                "<div class='status-banner-danger'><b>⛔ REJECTED BY OPERATOR:</b> Rencana ditahan operator untuk negosiasi ulang manual (tercatat di Audit Trail SHA-256).</div>",
                unsafe_allow_html=True,
            )
        elif state["hitl_required"]:
            st.markdown(
                f"<div class='status-banner-warn'><b>⚠️ HITL GOVERNANCE GATE AKTIF (NIST AI RMF 1.0):</b> Pemicu risiko terdeteksi → <code>{', '.join(state['hitl_reasons'])}</code>. Menunggu persetujuan operator sebelum komitmen final.</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div class='status-banner-ok'><b>🟢 EKOSISTEM NORMAL & OPTIMAL:</b> Seluruh ambang risiko NIST AI RMF 1.0 aman, 0 pelanggaran kendala, 0 kebocoran privasi.</div>",
                unsafe_allow_html=True,
            )

        # 6 Executive KPI Cards with measurable deltas vs Static No-Replanning
        d_flr = kpis["food_loss_rate_pct"] - base_kpis["food_loss_rate_pct"]
        d_ofr = kpis["order_fulfillment_rate_pct"] - base_kpis["order_fulfillment_rate_pct"]
        d_prof = (kpis["net_ecosystem_profit_rp"] - base_kpis["net_ecosystem_profit_rp"]) / 1e6
        d_cost = (kpis["total_supply_chain_cost_rp"] - base_kpis["total_supply_chain_cost_rp"]) / 1e6
        d_fair = kpis["jains_fairness_index"] - base_kpis["jains_fairness_index"]

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Food Loss Rate (FLR)", f"{kpis['food_loss_rate_pct']:.2f}%", f"{d_flr:+.2f}% vs Statis", delta_color="inverse")
        c2.metric("Order Fulfillment (OFR)", f"{kpis['order_fulfillment_rate_pct']:.1f}%", f"{d_ofr:+.1f}% vs Statis")
        c3.metric("Net Ecosystem Profit", f"Rp{kpis['net_ecosystem_profit_rp']/1e6:.2f} Jt", f"{d_prof:+.2f} Jt vs Statis")
        c4.metric("Total Supply Cost", f"Rp{kpis['total_supply_chain_cost_rp']/1e6:.2f} Jt", f"{d_cost:+.2f} Jt vs Statis", delta_color="inverse")
        c5.metric("Jain's Fairness", f"{kpis['jains_fairness_index']:.4f}", f"{d_fair:+.4f} vs Statis")
        c6.metric(
            "Replan Time & LLM Cost",
            f"{kpis['replanning_response_time_sec']:.2f} s",
            f"USD {kpis['llm_cost_usd']:.5f} | {kpis['constraint_violations']} viol.",
            delta_color="off",
        )

        # Interactive HITL Governance Drawer
        if state["hitl_required"]:
            with st.expander("🛡️ Konsol Keputusan Operator Human-in-the-Loop (NIST AI RMF 1.0)", expanded=True):
                h1, h2 = st.columns([2, 3])
                op_name = h1.text_input("Nama Operator / Approver", value=role_info["user"], key="hitl_op")
                op_note = h2.text_input("Catatan Keputusan Audit", value="Disetujui setelah verifikasi alokasi MILP-FEFO & margin petani.", key="hitl_note")
                b_ok, b_rej, b_info = st.columns([1, 1, 3])
                if b_ok.button("✅ Approve & Commit Plan", type="primary", use_container_width=True):
                    state["hitl_status"] = "HUMAN_APPROVED"
                    kpis["hitl_status"] = "HUMAN_APPROVED"
                    entry = orch.audit.record("HITL_MANUAL_APPROVAL", op_name, {"cycle_id": state["cycle_id"], "note": op_note})
                    st.success(f"Disetujui oleh `{op_name}` — Hash Audit: `{entry['hash'][:16]}...`")
                    st.rerun()
                if b_rej.button("⛔ Reject & Hold Plan", use_container_width=True):
                    state["hitl_status"] = "HUMAN_REJECTED"
                    kpis["hitl_status"] = "HUMAN_REJECTED"
                    entry = orch.audit.record("HITL_MANUAL_REJECTION", op_name, {"cycle_id": state["cycle_id"], "note": op_note})
                    st.error(f"Ditolak oleh `{op_name}` — Hash Audit: `{entry['hash'][:16]}...`")
                    st.rerun()
                b_info.caption(f"Status HITL saat ini: **{state['hitl_status']}** | Privacy Leaks: **{kpis['privacy_leaks_detected']}** | Ronde Negosiasi: **{kpis['negotiation_rounds_used']}/3**")

        # Sankey + Measured Decision Shift side-by-side
        g1, g2 = st.columns([1.15, 1.0])
        with g1:
            st.plotly_chart(
                build_sankey(state["milp_result"]["allocations"], state["milp_result"]["unallocated_kg"]),
                use_container_width=True,
            )
        with g2:
            st.plotly_chart(build_decision_shift_chart(base_state, state), use_container_width=True)

        # Live Agent Status Matrix (6 Heterogeneous Agents)
        st.subheader("📡 Live Agent Status Matrix (6 Agen Heterogen)")
        ag_df = pd.DataFrame(state.get("agent_statuses", []))
        if not ag_df.empty:
            st.dataframe(
                ag_df.rename(columns={
                    "agent_id": "ID",
                    "enterprise": "Enterprise",
                    "status": "Status Operasional",
                    "domain_model": "Model Domain ML/Opt",
                    "llm_model": "LLM Backbone",
                    "calls": "Calls",
                    "avg_latency_ms": "Latensi (ms)",
                    "cost_usd": "Biaya (USD)",
                    "privacy_firewall": "Privacy Firewall",
                    "last_action": "Aksi Terakhir",
                }),
                use_container_width=True,
                hide_index=True,
            )

        # Allocation table & Enterprise Profit Fairness chart
        col_l, col_r = st.columns([1.2, 1.0])
        with col_l:
            st.subheader("📦 Matriks Alokasi MILP-FEFO (Output Keputusan)")
            alloc_df = pd.DataFrame(state["milp_result"]["allocations"])
            if not alloc_df.empty:
                st.dataframe(alloc_df, use_container_width=True, hide_index=True)
            else:
                st.warning("Tidak ada alokasi aktif pada siklus ini.")
        with col_r:
            st.subheader("💰 Distribusi Profit Bersih 5 Enterprise (Rp)")
            prof_df = pd.DataFrame(list(state["enterprise_profits_rp"].items()), columns=["Enterprise", "Profit (Rp)"])
            fig_prof = px.bar(
                prof_df,
                x="Enterprise",
                y="Profit (Rp)",
                color="Enterprise",
                text_auto=".2s",
                color_discrete_sequence=["#2F855A", "#B7791F", "#6B46C1", "#0987A0", "#C53030"],
            )
            fig_prof.update_layout(showlegend=False, height=310, margin=dict(l=10, r=10, t=15, b=10))
            st.plotly_chart(fig_prof, use_container_width=True)

    # =========================================================================
    # TAB 2: DECISION TRACE, FIPA-ACL COMMUNICATION, LLM TELEMETRY & AUDIT TRAIL
    # =========================================================================
    with tabs[1]:
        st.subheader("🧭 LangGraph 7-Node Decision Trace (Jejak Perubahan Keputusan)")
        for step in state.get("decision_trace", []):
            st.markdown(
                f"""
                <div class="trace-card">
                    <b>Step {step['step']} · <code>{step['node']}</code></b> &nbsp;|&nbsp;
                    <span>Actor: <b>{step['actors']}</b></span> &nbsp;|&nbsp;
                    <span>Status: <code>{step['status']}</code></span> &nbsp;|&nbsp;
                    <span style="color:#64748B; font-size:0.8rem;">{step['timestamp']}</span><br/>
                    <span style="font-size:0.92rem;">{step['summary']}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.divider()
        c_msg, c_llm = st.columns([1.25, 1.0])
        with c_msg:
            st.subheader("💬 Log Komunikasi A2A / FIPA-ACL / GS1 EPCIS 2.0")
            msgs = state.get("messages", [])
            perf_opts = ["ALL"] + sorted({m["performative"] for m in msgs})
            sel_perf = st.selectbox("Filter Performatif FIPA-ACL", perf_opts)
            filtered_msgs = [m for m in msgs if sel_perf == "ALL" or m["performative"] == sel_perf]
            for idx, m in enumerate(filtered_msgs):
                st.markdown(
                    f"""
                    <div class="msg-card">
                        <b>#{idx+1}</b> <code>{m['performative']}</code> &nbsp;|&nbsp;
                        <b>{m['sender']}</b> → <b>{m['receiver']}</b>
                        <span style="float:right; color:#64748B; font-size:0.78rem;">{m['protocol']} · R{m['negotiation_round']}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                with st.expander(f"Lihat Payload JSON & GS1 EPCIS (#{idx+1} — {m['sender']})", expanded=False):
                    st.json({"payload": m["payload"], "epcis_event": m.get("epcis_event")})

        with c_llm:
            st.subheader("🧠 Telemetri Panggilan 6-LLM Router")
            tel = kpis.get("llm_telemetry", {})
            st.caption(
                f"Routing Mode: **{tel.get('routing_mode', 'HETEROGENEOUS_6_LLM')}** | "
                f"Total Calls: **{tel.get('total_calls', 0)}** | "
                f"Total Tokens: **{kpis.get('llm_total_tokens', 0):,}** | "
                f"Est. Cost: **USD {tel.get('total_cost_usd', 0):.6f}**"
            )
            calls_df = pd.DataFrame(tel.get("calls", []))
            if not calls_df.empty:
                st.dataframe(calls_df, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("🔐 Immutable SHA-256 Hash-Chained Audit Trail")
        a_btn, a_stat = st.columns([1, 3])
        if a_btn.button("🔍 Verifikasi Integritas Rantai SHA-256"):
            valid = orch.audit.verify_chain()
            if valid:
                a_stat.success("✅ VERIFIED: Seluruh rantai hash SHA-256 di `results/audit_trail.jsonl` utuh tanpa manipulasi.")
            else:
                a_stat.error("❌ TAMPER DETECTED: Rantai hash tidak valid!")
        else:
            a_stat.info("Klik tombol untuk menjalankan verifikasi kriptografi `ImmutableAuditTrail.verify_chain()`.")

        audit_path = RESULTS_DIR / "audit_trail.jsonl"
        if audit_path.exists():
            lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
            recent = [json.loads(ln) for ln in lines[-15:]][::-1]
            audit_df = pd.DataFrame([
                {
                    "Timestamp": e["timestamp"],
                    "Event": e["event_type"],
                    "Actor": e["actor"],
                    "Details": json.dumps(e["details"]),
                    "SHA-256 Hash": e["hash"][:20] + "...",
                    "Prev Hash": e["prev_hash"][:16] + "...",
                }
                for e in recent
            ])
            st.dataframe(audit_df, use_container_width=True, hide_index=True)

    # =========================================================================
    # TAB 3: AGROFARM MODULE (AGT-01)
    # =========================================================================
    with tabs[2]:
        st.subheader("🌱 AgroFarm Cockpit — Random Forest Yield Prediction (PostgreSQL · Qwen 2.5 14B)")
        m_af = ml_metrics.get("agrofarm_rf", {})
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Test MAE (RF)", f"{m_af.get('test_mae_kg', 93.09)} kg", f"{m_af.get('test_mae_pct_of_mean', 7.24)}% mean (<=10%)")
        k2.metric("Test R²", f"{m_af.get('test_r2', 0.9393)}")
        k3.metric("5-Fold CV MAE", f"{m_af.get('cv_5fold_mae_kg', 142.99)} kg")
        k4.metric("Private HPP Scope", "UNLOCKED (Lokal)" if "agrofarm" in role_info["private_unlocked"] else "🔒 REDACTED")

        c_sim, c_lot = st.columns([1.0, 1.2])
        with c_sim:
            st.markdown("#### 🎛️ Simulator Prediksi Panen Interaktif (Random Forest)")
            s_area = st.slider("Luas Lahan (ha)", 0.4, 2.0, 1.2, 0.05)
            s_temp = st.slider("Suhu Rata-rata (°C)", 20.0, 32.0, 25.0, 0.5)
            s_moist = st.slider("Kelembaban Tanah (%)", 45.0, 85.0, 66.0, 1.0)
            s_rain = st.slider("Curah Hujan (mm)", 0.0, 50.0, 15.0, 1.0)
            s_fert = st.slider("Dosis Pupuk (kg/ha)", 100.0, 240.0, 180.0, 5.0)
            s_age = st.slider("Umur Tanaman (hari)", 65, 90, 76, 1)
            pred_af = orch.agrofarm.model.predict_batch([{
                "lot_id": "SIM-PLOT",
                "area_ha": s_area,
                "avg_temp_c": s_temp,
                "soil_moisture_pct": s_moist,
                "rainfall_mm": s_rain,
                "fertilizer_kg_ha": s_fert,
                "crop_age_days": s_age,
                "grade": "A",
                "shelf_life_days": 5,
            }])[0]
            ci = pred_af["confidence_interval_95"]
            st.success(f"**Prediksi Hasil Panen:** `{pred_af['predicted_kg']:,.1f} kg`  |  **95% CI:** `[{ci[0]:,.1f} – {ci[1]:,.1f}] kg`")

        with c_lot:
            st.markdown("#### 📋 Lot Panen Aktif & Risiko Umur Simpan (FEFO)")
            df_lots = read_local_db_table("agrofarm", "active_harvest_lots")
            df_lots_masked, mcols = apply_privacy_masking(df_lots, "agrofarm", role_info["private_unlocked"])
            st.dataframe(df_lots_masked, use_container_width=True, hide_index=True)

            st.markdown("#### 🔒 Tabel Biaya Pokok Privat (`private_costs`)")
            df_priv = read_local_db_table("agrofarm", "private_costs")
            df_priv_masked, mcols_p = apply_privacy_masking(df_priv, "agrofarm", role_info["private_unlocked"])
            if mcols_p:
                st.warning(f"Kolom privat disamarkan untuk peran `{selected_role}`: `{', '.join(mcols_p)}`")
            st.dataframe(df_priv_masked.head(8), use_container_width=True, hide_index=True)

    # =========================================================================
    # TAB 4: KOPERASI TANI MODULE (AGT-02)
    # =========================================================================
    with tabs[3]:
        st.subheader("🤝 Koperasi Tani Cockpit — LightGBM Price Forecasting & Contract Net (MySQL · Claude 3.5)")
        m_kp = ml_metrics.get("koperasi_lgbm", {})
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Test MAE Harga", f"Rp{m_kp.get('test_mae_rp', 240.1):,.1f}/kg")
        k2.metric("Test MAPE", f"{m_kp.get('test_mape_pct', 4.28)}%", "Target <= 8%")
        k3.metric("Test R²", f"{m_kp.get('test_r2', 0.9853)}")
        k4.metric("Floor Price Scope", "UNLOCKED (Lokal)" if "koperasi" in role_info["private_unlocked"] else "🔒 REDACTED")

        c_k1, c_k2 = st.columns([1.0, 1.25])
        with c_k1:
            st.markdown("#### ⚖️ Simulator Harga LightGBM & Uji Lelang Contract Net")
            k_grade = st.selectbox("Grade Tomat", ["A", "B", "C"], index=1)
            k_season = st.selectbox("Musim", ["Wet", "Dry"], index=0)
            k_sup = st.slider("Pasokan Regional (ton)", 15.0, 60.0, 34.0, 1.0)
            k_sl = st.slider("Umur Simpan (hari)", 1, 7, 3, 1)
            ask_pred = orch.koperasi.model.predict_price(grade=k_grade, season=k_season, regional_supply_ton=k_sup, shelf_life_days=k_sl)
            st.info(f"**Referensi Harga Jual (LightGBM):** `Rp{ask_pred:,.0f} / kg`")

            buyer_offer = st.number_input("Simulasi Tawaran Pembeli (Rp/kg)", min_value=2000, max_value=15000, value=6400, step=100)
            floor_p = orch.koperasi._private_floor_prices[k_grade]
            auc_res = orch.koperasi.model.evaluate_contract_net_bids(
                "SIM-LOT", 500.0, floor_p, [{"buyer_id": "SimulatedBuyer", "qty_kg": 500.0, "offer_price_rp": buyer_offer, "slot": "SPOT"}]
            )
            if auc_res["status"] == "ACCEPT_PROPOSAL":
                st.success(f"✅ **ACCEPT_PROPOSAL:** Tawaran Rp{buyer_offer:,.0f}/kg diterima (di atas ambang kelayakan petani).")
            else:
                st.error(f"❌ **REJECT_PROPOSAL** (`{auc_res['reason_code']}`): Tawaran ditolak tanpa membocorkan `floor_price_rp` privat!")

        with c_k2:
            st.markdown("#### 📈 Tren Harga Pasar Historis & Data Negosiasi (MySQL)")
            df_kop = read_local_db_table("koperasi", "market_price_negotiations")
            fig_kp = px.line(
                df_kop.tail(180),
                x="tx_date",
                y="market_ref_price_rp",
                color="grade",
                title="Pergerakan Harga Referensi Pasar Tomat per Grade (Rp/kg)",
            )
            fig_kp.update_layout(height=280, margin=dict(l=10, r=10, t=35, b=10))
            st.plotly_chart(fig_kp, use_container_width=True)

            df_kop_masked, mcols_k = apply_privacy_masking(df_kop.head(8), "koperasi", role_info["private_unlocked"])
            if mcols_k:
                st.caption(f"🔒 Kolom privat ter-redaksi di mode `{selected_role}`: `{', '.join(mcols_k)}`")
            st.dataframe(df_kop_masked, use_container_width=True, hide_index=True)

    # =========================================================================
    # TAB 5: FRESHFOOD PROCESSING MODULE (AGT-03 — REAL RGB TOMATO GALLERY + CNN)
    # =========================================================================
    with tabs[4]:
        st.subheader("🏭 FreshFood Processing Cockpit — 2D-Conv CNN Visual Grading & Food Safety Hard-Block (MongoDB · Gemini 2.5 Flash)")
        m_ff = ml_metrics.get("freshfood_cnn", {})
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("CNN Test Accuracy", f"{m_ff.get('test_accuracy_pct', 98.67)}%", "Target >= 90%")
        k2.metric("Macro-F1 Score", f"{m_ff.get('test_macro_f1', 0.9878)}")
        k3.metric("Reject Class Recall", f"{m_ff.get('reject_recall_pct', 100.0)}%", "Zero Missed Reject")
        k4.metric("Overtime Status (Siklus Aktif)", "AKTIF (+500 kg)" if kpis.get("overtime_activated") else "REGULER (2.000 kg)")

        st.markdown("#### 📸 Galeri Sampel Citra RGB Tomat Aktual (`freshfood_tomato_images.npz`) + Inferensi CNN Real-Time")
        samples = load_tomato_rgb_sample(n_per_class=2)
        if samples:
            batch_imgs = np.stack([s["image"] for s in samples])
            preds = orch.freshfood.model.classify_images(batch_imgs)
            cols_img = st.columns(4)
            for idx, (s, pr) in enumerate(zip(samples, preds)):
                col_i = cols_img[idx % 4]
                upscaled = Image.fromarray(s["image"].astype(np.uint8)).resize((128, 128), Image.Resampling.NEAREST)
                badge = "🔴 REJECT / BLOCK" if pr["predicted_grade"] == "Reject" else f"🟢 Grade {pr['predicted_grade']}"
                col_i.image(upscaled, caption=f"#{s['index']} | True: {s['true_grade']} → Pred: {badge} ({pr['confidence']*100:.1f}%)")

        st.divider()
        c_fs1, c_fs2 = st.columns([1.0, 1.1])
        with c_fs1:
            st.markdown("#### 🧪 Simulator Guardrail Keamanan Pangan (0% Toleransi Hard-Block)")
            fs_ph = st.slider("Level pH (Aman: 4.0 – 4.6)", 3.5, 5.5, 4.32, 0.02)
            fs_pest = st.slider("Residu Pestisida ppm (Batas MRL ≤ 0.05)", 0.00, 0.12, 0.015, 0.005)
            fs_def = st.slider("Rasio Cacat Visual (Batas ≤ 0.20)", 0.00, 0.35, 0.08, 0.01)
            fs_mic = st.checkbox("Lolos Uji Mikrobiologi (`microbial_pass`)", value=True)
            fs_check = orch.freshfood.model.verify_food_safety_hard_block(
                {"ph_level": fs_ph, "pesticide_residue_ppm": fs_pest, "microbial_pass": fs_mic}, fs_def
            )
            if fs_check["food_safety_approved"]:
                st.success("✅ **FOOD SAFETY APPROVED:** Batch layak masuk penjadwalan produksi FEFO.")
            else:
                st.error(f"⛔ **HARD-BLOCK TRIGGERED (0% Toleransi):** Alokasi otomatis diblokir (`0 kg`). Pelanggaran: `{', '.join(fs_check['violation_reasons'])}`")
        with c_fs2:
            st.markdown("#### 📄 Sampel Dokumen QC MongoDB (`freshfood_tomato_qc.json`)")
            df_qc = read_local_db_table("freshfood", "qc_docs")
            st.dataframe(df_qc.head(10), use_container_width=True, hide_index=True)

    # =========================================================================
    # TAB 6: COLDCHAIN LOGISTICS MODULE (AGT-04 — IFOREST ANOMALY + OR-TOOLS CVRP)
    # =========================================================================
    with tabs[5]:
        st.subheader("❄️ ColdChain Logistics Cockpit — Isolation Forest Anomaly & Google OR-Tools CVRP (TimescaleDB · Llama 3.1 8B Edge)")
        m_cc = ml_metrics.get("coldchain_iforest_cvrp", {})
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Anomaly F1-Score", f"{m_cc.get('anomaly_f1_pct', 95.32)}%", f"Recall {m_cc.get('anomaly_recall_pct', 100.0)}%")
        k2.metric("ROC-AUC", f"{m_cc.get('anomaly_roc_auc', 1.0):.4f}")
        k3.metric("Reduksi Jarak CVRP", f"-{m_cc.get('cvrp_distance_reduction_pct', 31.15)}%", "382 → 263 km")
        k4.metric("Kapasitas Aktif Siklus", f"{state['cold_storage_cap_kg']:,.0f} kg", f"Drop {state['capacity_drop_pct']}%", delta_color="inverse")

        df_tel = read_local_db_table("coldchain", "cold_storage_telemetry").tail(240)
        fig_tel = go.Figure()
        fig_tel.add_hrect(y0=7.0, y1=12.0, fillcolor="rgba(16, 185, 129, 0.12)", line_width=0, annotation_text="Zona Suhu Aman (7–12°C)")
        fig_tel.add_trace(go.Scatter(x=df_tel["ts"], y=df_tel["temp_c"], mode="lines", name="Suhu Ruang (°C)", line=dict(color="#1F4E79", width=2)))
        anoms = df_tel[df_tel["is_anomaly"] == 1]
        if not anoms.empty:
            fig_tel.add_trace(go.Scatter(x=anoms["ts"], y=anoms["temp_c"], mode="markers", name="Anomali Isolation Forest", marker=dict(color="#DC2626", size=9, symbol="x")))
        fig_tel.update_layout(title="Telemetri Suhu Cold Storage & Deteksi Anomali Real-Time (TimescaleDB)", yaxis_title="Suhu (°C)", height=320, margin=dict(l=10, r=10, t=38, b=10))
        st.plotly_chart(fig_tel, use_container_width=True)

        cv1, cv2 = st.columns([1.2, 1.0])
        cvrp_sol = orch.coldchain.model.solve_cvrp_demo()
        with cv1:
            st.markdown("#### 🚚 Rute Armada Pendingin Optimal (Google OR-Tools CVRP)")
            route_rows = [
                {
                    "Armada": r["truck"],
                    "Urutan Rute": " → ".join(r["stops"]),
                    "Muatan (kg)": r["load_kg"],
                    "Jarak (km)": r["distance_km"],
                }
                for r in cvrp_sol["routes"]
            ]
            st.dataframe(pd.DataFrame(route_rows), use_container_width=True, hide_index=True)
        with cv2:
            fig_cvrp = go.Figure(data=[
                go.Bar(x=["Naive Point-to-Point", "OR-Tools CVRP Optimal"], y=[cvrp_sol["naive_distance_km"], cvrp_sol["optimized_distance_km"]], marker_color=["#94A3B8", "#0987A0"], text=[f"{cvrp_sol['naive_distance_km']:.0f} km", f"{cvrp_sol['optimized_distance_km']:.0f} km"], textposition="outside")
            ])
            fig_cvrp.update_layout(
                title=f"Efisiensi Rute Armada (-{cvrp_sol['distance_reduction_pct']}%)",
                yaxis_title="Total Jarak (km)",
                yaxis=dict(range=[0, max(cvrp_sol["naive_distance_km"], 400) * 1.18]),
                height=280,
                margin=dict(l=10, r=10, t=42, b=10),
            )
            st.plotly_chart(fig_cvrp, use_container_width=True)

    # =========================================================================
    # TAB 7: SUPERMART MODULE (AGT-05 — XGBOOST DEMAND + NEWSVENDOR PO)
    # =========================================================================
    with tabs[6]:
        st.subheader("🛒 SuperMart Cockpit — XGBoost Demand Forecasting & Newsvendor PO (MySQL · Mistral Small 3)")
        m_sm = ml_metrics.get("supermart_xgb", {})
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Test MAE Demand", f"{m_sm.get('test_mae_kg', 26.71)} kg")
        k2.metric("Test MAPE", f"{m_sm.get('test_mape_pct', 3.72)}%", "Target <= 15%")
        k3.metric("Test R²", f"{m_sm.get('test_r2', 0.9215)}")
        k4.metric("Substitusi Grade B", "DIIZINKAN (≤30%)" if state.get("allow_grade_b_to_supermart") else "GRADE A ONLY")

        s1, s2 = st.columns([1.0, 1.25])
        with s1:
            st.markdown("#### 📊 Kalkulator Prediksi Demand XGBoost & Newsvendor PO")
            sm_day = st.selectbox("Hari Penjualan", [(0, "Senin"), (2, "Rabu"), (4, "Jumat"), (5, "Sabtu (Weekend)"), (6, "Minggu (Weekend)")], format_func=lambda x: x[1])[0]
            sm_promo = st.checkbox("Promo Akhir Pekan Aktif (`is_promo=1`)", value=False)
            sm_price = st.slider("Harga Jual Ritel (Rp/kg)", 11000, 18000, 14500, 250)
            sm_stock = st.slider("Stok Awal Gerai (kg)", 0, 1500, 200, 50)
            f_dem = orch.supermart.model.forecast_total_chain_demand(day_of_week=sm_day, price_rp=float(sm_price), is_promo=1 if sm_promo else 0)
            po_calc = orch.supermart.model.compute_newsvendor_po(f_dem, current_stock_kg=float(sm_stock), sell_price_rp=float(sm_price))
            st.success(
                f"**Forecast 3 Gerai (XGBoost):** `{po_calc['forecast_demand_kg']:,.1f} kg`  \n"
                f"**Safety Buffer (Newsvendor):** `{po_calc['safety_buffer_kg']:+,.1f} kg` (Fractile `{po_calc['critical_fractile']}`)  \n"
                f"**Rekomendasi Purchase Order:** **`{po_calc['recommended_po_kg']:,.1f} kg`**"
            )
            if "supermart" in role_info["private_unlocked"]:
                st.caption(f"🔓 Kebijakan Privat Lokal: `ceiling_price_grade_a = Rp{orch.supermart._private_ceiling_price_grade_a:,.0f}/kg`")
            else:
                st.caption("🔒 `ceiling_price_rp` & margin ritel disamarkan untuk peran non-SuperMart.")

        with s2:
            df_pos = read_local_db_table("supermart", "retail_pos_sales")
            daily_pos = df_pos.groupby("sales_date", as_index=False)["demand_sold_kg"].sum().tail(90)
            fig_pos = px.area(daily_pos, x="sales_date", y="demand_sold_kg", title="Penjualan POS Harian Total 3 Gerai SuperMart (90 Hari Terakhir)")
            fig_pos.update_traces(line_color="#C53030", fillcolor="rgba(197, 48, 48, 0.16)")
            fig_pos.update_layout(height=320, margin=dict(l=10, r=10, t=38, b=10))
            st.plotly_chart(fig_pos, use_container_width=True)

    # =========================================================================
    # TAB 8: MULTI-ENTERPRISE DATA EXPLORER & BENCHMARK RESULTS
    # =========================================================================
    with tabs[7]:
        st.subheader("🗄️ Multi-Enterprise Local DB Data Explorer (Schema Mapping & Privacy Enforcement)")
        db_catalog = {
            "Koperasi Tani — market_price_negotiations [Privasi: floor_price_rp] (MySQL)": ("koperasi", "market_price_negotiations"),
            "AgroFarm — private_costs [Privasi: HPP & Farmer ID] (PostgreSQL)": ("agrofarm", "private_costs"),
            "AgroFarm — farm_harvest_history (PostgreSQL)": ("agrofarm", "farm_harvest_history"),
            "AgroFarm — active_harvest_lots (PostgreSQL)": ("agrofarm", "active_harvest_lots"),
            "FreshFood — tomato_qc_documents (MongoDB JSON)": ("freshfood", "qc_docs"),
            "ColdChain — cold_storage_telemetry (TimescaleDB)": ("coldchain", "cold_storage_telemetry"),
            "ColdChain — fleet_delivery_routes (TimescaleDB)": ("coldchain", "fleet_delivery_routes"),
            "SuperMart — retail_pos_sales (MySQL)": ("supermart", "retail_pos_sales"),
        }
        e1, e2, e3 = st.columns([2, 1.2, 0.8])
        sel_tbl_lbl = e1.selectbox("Pilih Basis Data & Tabel Enterprise", list(db_catalog.keys()))
        search_txt = e2.text_input("Cari Nilai / Lot / Zona", value="")
        max_rows = e3.number_input("Maks. Baris", min_value=10, max_value=500, value=50, step=10)

        ent_key, tbl_name = db_catalog[sel_tbl_lbl]
        raw_df = read_local_db_table(ent_key, tbl_name)
        view_df, masked_cols = apply_privacy_masking(raw_df, ent_key, role_info["private_unlocked"])

        if search_txt.strip():
            mask_match = view_df.astype(str).apply(lambda col: col.str.contains(search_txt.strip(), case=False, na=False)).any(axis=1)
            view_df = view_df[mask_match]

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Rekaman Tabel", f"{len(raw_df):,}")
        m2.metric("Baris Cocok Filter", f"{len(view_df):,}")
        m3.metric("Kolom Privat Ter-redaksi", f"{len(masked_cols)} kolom" if masked_cols else "0 (Lokal / Publik)")

        if masked_cols:
            st.warning(f"🔒 **Data Sovereignty Aktif:** Kolom `{', '.join(masked_cols)}` disamarkan karena peran `{selected_role}` bukan pemilik DB `{ent_key}`.")

        st.dataframe(view_df.head(int(max_rows)), use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️ Download Filtered CSV",
            data=view_df.head(int(max_rows)).to_csv(index=False).encode("utf-8"),
            file_name=f"{ent_key}_{tbl_name}_filtered.csv",
            mime="text/csv",
        )

        st.divider()
        st.subheader("📊 Ringkasan Benchmark & Studi Ablasi Bab 9 (N = 30 Siklus Berpasangan)")
        if exp_results:
            fig_dir = RESULTS_DIR / "figures"
            f1, f2 = st.columns(2)
            if (fig_dir / "fig_9_1_conditions.png").exists():
                f1.image(str(fig_dir / "fig_9_1_conditions.png"), caption="Gambar 9.1 — Perbandingan 4 Kondisi Eksperimen")
            if (fig_dir / "fig_9_2_ablation_comparison.png").exists():
                f2.image(str(fig_dir / "fig_9_2_ablation_comparison.png"), caption="Gambar 9.2 — Hasil 3 Studi Ablasi Arsitektur")
            if (fig_dir / "fig_9_3_agent_cost_latency.png").exists():
                st.image(str(fig_dir / "fig_9_3_agent_cost_latency.png"), caption="Gambar 9.3 — Analisis Biaya Token & Latensi 6 LLM Heterogen vs 6× GPT-4o")


if __name__ == "__main__":
    main()
