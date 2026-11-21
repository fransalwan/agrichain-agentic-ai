"""FastAPI Authorized Multi-Enterprise Gateway & A2A Discovery Service (Bab 5.3 & 7.4)."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from config.settings import DATA_DIR, RESULTS_DIR
from src.agents.orchestrator import AgriChainOrchestrator
from src.protocols.security import verify_scoped_token

app = FastAPI(
    title="AgriChain Agentic AI — Multi-Enterprise API Gateway",
    version="2.0.0",
    description=(
        "A2A-Inspired & GS1 EPCIS 2.0 Authorized API Gateway for 5 Independent Enterprises "
        "(AgroFarm, Koperasi Tani, FreshFood Processing, ColdChain Logistics, SuperMart) + Global Orchestrator."
    ),
)

_orchestrator: Optional[AgriChainOrchestrator] = None
_cycle_store: Dict[str, Dict[str, Any]] = {}


def get_orchestrator() -> AgriChainOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgriChainOrchestrator()
    return _orchestrator


class CycleRequest(BaseModel):
    trigger_mode: str = "NORMAL"  # NORMAL | COLD_STORAGE_FAILURE | DEMAND_SURGE | FOOD_SAFETY_FAIL | COMPOUND | DEADLOCK
    adaptive_replanning: bool = True
    use_milp: bool = True
    auto_approve_hitl: bool = False
    demand_override_kg: Optional[float] = None
    cold_storage_cap_override_kg: Optional[float] = None


class HITLDecisionRequest(BaseModel):
    operator_name: str = "ControlCenterOperator"
    note: str = ""


@app.get("/api/v1/health", tags=["Global Control Center"])
def health_check() -> Dict[str, Any]:
    orch = get_orchestrator()
    return {
        "status": "healthy",
        "ecosystem": "AgriChain Multi-Enterprise Agentic AI",
        "agents": 6,
        "audit_chain_valid": orch.audit.verify_chain(),
    }


@app.get("/.well-known/agent.json", tags=["A2A Discovery"])
def a2a_agent_cards() -> Dict[str, Any]:
    """A2A Agent Card Discovery endpoint for all 6 heterogeneous agents."""
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
    """Per-enterprise local microservice status & KPI summary (Zero-Direct-DB-Access compliant)."""
    orch = get_orchestrator()
    key = enterprise_id.lower().strip()
    agent_map = {
        "agrofarm": (orch.agrofarm, "PostgreSQL (local_dbs/agrofarm_pg.sqlite)", "agrofarm_rf"),
        "koperasi": (orch.koperasi, "MySQL (local_dbs/koperasi_mysql.sqlite)", "koperasi_lgbm"),
        "freshfood": (orch.freshfood, "MongoDB JSON (freshfood_tomato_qc.json + RGB NPZ)", "freshfood_cnn"),
        "coldchain": (orch.coldchain, "TimescaleDB (local_dbs/coldchain_timescaledb.sqlite)", "coldchain_iforest_cvrp"),
        "supermart": (orch.supermart, "MySQL (local_dbs/supermart_mysql.sqlite)", "supermart_xgb"),
    }
    if key not in agent_map:
        raise HTTPException(status_code=404, detail=f"Unknown enterprise_id '{enterprise_id}'. Valid: {list(agent_map.keys())}")

    agent_obj, db_desc, metric_key = agent_map[key]
    card = agent_obj.card().model_dump()
    ml_metrics: Dict[str, Any] = {}
    metrics_path = RESULTS_DIR / "ml_metrics.json"
    if metrics_path.exists():
        with open(metrics_path, "r", encoding="utf-8") as f:
            ml_metrics = json.load(f).get(metric_key, {})

    return {
        "enterprise_id": key,
        "agent_card": card,
        "local_database": db_desc,
        "data_sovereignty_policy": "STRICT_ZERO_DIRECT_DB_ACCESS",
        "private_fields_masked": card["private_data_protected"],
        "local_model_metrics": ml_metrics,
        "status": "ONLINE",
    }


@app.post("/api/v1/orchestrator/run-cycle", tags=["Global Control Center"])
def run_orchestrator_cycle(
    req: CycleRequest,
    x_scoped_token: str = Header(default="tok_orchestrator_global_scope_v1"),
) -> Dict[str, Any]:
    if not verify_scoped_token("AGT-06", x_scoped_token):
        raise HTTPException(status_code=403, detail="Invalid scoped enterprise API token")
    orch = get_orchestrator()
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
        "enterprise_profits_rp": result["enterprise_profits_rp"],
        "hitl_required": result["hitl_required"],
        "hitl_reasons": result["hitl_reasons"],
        "hitl_status": result["hitl_status"],
        "decision_trace": result["decision_trace"],
        "agent_statuses": result["agent_statuses"],
        "message_count": len(result["messages"]),
    }


@app.post("/api/v1/orchestrator/hitl/{cycle_id}/approve", tags=["HITL Governance & Audit"])
def approve_hitl(
    cycle_id: str,
    operator_name: str = "ControlCenterOperator",
    note: str = "Approved after verifying MILP-FEFO replanning impact",
) -> Dict[str, Any]:
    if cycle_id not in _cycle_store:
        raise HTTPException(status_code=404, detail="Cycle ID not found")
    st = _cycle_store[cycle_id]
    st["hitl_status"] = "HUMAN_APPROVED"
    st["global_kpis"]["hitl_status"] = "HUMAN_APPROVED"
    entry = get_orchestrator().audit.record(
        "HITL_MANUAL_APPROVAL", operator_name, {"cycle_id": cycle_id, "note": note}
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
        "HITL_MANUAL_REJECTION", operator_name, {"cycle_id": cycle_id, "note": note}
    )
    return {"cycle_id": cycle_id, "hitl_status": "HUMAN_REJECTED", "rejected_by": operator_name, "audit_hash": entry["hash"]}


@app.get("/api/v1/audit/trail", tags=["HITL Governance & Audit"])
def get_audit_trail(limit: int = 25) -> Dict[str, Any]:
    """Return latest immutable SHA-256 hash-chained audit entries and cryptographic verification status."""
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
    }
