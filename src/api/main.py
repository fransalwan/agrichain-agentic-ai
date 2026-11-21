"""FastAPI Decoupled Multi-Enterprise API Gateway v2.0 (Server-Side RBAC, AgroFarm & ColdChain Local APIs)."""
from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field, model_validator

from config.settings import DATA_DIR, RESULTS_DIR, settings
from src.agents.orchestrator import AgriChainOrchestrator
from src.protocols.fipa_epcis import now_wib_iso
from src.protocols.security import (
    redact_records_for_scope,
    resolve_token_scope,
    verify_scoped_token,
)

app = FastAPI(
    title="AgriChain Agentic AI — Multi-Enterprise API Gateway v2.0",
    version="2.0.0",
    description=(
        "Decoupled A2A / FIPA-ACL / GS1 EPCIS 2.0 API Gateway with Server-Side Data Sovereignty Redaction, "
        "AgroFarm NDVI/PI80 Services, ColdChain VRPTW + XGBoost ETA + Fleet/Shipments CRUD, and LangGraph Orchestrator."
    ),
)

_orchestrators: Dict[bool, AgriChainOrchestrator] = {}
_cycle_store: Dict[str, Dict[str, Any]] = {}

# Local ColdChain Operational Master Stores (Fleet & Shipments Inbox per ColdChain Revised UI/UX)
_fleet_store: List[Dict[str, Any]] = [
    {"vehicle_id": "V001", "reefer_type": "Chilled Reefer 6-Wheel", "capacity_kg": 3000, "min_temp_c": 7.0, "max_temp_c": 12.0, "status": "Available", "driver_ref": "D-001 (Budi S.)", "maintenance_due": "2026-12-15"},
    {"vehicle_id": "V002", "reefer_type": "Heavy Chilled Reefer", "capacity_kg": 5000, "min_temp_c": 7.0, "max_temp_c": 12.0, "status": "Available", "driver_ref": "D-002 (Agus W.)", "maintenance_due": "2026-12-22"},
    {"vehicle_id": "V003", "reefer_type": "Medium Reefer Box", "capacity_kg": 2000, "min_temp_c": 7.0, "max_temp_c": 12.0, "status": "Maintenance", "driver_ref": "D-003 (Hendra K.)", "maintenance_due": "2026-11-23"},
    {"vehicle_id": "V004", "reefer_type": "Chilled Reefer 6-Wheel", "capacity_kg": 4000, "min_temp_c": 7.0, "max_temp_c": 12.0, "status": "In Transit", "driver_ref": "D-004 (Slamet R.)", "maintenance_due": "2027-01-05"},
]

_shipment_store: List[Dict[str, Any]] = [
    {"shipment_id": "SH001", "lot_id": "H001", "product": "Tomato", "grade": "A", "quantity_kg": 2000, "pickup": "Koperasi_Hub", "destination": "SuperMart_DC", "ready_time": "08:00", "deadline": "12:00", "req_temp_min_c": 7.0, "req_temp_max_c": 12.0, "shelf_life_hours": 120, "priority": "High", "status": "Ready for Planning"},
    {"shipment_id": "SH002", "lot_id": "H002", "product": "Tomato", "grade": "B", "quantity_kg": 1500, "pickup": "Koperasi_Hub", "destination": "FreshFood_Plant", "ready_time": "08:00", "deadline": "13:00", "req_temp_min_c": 7.0, "req_temp_max_c": 12.0, "shelf_life_hours": 72, "priority": "High", "status": "Ready for Planning"},
    {"shipment_id": "SH003", "lot_id": "H003", "product": "Tomato", "grade": "C", "quantity_kg": 1000, "pickup": "Koperasi_Hub", "destination": "FreshFood_Plant", "ready_time": "08:00", "deadline": "11:00", "req_temp_min_c": 7.0, "req_temp_max_c": 12.0, "shelf_life_hours": 48, "priority": "Critical", "status": "Ready for Planning"},
]


def get_orchestrator(homogeneous_frontier: bool = False) -> AgriChainOrchestrator:
    if homogeneous_frontier not in _orchestrators:
        _orchestrators[homogeneous_frontier] = AgriChainOrchestrator(homogeneous_frontier=homogeneous_frontier)
    return _orchestrators[homogeneous_frontier]


