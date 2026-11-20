"""FastAPI Authorized Multi-Enterprise Gateway & A2A Discovery Service (Bab 5.3 & 7.4)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from src.agents.orchestrator import AgriChainOrchestrator
from src.protocols.security import verify_scoped_token

app = FastAPI(
    title="AgriChain Agentic AI — Multi-Enterprise API Gateway",
    version="1.0.0",
    description="A2A-Inspired & GS1 EPCIS 2.0 Authorized API Gateway for 5 Independent Enterprises + Global Orchestrator.",
)

_orchestrator: Optional[AgriChainOrchestrator] = None
_cycle_store: Dict[str, Dict[str, Any]] = {}


def get_orchestrator() -> AgriChainOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgriChainOrchestrator()
    return _orchestrator


class CycleRequest(BaseModel):
    trigger_mode: str = "NORMAL"  # NORMAL | COLD_STORAGE_FAILURE | DEMAND_SURGE | FOOD_SAFETY_FAIL | COMPOUND
    adaptive_replanning: bool = True
    auto_approve_hitl: bool = False
    demand_override_kg: Optional[float] = None


@app.get("/api/v1/health")
def health_check() -> Dict[str, str]:
    return {"status": "healthy", "ecosystem": "AgriChain Multi-Enterprise Agentic AI", "agents": "6"}


@app.get("/.well-known/agent.json")
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


@app.post("/api/v1/orchestrator/run-cycle")
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
        auto_approve_hitl=req.auto_approve_hitl,
        demand_override_kg=req.demand_override_kg,
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
        "message_count": len(result["messages"]),
    }


@app.post("/api/v1/orchestrator/hitl/{cycle_id}/approve")
def approve_hitl(cycle_id: str, operator_name: str = "ControlCenterOperator") -> Dict[str, Any]:
    if cycle_id not in _cycle_store:
        raise HTTPException(status_code=404, detail="Cycle ID not found")
    st = _cycle_store[cycle_id]
    st["hitl_status"] = "HUMAN_APPROVED"
    st["global_kpis"]["hitl_status"] = "HUMAN_APPROVED"
    get_orchestrator().audit.record("HITL_MANUAL_APPROVAL", operator_name, {"cycle_id": cycle_id})
    return {"cycle_id": cycle_id, "hitl_status": "HUMAN_APPROVED", "approved_by": operator_name}
