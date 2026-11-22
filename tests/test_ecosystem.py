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
    assert len(st_disrupt.get("lineage", [])) >= 1
    assert "Executive Briefing" in st_disrupt.get("executive_briefing", "") or len(st_disrupt.get("executive_briefing", "")) > 40


def test_agrofarm_v2_extreme_rain_and_sensor_outage_fallback():
    orch = AgriChainOrchestrator()
    # 1. Extreme rain: harvest window advances -2 days on impacted BLK-11/H003, 80% Quantile PI present, yield drops vs normal
    st_norm = orch.run_cycle(trigger_mode="NORMAL", adaptive_replanning=True)
    st_rain = orch.run_cycle(trigger_mode="EXTREME_RAIN", adaptive_replanning=True)
    norm_yield = sum(b["qty_kg"] for b in st_norm["batches"])
    rain_yield = sum(b["qty_kg"] for b in st_rain["batches"])
    assert rain_yield < norm_yield
    for b in st_rain["batches"]:
        lo, hi = b["pi80_interval_kg"]
        assert lo <= b["qty_kg"] <= hi
        assert b["ndvi"] is not None
    h003_rain = next(b for b in st_rain["batches"] if b["lot_id"] == "H003")
    assert h003_rain["harvest_window"]["shift_days"] == -2
    assert len(st_rain["agrofarm_monitoring"]) == 3
    assert any(m["status"] == "MENYIMPANG" for m in st_rain["agrofarm_monitoring"])

    # 2. Sensor outage (>= 3 days offline): triggers historical mean fallback + freshness warning
    st_out = orch.run_cycle(trigger_mode="SENSOR_OUTAGE", adaptive_replanning=True)
    assert st_out["data_freshness_warning"] is not None
    assert any(b["prediction_mode"] == "FALLBACK_HISTORICAL_MEAN" for b in st_out["batches"])
    assert any(m["stale_data"] for m in st_out["agrofarm_monitoring"])


def test_coldchain_v2_vrptw_eta_and_crud_endpoints():
    client = TestClient(app)

    # 1. Standardized tomato temperature range 7.0-12.0 C in health
    r_h = client.get("/api/v1/health")
    assert r_h.status_code == 200
    assert r_h.json()["tomato_safe_temp_c"] == [7.0, 12.0]

    # 2. AgroFarm Local REST endpoints
    r_mon = client.get("/api/v1/agrofarm/monitoring?extreme_rain=true")
    assert r_mon.status_code == 200
    assert len(r_mon.json()["blocks"]) == 3
    r_pred = client.post(
        "/api/v1/agrofarm/predict",
        json={"block_id": "BLK-11", "lot_id": "H003", "extreme_rain_flag": True},
    )
    assert r_pred.status_code == 200
    p = r_pred.json()["prediction"]
    lo, hi = p["pi80_interval_kg"]
    assert lo <= p["predicted_kg"] <= hi
    assert p["harvest_window"]["shift_days"] == -2
    assert len(r_pred.json()["feature_importance"]) >= 5

    # 3. ColdChain VRPTW & XGBoost ETA
    r_vrp = client.post("/api/v1/coldchain/vrptw", json={"scenario": "ROAD_DISRUPTION", "traffic_level": 2})
    assert r_vrp.status_code == 200
    plan = r_vrp.json()["active_plan"]
    assert plan["time_window_violations"] == 0
    assert plan["scenario"] == "ROAD_DISRUPTION"
    assert len(plan["routes"]) >= 1

    r_eta = client.post(
        "/api/v1/coldchain/eta",
        json={"distance_km": 42.0, "traffic_level": 2, "num_stops": 2, "weather_severity": 1, "departure_hour": 8},
    )
    assert r_eta.status_code == 200
    assert r_eta.json()["eta"]["predicted_duration_min"] > 0

    # 4. Fleet CRUD & RBAC rejection for non-fleet role
    r_fleet_deny = client.post(
        "/api/v1/coldchain/fleet",
        headers={"X-Scoped-Token": "tok_agrofarm_local_v1"},
        json={"vehicle_id": "V099", "capacity_kg": 2500, "min_temp_c": 7.0, "max_temp_c": 12.0},
    )
    assert r_fleet_deny.status_code == 403

    r_fleet_ok = client.post(
        "/api/v1/coldchain/fleet",
        headers={"X-Scoped-Token": "tok_coldchain_local_v1"},
        json={"vehicle_id": "V005", "capacity_kg": 3500, "min_temp_c": 7.0, "max_temp_c": 12.0, "status": "Available"},
    )
    assert r_fleet_ok.status_code == 200
    assert r_fleet_ok.json()["action"] in ("CREATE_VEHICLE", "UPDATE_VEHICLE")

    # 5. Shipments CRUD validation (deadline <= ready_time MUST be rejected 422)
    r_ship_bad = client.post(
        "/api/v1/coldchain/shipments",
        headers={"X-Scoped-Token": "tok_coldchain_local_v1"},
        json={"shipment_id": "SH999", "quantity_kg": 500, "ready_time": "12:00", "deadline": "10:00"},
    )
    assert r_ship_bad.status_code == 422

    r_ship_ok = client.post(
        "/api/v1/coldchain/shipments",
        headers={"X-Scoped-Token": "tok_coldchain_local_v1"},
        json={"shipment_id": "SH_TEST_01", "lot_id": "H001", "quantity_kg": 900, "ready_time": "08:00", "deadline": "12:00"},
    )
    assert r_ship_ok.status_code == 200
    assert r_ship_ok.json()["status"] == "CREATED"


