"""Streamlit Role-Based Dashboard: Global Agentic Control Center + 5 Enterprise Tabs (Bab 5.5)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.settings import AGENT_MODEL_PROFILES, DATA_DIR, RESULTS_DIR
from src.agents.orchestrator import AgriChainOrchestrator

st.set_page_config(page_title="AgriChain Agentic AI Control Center", layout="wide")


@st.cache_resource
def load_orchestrator() -> AgriChainOrchestrator:
    return AgriChainOrchestrator()


def build_sankey(allocations: list[dict]) -> go.Figure:
    nodes = ["AgroFarm", "Koperasi Tani", "SuperMart", "FreshFood_Reg", "FreshFood_OT", "ColdStorage", "Partner3PL", "AltBuyer"]
    node_idx = {n: i for i, n in enumerate(nodes)}
    sources, targets, values, labels = [], [], [], []
    total_qty = sum(a["qty_kg"] for a in allocations)
    if total_qty > 0:
        sources.append(node_idx["AgroFarm"])
        targets.append(node_idx["Koperasi Tani"])
        values.append(total_qty)
        labels.append(f"Total Panen: {total_qty:,.0f} kg")
    for a in allocations:
        ch = a["channel"]
        if ch in node_idx:
            sources.append(node_idx["Koperasi Tani"])
            targets.append(node_idx[ch])
            values.append(a["qty_kg"])
            labels.append(f"{a['lot_id']} (Grade {a['grade']}, SL {a['shelf_life_days']}d): {a['qty_kg']:,.0f} kg")

    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(
                    pad=18,
                    thickness=20,
                    label=nodes,
                    color=["#2F855A", "#B7791F", "#C53030", "#6B46C1", "#805AD5", "#0987A0", "#3182CE", "#718096"],
                ),
                link=dict(source=sources, target=targets, value=values, label=labels),
            )
        ]
    )
    fig.update_layout(title="Aliran Alokasi Rantai Pasok Tomat (MILP-FEFO Real-Time)", height=360, margin=dict(l=10, r=10, t=40, b=10))
    return fig


def main() -> None:
    st.title("AgriChain Agentic AI — Multi-Enterprise Control Center")
    st.caption("Heterogeneous Multi-Enterprise Agentic AI Ecosystem (6 Agents | 6 ML/Opt Models | 6 LLM Backbones | GS1 EPCIS 2.0 | NIST AI RMF 1.0)")

    orch = load_orchestrator()

    with st.sidebar:
        st.header("Chaos / Disruption Injector")
        scenario = st.selectbox(
            "Skenario Simulasi",
            ["NORMAL", "COLD_STORAGE_FAILURE", "DEMAND_SURGE", "FOOD_SAFETY_FAIL", "COMPOUND"],
        )
        adaptive = st.toggle("Aktifkan Adaptive Replanning & Negosiasi", value=True)
        run_btn = st.button("Jalankan Siklus Orkestrator", type="primary", use_container_width=True)
        st.divider()
        st.subheader("6 Agen Heterogen")
        for aid, p in AGENT_MODEL_PROFILES.items():
            st.markdown(f"**{aid}** ({p.enterprise})  \n`{p.llm_model}` + *{p.domain_model}*")

    if "last_state" not in st.session_state or run_btn:
        st.session_state["last_state"] = orch.run_cycle(
            trigger_mode=scenario,
            adaptive_replanning=adaptive,
            auto_approve_hitl=False,
        )

    state = st.session_state["last_state"]
    kpis = state["global_kpis"]

    tabs = st.tabs([
        "Global Control Center",
        "AgroFarm (AGT-01)",
        "Koperasi Tani (AGT-02)",
        "FreshFood (AGT-03)",
        "ColdChain (AGT-04)",
        "SuperMart (AGT-05)",
    ])

    with tabs[0]:
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Food Loss Rate", f"{kpis['food_loss_rate_pct']:.2f}%")
        c2.metric("Order Fulfillment", f"{kpis['order_fulfillment_rate_pct']:.1f}%")
        c3.metric("Total Cost", f"Rp{kpis['total_supply_chain_cost_rp']/1e6:.2f} Jt")
        c4.metric("Jain's Fairness", f"{kpis['jains_fairness_index']:.4f}")
        c5.metric("Replanning Time", f"{kpis['replanning_response_time_sec']:.2f} s")
        c6.metric("LLM Cost / Cycle", f"${kpis['llm_cost_usd']:.5f}")

        if state["hitl_required"]:
            st.warning(f"HITL Governance Gate Aktif (NIST AI RMF 1.0) — Alasan: {', '.join(state['hitl_reasons'])}")
            col_a, col_b = st.columns([1, 4])
            if col_a.button("Approve Replan (Operator)"):
                state["hitl_status"] = "HUMAN_APPROVED"
                st.success("Keputusan Adaptive Replanning telah disetujui operator manusia (COMMIT_PLAN dikirim).")

        st.plotly_chart(build_sankey(state["milp_result"]["allocations"]), use_container_width=True)

        col_l, col_r = st.columns(2)
        with col_l:
            st.subheader("Matriks Alokasi MILP-FEFO")
            st.dataframe(pd.DataFrame(state["milp_result"]["allocations"]), use_container_width=True)
        with col_r:
            st.subheader("Distribusi Profit 5 Enterprise (Rp)")
            prof_df = pd.DataFrame(list(state["enterprise_profits_rp"].items()), columns=["Enterprise", "Profit (Rp)"])
            st.bar_chart(prof_df.set_index("Enterprise"))

        st.subheader("Log Pesan A2A / FIPA-ACL / GS1 EPCIS 2.0")
        msg_rows = [
            {
                "Time": m["timestamp"],
                "Sender": m["sender"],
                "Receiver": m["receiver"],
                "Performative": m["performative"],
                "Protocol": m["protocol"],
                "Round": m["negotiation_round"],
            }
            for m in state["messages"]
        ]
        st.dataframe(pd.DataFrame(msg_rows), use_container_width=True)

    with tabs[1]:
        st.subheader("AgroFarm — Random Forest Yield Prediction (PostgreSQL)")
        st.dataframe(pd.read_csv(DATA_DIR / "agrofarm_active_lots.csv").head(10), use_container_width=True)

    with tabs[2]:
        st.subheader("Koperasi Tani — LightGBM Price Forecasting & Contract Net (MySQL)")
        st.dataframe(pd.read_csv(DATA_DIR / "koperasi_market_negotiations.csv").drop(columns=["floor_price_rp"]).head(10), use_container_width=True)

    with tabs[3]:
        st.subheader("FreshFood Processing — 2D-Conv CNN Visual QC & FEFO (MongoDB)")
        with open(DATA_DIR / "freshfood_tomato_qc.json", "r", encoding="utf-8") as f:
            docs = json.load(f)[:8]
        st.json(docs[:2])

    with tabs[4]:
        st.subheader("ColdChain Logistics — Isolation Forest Telemetry & OR-Tools CVRP (TimescaleDB)")
        df_tel = pd.read_csv(DATA_DIR / "coldchain_iot_telemetry.csv").tail(200)
        st.line_chart(df_tel.set_index("ts")[["temp_c", "power_kw"]])

    with tabs[5]:
        st.subheader("SuperMart — XGBoost Demand Forecasting & Newsvendor PO (MySQL)")
        df_pos = pd.read_csv(DATA_DIR / "supermart_pos_sales.csv").tail(90)
        st.line_chart(df_pos.groupby("sales_date")["demand_sold_kg"].sum())


if __name__ == "__main__":
    main()