# ---------------------------------------------------------------------------
# Request Schemas with Strict Validation
# ---------------------------------------------------------------------------
class CycleRequest(BaseModel):
    trigger_mode: str = "NORMAL"  # NORMAL | COLD_STORAGE_FAILURE | DEMAND_SURGE | FOOD_SAFETY_FAIL | COMPOUND | DEADLOCK | EXTREME_RAIN | SENSOR_OUTAGE
    adaptive_replanning: bool = True
    use_milp: bool = True
    homogeneous_frontier: bool = False
    auto_approve_hitl: bool = False
    demand_override_kg: Optional[float] = None
    cold_storage_cap_override_kg: Optional[float] = None


class AgroFarmPredictRequest(BaseModel):
    block_id: str = "BLK-11"
    lot_id: str = "H003"
    area_ha: float = Field(default=0.70, gt=0)
    avg_temp_c: float = 27.6
    soil_moisture_pct: float = 69.0
    rainfall_mm: float = 24.0
    fertilizer_kg_ha: float = 165.0
    crop_age_days: int = Field(default=78, ge=30, le=120)
    ndvi: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    grade: str = "C"
    shelf_life_days: int = Field(default=2, ge=1)
    extreme_rain_flag: bool = False
    sensor_offline_days: int = Field(default=0, ge=0)


class VehicleCreateRequest(BaseModel):
    vehicle_id: str = Field(..., min_length=2)
    reefer_type: str = "Chilled Reefer"
    capacity_kg: float = Field(..., gt=0)
    min_temp_c: float = 7.0
    max_temp_c: float = 12.0
    status: str = "Available"
    driver_ref: str = "D-005"
    maintenance_due: str = "2027-01-15"

    @model_validator(mode="after")
    def check_temp_range(self):
        if self.min_temp_c >= self.max_temp_c:
            raise ValueError("min_temp_c harus lebih kecil dari max_temp_c")
        return self


class ShipmentCreateRequest(BaseModel):
    shipment_id: str = Field(..., min_length=2)
    lot_id: str = "H004"
    product: str = "Tomato"
    grade: str = "A"
    quantity_kg: float = Field(..., gt=0)
    pickup: str = "Koperasi_Hub"
    destination: str = "SuperMart_DC"
    ready_time: str = "08:00"
    deadline: str = "12:00"
    req_temp_min_c: float = 7.0
    req_temp_max_c: float = 12.0
    shelf_life_hours: int = Field(default=72, gt=0)
    priority: str = "High"

    @model_validator(mode="after")
    def validate_shipment_rules(self):
        if self.deadline <= self.ready_time:
            raise ValueError("deadline tidak boleh lebih awal atau sama dengan ready_time")
        if self.req_temp_min_c >= self.req_temp_max_c:
            raise ValueError("req_temp_min_c harus lebih kecil dari req_temp_max_c")
        return self


class VRPTWRequest(BaseModel):
    scenario: str = "NORMAL"  # NORMAL | ROAD_DISRUPTION | VEHICLE_BREAKDOWN | COLD_STORAGE_DROP
    traffic_level: int = Field(default=1, ge=0, le=2)


class ETARequest(BaseModel):
    distance_km: float = Field(default=42.0, gt=0)
    traffic_level: int = Field(default=1, ge=0, le=2)
    num_stops: int = Field(default=2, ge=1)
    weather_severity: int = Field(default=0, ge=0, le=2)
    departure_hour: int = Field(default=8, ge=0, le=23)


# ---------------------------------------------------------------------------
# Health & Discovery Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/v1/health", tags=["Global Control Center"])
def health_check() -> Dict[str, Any]:
    orch = get_orchestrator()
    return {
        "status": "healthy",
        "ecosystem": "AgriChain Multi-Enterprise Agentic AI v2.0",
        "agents": 6,
        "audit_chain_valid": orch.audit.verify_chain(),
        "tomato_safe_temp_c": [settings.tomato_safe_temp_min_c, settings.tomato_safe_temp_max_c],
        "server_timestamp": now_wib_iso(),
    }