def test_server_side_rbac_data_explorer_redaction():
    client = TestClient(app)

    # 1. Global Operator querying Koperasi table -> floor_price_rp MUST be redacted server-side
    r_global = client.get(
        "/api/v1/data-explorer/koperasi/market_price_negotiations?limit=5",
        headers={"X-Scoped-Token": "tok_orchestrator_global_scope_v1"},
    )
    assert r_global.status_code == 200
    b_global = r_global.json()
    assert b_global["server_side_firewall"] is True
    assert "floor_price_rp" in b_global["redacted_columns"]
    assert all("REDACTED" in str(row["floor_price_rp"]) for row in b_global["records"])

    # 2. Koperasi Owner querying OWN table -> floor_price_rp unlocked server-side
    r_owner = client.get(
        "/api/v1/data-explorer/koperasi/market_price_negotiations?limit=5",
        headers={"X-Scoped-Token": "tok_koperasi_local_v1"},
    )
    assert r_owner.status_code == 200
    b_owner = r_owner.json()
    assert b_owner["redacted_columns"] == []
    assert all(isinstance(row["floor_price_rp"], (int, float)) for row in b_owner["records"])

    # 3. Unauthorized token -> 403 Forbidden
    r_bad = client.get(
        "/api/v1/data-explorer/koperasi/market_price_negotiations",
        headers={"X-Scoped-Token": "tok_invalid_hacker"},
    )
    assert r_bad.status_code == 403


def test_freshfood_v21_qc_feedback_fefo_schedule_and_valorization():
    client = TestClient(app)

    # 1. Food Safety Hard-Block -> emits CRITICAL QC feedback to AgroFarm + COMPOST_BIOGAS_RECOVERY plan
    r_qc = client.post(
        "/api/v1/freshfood/qc-inspect",
        headers={"X-Scoped-Token": "tok_freshfood_local_v1"},
        json={
            "lot_id": "H003",
            "block_id": "BLK-11",
            "qty_kg": 1000.0,
            "ph_level": 4.95,
            "pesticide_residue_ppm": 0.08,
            "microbial_pass": False,
            "defect_ratio": 0.24,
        },
    )
    assert r_qc.status_code == 200
    body = r_qc.json()
    assert body["safety_verdict"]["food_safety_approved"] is False
    assert body["safety_verdict"]["hard_block_triggered"] is True
    assert body["qc_feedback_to_agrofarm"]["severity"] == "CRITICAL"
    assert body["qc_feedback_to_agrofarm"]["block_id"] == "BLK-11"
    assert body["waste_valorization_plan"]["disposal_channel"] == "COMPOST_BIOGAS_RECOVERY"
    assert body["waste_valorization_plan"]["human_food_chain_entry"] is False

    # 2. FEFO Line Schedule + Dynamic Receiving Dock Window extension when overtime=True
    r_reg = client.post("/api/v1/freshfood/schedule", json={"include_overtime": False})
    r_ot = client.post("/api/v1/freshfood/schedule", json={"include_overtime": True})
    assert r_reg.status_code == 200 and r_ot.status_code == 200
    assert r_reg.json()["receiving_dock_window"]["close_time"] == "11:40"
    assert r_ot.json()["receiving_dock_window"]["close_time"] == "14:00"
    assert r_ot.json()["fefo_schedule"]["scheduled_lots"][0]["lot_id"] == "H003"


