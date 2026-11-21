"""Automated Verification Test Suite for AgriChain Agentic AI Ecosystem."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from src.agents.orchestrator import AgriChainOrchestrator
from src.api.main import app
from src.models.milp_fefo import solve_milp_fefo
from src.protocols.fipa_epcis import HarvestBatch
from src.protocols.security import detect_privacy_leak, sanitize_outbound_payload


def test_data_sovereignty_firewall_blocks_private_fields():
    raw = {
        "lot_id": "H001",
        "ask_price_rp": 10000,
        "floor_price_rp": 9000,
        "production_cost_per_kg": 4800,
        "ceiling_price_rp": 10500,
    }
    clean, blocked = sanitize_outbound_payload("Koperasi Tani", raw)
    assert "floor_price_rp" not in clean
    assert "production_cost_per_kg" not in clean
    assert "ceiling_price_rp" not in clean
    assert len(blocked) == 3
    assert detect_privacy_leak(clean) == []


def test_milp_fefo_prioritizes_shortest_shelf_life_batch():
    lots = [
        HarvestBatch(lot_id="H001", qty_kg=2000, grade="A", shelf_life_days=5, ask_price_rp=10000, food_safety_approved=True),
        HarvestBatch(lot_id="H002", qty_kg=1500, grade="B", shelf_life_days=3, ask_price_rp=7000, food_safety_approved=True),
        HarvestBatch(lot_id="H003", qty_kg=1000, grade="C", shelf_life_days=2, ask_price_rp=4000, food_safety_approved=True),
    ]
    res = solve_milp_fefo(lots, demand_supermart_kg=2000, cap_freshfood_reg_kg=2000, cap_cold_storage_kg=3000, allow_overtime=False)
    assert res["solver_status"] == "Optimal"
    assert res["food_loss_rate_pct"] == 0.0
    # H003 (SL=2 days) MUST go 100% to FreshFood_Reg, NEVER ColdStorage!
    h003_allocs = [a for a in res["allocations"] if a["lot_id"] == "H003"]
    assert all(a["channel"] == "FreshFood_Reg" for a in h003_allocs)
    assert sum(a["qty_kg"] for a in h003_allocs) == 1000.0


def test_food_safety_hard_block_enforced():
    orch = AgriChainOrchestrator()
    st = orch.run_cycle(trigger_mode="FOOD_SAFETY_FAIL", failed_food_safety_lots=["H003"])
    h003_allocs = [a for a in st["milp_result"]["allocations"] if a["lot_id"] == "H003"]
    assert len(h003_allocs) == 0
    assert st["hitl_required"] is True
    assert "FOOD_SAFETY_HARD_BLOCK_TRIGGERED" in st["hitl_reasons"]
    assert st["global_kpis"]["privacy_leaks_detected"] == 0


def test_cold_storage_failure_triggers_adaptive_replanning_and_hitl():
    orch = AgriChainOrchestrator()
    st = orch.run_cycle(trigger_mode="COLD_STORAGE_FAILURE", adaptive_replanning=True)
    assert st["cold_storage_cap_kg"] == 1000.0
    assert st["milp_result"]["food_loss_rate_pct"] <= 2.0
    assert st["milp_result"]["overtime_activated"] is True
    assert st["hitl_required"] is True
    assert st["global_kpis"]["privacy_leaks_detected"] == 0
    assert orch.audit.verify_chain() is True


def test_negotiation_deadlock_bounded_at_3_rounds_and_escalates():
    orch = AgriChainOrchestrator()
    st = orch.run_cycle(trigger_mode="NORMAL", force_low_bid_deadlock=True)
    assert st["round_counter"] == 3
    assert st["deadlock_occurred"] is True
    assert st["hitl_required"] is True
    assert "NEGOTIATION_DEADLOCK_AFTER_3_ROUNDS" in st["hitl_reasons"]


def test_fastapi_gateway_endpoints():
    client = TestClient(app)
    r_health = client.get("/api/v1/health")
    assert r_health.status_code == 200
    assert int(r_health.json()["agents"]) == 6
    assert r_health.json()["audit_chain_valid"] is True

    r_cards = client.get("/.well-known/agent.json")
    assert r_cards.status_code == 200
    assert r_cards.json()["agent_count"] == 6

    # Per-enterprise local service status endpoints (Zero-Direct-DB-Access verified)
    for ent in ("agrofarm", "koperasi", "freshfood", "coldchain", "supermart"):
        r_ent = client.get(f"/api/v1/enterprises/{ent}/status")
        assert r_ent.status_code == 200
        assert r_ent.json()["status"] == "ONLINE"
        assert r_ent.json()["data_sovereignty_policy"] == "STRICT_ZERO_DIRECT_DB_ACCESS"

    r_cycle = client.post(
        "/api/v1/orchestrator/run-cycle",
        json={"trigger_mode": "COLD_STORAGE_FAILURE", "adaptive_replanning": True, "auto_approve_hitl": False},
    )
    assert r_cycle.status_code == 200
    body = r_cycle.json()
    assert body["hitl_required"] is True
    assert body["hitl_status"] == "PENDING_APPROVAL"
    assert len(body["decision_trace"]) >= 5
    assert len(body["agent_statuses"]) == 6

    r_app = client.post(f"/api/v1/orchestrator/hitl/{body['cycle_id']}/approve")
    assert r_app.status_code == 200
    assert r_app.json()["hitl_status"] == "HUMAN_APPROVED"

    r_rej = client.post(f"/api/v1/orchestrator/hitl/{body['cycle_id']}/reject")
    assert r_rej.status_code == 200
    assert r_rej.json()["hitl_status"] == "HUMAN_REJECTED"

    r_aud = client.get("/api/v1/audit/trail?limit=10")
    assert r_aud.status_code == 200
    assert r_aud.json()["chain_valid"] is True
    assert len(r_aud.json()["entries"]) >= 1


def test_measurable_decision_change_under_environmental_shock():
    orch = AgriChainOrchestrator()
    st_normal = orch.run_cycle(trigger_mode="NORMAL", adaptive_replanning=True)
    st_disrupt = orch.run_cycle(trigger_mode="COLD_STORAGE_FAILURE", adaptive_replanning=True)
    assert st_normal["milp_result"]["overtime_activated"] is False
    assert st_disrupt["milp_result"]["overtime_activated"] is True
    assert st_disrupt["round_counter"] >= 1
    assert len(st_disrupt["decision_trace"]) > len(st_normal["decision_trace"])
    assert st_disrupt["milp_result"]["food_loss_rate_pct"] == 0.0