@app.get("/.well-known/agent.json", tags=["A2A Discovery"])
def a2a_agent_cards() -> Dict[str, Any]:
    orch = get_orchestrator()
    cards = [
        orch.agrofarm.card().model_dump(),
        orch.koperasi.card().model_dump(),
        orch.freshfood.card().model_dump(),
        orch.coldchain.card().model_dump(),
        orch.supermart.card().model_dump(),
        {
            "agent_id": "AGT-06",
            "name": "Global Orchestrator & Replanning Agent",
            "enterprise": "Global Control Center",
            "domain_model": "MILP Solver (PuLP/CBC) + FEFO",
            "llm_model": "GPT-4o",
            "endpoint": "/api/v1/orchestrator",
            "protocols": ["A2A-EPCIS-2.0", "FIPA-CONTRACT-NET", "NIST-AI-RMF-HITL"],
        },
    ]
    return {"protocol_version": "A2A-EPCIS-2.0", "agent_count": len(cards), "agents": cards}


@app.get("/api/v1/enterprises/{enterprise_id}/status", tags=["Local Enterprise Services"])
def enterprise_local_status(enterprise_id: str) -> Dict[str, Any]:
    orch = get_orchestrator()
    key = enterprise_id.lower().strip()
    agent_map = {
        "agrofarm": (orch.agrofarm, "PostgreSQL (local_dbs/agrofarm_pg.sqlite)", "AGT-01_AgroFarm"),
        "koperasi": (orch.koperasi, "MySQL (local_dbs/koperasi_mysql.sqlite)", "AGT-02_Koperasi"),
        "freshfood": (orch.freshfood, "MongoDB JSON (freshfood_tomato_qc.json + RGB NPZ)", "AGT-03_FreshFood"),
        "coldchain": (orch.coldchain, "TimescaleDB (local_dbs/coldchain_timescaledb.sqlite)", "AGT-04_ColdChain"),
        "supermart": (orch.supermart, "MySQL (local_dbs/supermart_mysql.sqlite)", "AGT-05_SuperMart"),
    }
    if key not in agent_map:
        raise HTTPException(status_code=404, detail=f"Unknown enterprise_id '{enterprise_id}'. Valid: {list(agent_map.keys())}")

    agent_obj, db_desc, metric_key = agent_map[key]
    card = agent_obj.card().model_dump()
    ml_metrics: Dict[str, Any] = {}
    metrics_path = RESULTS_DIR / "ml_metrics.json"
    if metrics_path.exists():
        raw_m = json.loads(metrics_path.read_text(encoding="utf-8"))
        ml_metrics = raw_m.get("enterprise_models", raw_m).get(metric_key, {})

    return {
        "enterprise_id": key,
        "agent_card": card,
        "local_database": db_desc,
        "data_sovereignty_policy": "STRICT_ZERO_DIRECT_DB_ACCESS",
        "private_fields_masked": card["private_data_protected"],
        "local_model_metrics": ml_metrics,
        "status": "ONLINE",
        "timestamp": now_wib_iso(),
    }


# ---------------------------------------------------------------------------
# AgroFarm Local Endpoints (Pillar 2 & 3)
# ---------------------------------------------------------------------------
@app.get("/api/v1/agrofarm/monitoring", tags=["AgroFarm Local Service (AGT-01)"])
def agrofarm_monitoring(extreme_rain: bool = False, sensor_outage: bool = False) -> Dict[str, Any]:
    orch = get_orchestrator()
    blocks = orch.agrofarm.model.evaluate_block_monitoring(extreme_rain=extreme_rain, sensor_outage=sensor_outage)
    return {
        "enterprise": "AgroFarm",
        "model_version": orch.agrofarm.model.MODEL_VERSION,
        "blocks": blocks,
        "stale_alert": any(b["stale_data"] for b in blocks),
        "timestamp": now_wib_iso(),
    }


@app.post("/api/v1/agrofarm/predict", tags=["AgroFarm Local Service (AGT-01)"])
def agrofarm_predict_block(req: AgroFarmPredictRequest) -> Dict[str, Any]:
    orch = get_orchestrator()
    rec = req.model_dump()
    if rec["ndvi"] is None:
        rec.pop("ndvi")
    pred = orch.agrofarm.model.predict_batch([rec])[0]
    return {
        "prediction": pred,
        "feature_importance": orch.agrofarm.model.feature_importance,
        "model_metrics": orch.agrofarm.model.metrics,
        "timestamp": now_wib_iso(),
    }