def test_supermart_v21_7d_horizon_po_crud_and_goods_receipt_sla():
    client = TestClient(app)

    # 1. 7-Day Forecast + Server-Side Ceiling Price Redaction (Global redacted vs SuperMart unlocked)
    r_g = client.get(
        "/api/v1/supermart/forecast-7d?demand_surge=true&early_harvest_signal=true",
        headers={"X-Scoped-Token": "tok_orchestrator_global_scope_v1"},
    )
    assert r_g.status_code == 200
    bg = r_g.json()
    assert len(bg["horizon_7d"]) == 7
    assert bg["flash_promo_absorption"]["enabled"] is True
    assert bg["flash_promo_absorption"]["extra_absorption_cap_kg"] == 300.0
    assert "REDACTED" in str(bg["ceiling_price_grade_a_rp"])

    r_own = client.get(
        "/api/v1/supermart/forecast-7d",
        headers={"X-Scoped-Token": "tok_supermart_local_v1"},
    )
    assert r_own.status_code == 200
    assert isinstance(r_own.json()["ceiling_price_grade_a_rp"], (int, float))

    # 2. Koperasi Local Price Forecast (Floor price redacted for Global vs unlocked for Koperasi)
    r_kp_g = client.post(
        "/api/v1/koperasi/price-forecast",
        headers={"X-Scoped-Token": "tok_orchestrator_global_scope_v1"},
        json={"grade": "B"},
    )
    assert r_kp_g.status_code == 200 and "REDACTED" in str(r_kp_g.json()["floor_price_rp"])
    r_kp_o = client.post(
        "/api/v1/koperasi/price-forecast",
        headers={"X-Scoped-Token": "tok_koperasi_local_v1"},
        json={"grade": "B"},
    )
    assert r_kp_o.status_code == 200 and isinstance(r_kp_o.json()["floor_price_rp"], (int, float))

    # 3. SuperMart PO Guardrails: Grade C rejected (422), Grade B > 30% rejected (422), Price > ceiling rejected (422), Valid PO OK
    assert client.post(
        "/api/v1/supermart/po",
        headers={"X-Scoped-Token": "tok_supermart_local_v1"},
        json={"po_id": "PO-BAD-C", "grade": "C", "qty_kg": 500, "agreed_price_rp": 4000},
    ).status_code == 422
    assert client.post(
        "/api/v1/supermart/po",
        headers={"X-Scoped-Token": "tok_supermart_local_v1"},
        json={"po_id": "PO-BAD-SUB", "grade": "B", "qty_kg": 500, "agreed_price_rp": 6500, "grade_b_sub_pct": 45.0},
    ).status_code == 422
    assert client.post(
        "/api/v1/supermart/po",
        headers={"X-Scoped-Token": "tok_supermart_local_v1"},
        json={"po_id": "PO-BAD-PRICE", "grade": "A", "qty_kg": 500, "agreed_price_rp": 12000},
    ).status_code == 422
    r_po_ok = client.post(
        "/api/v1/supermart/po",
        headers={"X-Scoped-Token": "tok_supermart_local_v1"},
        json={"po_id": "PO-TEST-V21", "lot_id": "H001", "grade": "A", "qty_kg": 1000, "agreed_price_rp": 10000},
    )
    assert r_po_ok.status_code == 200
    assert r_po_ok.json()["purchase_order"]["status"] == "CONFIRMED"

    # 4. Goods Receipt SLA check (7-12 C SOP)
    r_sla_ok = client.post(
        "/api/v1/supermart/goods-receipt-sla",
        headers={"X-Scoped-Token": "tok_supermart_local_v1"},
        json={"lot_id": "H001", "delivered_temp_c": 9.4, "arrival_min": 95, "deadline_min": 260},
    )
    assert r_sla_ok.status_code == 200
    assert r_sla_ok.json()["sla_verdict"]["sla_status"] == "ACCEPTED_ON_TIME"

    r_sla_hot = client.post(
        "/api/v1/supermart/goods-receipt-sla",
        headers={"X-Scoped-Token": "tok_supermart_local_v1"},
        json={"lot_id": "H001", "delivered_temp_c": 14.5, "arrival_min": 95, "deadline_min": 260},
    )
    assert r_sla_hot.status_code == 200
    assert r_sla_hot.json()["sla_verdict"]["sla_status"] == "REJECTED_TEMP_BREACH"


def test_cross_enterprise_closed_loop_vrptw_dock_sync():
    orch = AgriChainOrchestrator()
    st_rain = orch.run_cycle(trigger_mode="EXTREME_RAIN", adaptive_replanning=True)
    synced = st_rain["vrptw_plan"].get("dock_windows_synced_nodes", [])
    assert "FreshFood_Plant" in synced
    assert "SuperMart_DC" in synced
    assert st_rain["vrptw_plan"]["time_window_violations"] == 0
    assert len(st_rain["supermart_horizon_7d"]["horizon_7d"]) == 7
    assert st_rain["supermart_horizon_7d"]["flash_promo_absorption"]["enabled"] is True
    assert len(st_rain["goods_receipt_sla"]) >= 1
    assert all(s["sla_status"] == "ACCEPTED_ON_TIME" for s in st_rain["goods_receipt_sla"])

    st_fail = orch.run_cycle(trigger_mode="FOOD_SAFETY_FAIL", failed_food_safety_lots=["H003"])
    assert len(st_fail["freshfood_qc_feedback"]["feedback_to_agrofarm"]) >= 1
    assert len(st_fail["freshfood_qc_feedback"]["waste_valorization_plan"]) >= 1


def test_selective_llm_architecture_only_global_koperasi_freshfood_use_llm():
    from config.settings import AGENT_MODEL_PROFILES

    # Only AGT-02 (Koperasi), AGT-03 (FreshFood), and AGT-06 (Global) use LLM
    for aid in ("AGT-02", "AGT-03", "AGT-06"):
        assert AGENT_MODEL_PROFILES[aid].uses_llm is True
    for aid in ("AGT-01", "AGT-04", "AGT-05"):
        assert AGENT_MODEL_PROFILES[aid].uses_llm is False
        assert AGENT_MODEL_PROFILES[aid].provider == "deterministic"

    orch = AgriChainOrchestrator(homogeneous_frontier=False)
    st = orch.run_cycle(trigger_mode="COLD_STORAGE_FAILURE", adaptive_replanning=True)
    tel = st["global_kpis"]["llm_telemetry"]
    assert tel["routing_mode"] == "SELECTIVE_3_LLM_HYBRID"
    assert tel["llm_agents_active"] == ["AGT-02", "AGT-03", "AGT-06"]
    assert tel["deterministic_ml_agents"] == ["AGT-01", "AGT-04", "AGT-05"]

    for call in tel["calls"]:
        if call["agent_id"] in ("AGT-01", "AGT-04", "AGT-05"):
            assert call["mode"] == "DETERMINISTIC_ML_RULE"
            assert call["input_tokens"] == 0
            assert call["output_tokens"] == 0
            assert call["cost_usd"] == 0.0
        else:
            assert call["mode"] in ("POLICY_GROUNDED_SIMULATED", "LIVE_API", "POLICY_GROUNDED_FALLBACK")
            assert call["input_tokens"] > 0
            assert call["cost_usd"] > 0.0