# ---------------------------------------------------------------------------
# ColdChain Local Endpoints: Fleet CRUD, Shipments CRUD, VRPTW, XGBoost ETA
# ---------------------------------------------------------------------------
@app.get("/api/v1/coldchain/fleet", tags=["ColdChain Local Service (AGT-04)"])
def list_fleet() -> Dict[str, Any]:
    return {"count": len(_fleet_store), "vehicles": _fleet_store, "timestamp": now_wib_iso()}


@app.post("/api/v1/coldchain/fleet", tags=["ColdChain Local Service (AGT-04)"])
def upsert_vehicle(req: VehicleCreateRequest, x_scoped_token: str = Header(default="tok_coldchain_local_v1")) -> Dict[str, Any]:
    scope = resolve_token_scope(x_scoped_token)
    if scope not in ("coldchain", "global"):
        raise HTTPException(status_code=403, detail="Only ColdChain Fleet Manager or Global Operator may modify fleet")
    item = req.model_dump()
    existing_idx = next((i for i, v in enumerate(_fleet_store) if v["vehicle_id"] == item["vehicle_id"]), None)
    action = "UPDATE_VEHICLE" if existing_idx is not None else "CREATE_VEHICLE"
    if existing_idx is not None:
        _fleet_store[existing_idx] = item
    else:
        _fleet_store.append(item)
    entry = get_orchestrator().audit.record(action, f"FleetManager({scope})", item, model_version="fleet-master-v2")
    return {"action": action, "vehicle": item, "audit_hash": entry["hash"]}


@app.get("/api/v1/coldchain/shipments", tags=["ColdChain Local Service (AGT-04)"])
def list_shipments() -> Dict[str, Any]:
    return {"count": len(_shipment_store), "shipments": _shipment_store, "timestamp": now_wib_iso()}


@app.post("/api/v1/coldchain/shipments", tags=["ColdChain Local Service (AGT-04)"])
def create_shipment(req: ShipmentCreateRequest, x_scoped_token: str = Header(default="tok_coldchain_local_v1")) -> Dict[str, Any]:
    scope = resolve_token_scope(x_scoped_token)
    if scope not in ("coldchain", "koperasi", "global"):
        raise HTTPException(status_code=403, detail="Unauthorized role for shipment submission")
    item = {**req.model_dump(), "status": "Ready for Planning"}
    if any(s["shipment_id"] == item["shipment_id"] for s in _shipment_store):
        raise HTTPException(status_code=409, detail=f"Shipment ID {item['shipment_id']} sudah terdaftar")
    _shipment_store.append(item)
    entry = get_orchestrator().audit.record("CREATE_SHIPMENT", f"Scope({scope})", item, model_version="shipment-inbox-v2")
    return {"status": "CREATED", "shipment": item, "audit_hash": entry["hash"]}


@app.post("/api/v1/coldchain/vrptw", tags=["ColdChain Local Service (AGT-04)"])
def run_coldchain_vrptw(req: VRPTWRequest) -> Dict[str, Any]:
    orch = get_orchestrator()
    plan = orch.coldchain.model.solve_vrptw(scenario=req.scenario, traffic_level=req.traffic_level)
    baseline = orch.coldchain.model.solve_vrptw(scenario="NORMAL", traffic_level=1)
    return {
        "active_plan": plan,
        "normal_baseline": baseline,
        "distance_delta_km": round(plan["optimized_distance_km"] - baseline["optimized_distance_km"], 1),
        "timestamp": now_wib_iso(),
    }


@app.post("/api/v1/coldchain/eta", tags=["ColdChain Local Service (AGT-04)"])
def predict_coldchain_eta(req: ETARequest) -> Dict[str, Any]:
    orch = get_orchestrator()
    pred = orch.coldchain.model.eta_model.predict_eta_minutes(
        distance_km=req.distance_km,
        traffic_level=req.traffic_level,
        num_stops=req.num_stops,
        weather_severity=req.weather_severity,
        departure_hour=req.departure_hour,
    )
    return {"eta": pred, "eta_model_metrics": orch.coldchain.model.eta_model.metrics, "timestamp": now_wib_iso()}


# ---------------------------------------------------------------------------
# Server-Side Privacy-Enforced Data Explorer Endpoint (Pillar 1)
# ---------------------------------------------------------------------------
ALLOWED_TABLES = {
    "agrofarm": {"farm_harvest_history", "active_harvest_lots", "private_costs"},
    "koperasi": {"market_price_negotiations"},
    "freshfood": {"qc_docs"},
    "coldchain": {"cold_storage_telemetry", "fleet_delivery_routes"},
    "supermart": {"retail_pos_sales"},
}


@app.get("/api/v1/data-explorer/{enterprise_id}/{table_name}", tags=["Server-Side Privacy Data Explorer"])
def query_enterprise_data(
    enterprise_id: str,
    table_name: str,
    search: str = "",
    limit: int = 50,
    x_scoped_token: str = Header(default="tok_orchestrator_global_scope_v1"),
) -> Dict[str, Any]:
    """Query isolated enterprise DB with SERVER-SIDE Data Sovereignty redaction based on caller's X-Scoped-Token."""
    caller_scope = resolve_token_scope(x_scoped_token)
    if caller_scope == "unauthorized":
        raise HTTPException(status_code=403, detail="Invalid X-Scoped-Token")

    ent = enterprise_id.lower().strip()
    if ent not in ALLOWED_TABLES or table_name not in ALLOWED_TABLES[ent]:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found in enterprise '{ent}'")

    if ent == "freshfood":
        docs = json.loads((DATA_DIR / "freshfood_tomato_qc.json").read_text(encoding="utf-8"))
        flat = []
        for d in docs:
            row = {k: v for k, v in d.items() if not isinstance(v, dict)}
            for k, v in d.items():
                if isinstance(v, dict):
                    for sk, sv in v.items():
                        row[f"{k}.{sk}"] = sv
            flat.append(row)
        df = pd.DataFrame(flat)
    else:
        sqlite_map = {
            "agrofarm": DATA_DIR / "local_dbs" / "agrofarm_pg.sqlite",
            "koperasi": DATA_DIR / "local_dbs" / "koperasi_mysql.sqlite",
            "coldchain": DATA_DIR / "local_dbs" / "coldchain_timescaledb.sqlite",
            "supermart": DATA_DIR / "local_dbs" / "supermart_mysql.sqlite",
        }
        with sqlite3.connect(sqlite_map[ent]) as conn:
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)

    total_rows = len(df)
    if search.strip():
        mask = df.astype(str).apply(lambda col: col.str.contains(search.strip(), case=False, na=False)).any(axis=1)
        df = df[mask]

    matched_rows = len(df)
    raw_records = df.head(max(1, min(limit, 500))).to_dict(orient="records")
    safe_records, redacted_cols = redact_records_for_scope(raw_records, ent, caller_scope)

    return {
        "enterprise": ent,
        "table": table_name,
        "caller_scope": caller_scope,
        "server_side_firewall": True,
        "total_rows": total_rows,
        "matched_rows": matched_rows,
        "redacted_columns": redacted_cols,
        "records": safe_records,
        "timestamp": now_wib_iso(),
    }


# ---------------------------------------------------------------------------
# Global Orchestrator & HITL Governance Endpoints
# ---------------------------------------------------------------------------
@app.post("/api/v1/orchestrator/run-cycle", tags=["Global Control Center"])
def run_orchestrator_cycle(
    req: CycleRequest,
    x_scoped_token: str = Header(default="tok_orchestrator_global_scope_v1"),
) -> Dict[str, Any]:
    if not verify_scoped_token("AGT-06", x_scoped_token):
        raise HTTPException(status_code=403, detail="Invalid scoped enterprise API token")
    orch = get_orchestrator(homogeneous_frontier=req.homogeneous_frontier)
    result = orch.run_cycle(
        trigger_mode=req.trigger_mode,
        adaptive_replanning=req.adaptive_replanning,
        use_milp=req.use_milp,
        auto_approve_hitl=req.auto_approve_hitl,
        demand_override_kg=req.demand_override_kg,
        cold_storage_cap_override_kg=req.cold_storage_cap_override_kg,
    )
    _cycle_store[result["cycle_id"]] = result
    return {
        "cycle_id": result["cycle_id"],
        "trigger_mode": result["trigger_mode"],
        "global_kpis": result["global_kpis"],
        "allocations": result["milp_result"]["allocations"],
        "unallocated_kg": result["milp_result"]["unallocated_kg"],
        "milp_result": result["milp_result"],
        "enterprise_profits_rp": result["enterprise_profits_rp"],
        "cold_storage_cap_kg": result["cold_storage_cap_kg"],
        "capacity_drop_pct": result["capacity_drop_pct"],
        "allow_grade_b_to_supermart": result["allow_grade_b_to_supermart"],
        "hitl_required": result["hitl_required"],
        "hitl_reasons": result["hitl_reasons"],
        "hitl_status": result["hitl_status"],
        "messages": result["messages"],
        "decision_trace": result["decision_trace"],
        "agent_statuses": result["agent_statuses"],
        "agrofarm_monitoring": result.get("agrofarm_monitoring", []),
        "vrptw_plan": result.get("vrptw_plan", {}),
        "lineage": result.get("lineage", []),
        "executive_briefing": result.get("executive_briefing", ""),
        "data_freshness_warning": result.get("data_freshness_warning"),
        "message_count": len(result["messages"]),
    }


@app.post("/api/v1/orchestrator/hitl/{cycle_id}/approve", tags=["HITL Governance & Audit"])
def approve_hitl(
    cycle_id: str,
    operator_name: str = "ControlCenterOperator",
    note: str = "Approved after verifying Impact Preview & MILP-FEFO replanning",
) -> Dict[str, Any]:
    if cycle_id not in _cycle_store:
        raise HTTPException(status_code=404, detail="Cycle ID not found")
    st = _cycle_store[cycle_id]
    st["hitl_status"] = "HUMAN_APPROVED"
    st["global_kpis"]["hitl_status"] = "HUMAN_APPROVED"
    entry = get_orchestrator().audit.record(
        "HITL_MANUAL_APPROVAL",
        operator_name,
        {"cycle_id": cycle_id, "note": note},
        model_version="orchestrator-v2.0",
        input_reference=cycle_id,
        human_approval="APPROVED",
    )
    return {"cycle_id": cycle_id, "hitl_status": "HUMAN_APPROVED", "approved_by": operator_name, "audit_hash": entry["hash"]}


@app.post("/api/v1/orchestrator/hitl/{cycle_id}/reject", tags=["HITL Governance & Audit"])
def reject_hitl(
    cycle_id: str,
    operator_name: str = "ControlCenterOperator",
    note: str = "Rejected — requires revised commercial negotiation",
) -> Dict[str, Any]:
    if cycle_id not in _cycle_store:
        raise HTTPException(status_code=404, detail="Cycle ID not found")
    st = _cycle_store[cycle_id]
    st["hitl_status"] = "HUMAN_REJECTED"
    st["global_kpis"]["hitl_status"] = "HUMAN_REJECTED"
    entry = get_orchestrator().audit.record(
        "HITL_MANUAL_REJECTION",
        operator_name,
        {"cycle_id": cycle_id, "note": note},
        model_version="orchestrator-v2.0",
        input_reference=cycle_id,
        human_approval="REJECTED",
    )
    return {"cycle_id": cycle_id, "hitl_status": "HUMAN_REJECTED", "rejected_by": operator_name, "audit_hash": entry["hash"]}


@app.get("/api/v1/audit/trail", tags=["HITL Governance & Audit"])
def get_audit_trail(limit: int = 25) -> Dict[str, Any]:
    orch = get_orchestrator()
    audit_path = RESULTS_DIR / "audit_trail.jsonl"
    entries: List[Dict[str, Any]] = []
    if audit_path.exists():
        lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
        for ln in lines[-max(1, min(limit, 200)) :]:
            entries.append(json.loads(ln))
    return {
        "chain_valid": orch.audit.verify_chain(),
        "returned_entries": len(entries),
        "entries": list(reversed(entries)),
        "timestamp": now_wib_iso(),
    }
