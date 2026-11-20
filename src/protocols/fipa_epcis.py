"""A2A-Inspired Messaging, FIPA-ACL Performatives, and GS1 EPCIS 2.0 Schemas (Bab 7.3)."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

WIB = timezone(timedelta(hours=7))


def now_wib_iso() -> str:
    return datetime.now(WIB).isoformat(timespec="seconds")


class FIPAPerformative(str, Enum):
    REQUEST = "REQUEST"
    INFORM = "INFORM"
    CFP = "CFP"
    PROPOSE = "PROPOSE"
    COUNTER_PROPOSE = "COUNTER_PROPOSE"
    ACCEPT_PROPOSAL = "ACCEPT_PROPOSAL"
    REJECT_PROPOSAL = "REJECT_PROPOSAL"
    COMMIT = "COMMIT"
    FAILURE = "FAILURE"


class SensorReport(BaseModel):
    type: str = "gs1:Temperature"
    value: float
    uom: str = "CEL"
    exception: Optional[str] = None


class SensorElement(BaseModel):
    sensorMetadata: Dict[str, Any]
    sensorReport: List[SensorReport]


class EPCISEvent(BaseModel):
    type: str = "ObjectEvent"  # ObjectEvent | AggregationEvent | TransformationEvent | TransactionEvent
    action: str = "OBSERVE"    # ADD | OBSERVE | DELETE
    bizStep: str = "urn:epcglobal:cbv:bizstep:storing"
    disposition: str = "urn:epcglobal:cbv:disp:active"
    readPoint: Dict[str, str] = Field(default_factory=lambda: {"id": "urn:epc:id:sgln:8991234.00001.0"})
    epcList: List[str] = Field(default_factory=list)
    sensorElementList: Optional[List[SensorElement]] = None


class A2AMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: f"MSG-{uuid.uuid4().hex[:10].upper()}")
    conversation_id: str
    sender: str
    receiver: str
    performative: FIPAPerformative
    protocol: str = "A2A-EPCIS-2.0"
    negotiation_round: int = 0
    timestamp: str = Field(default_factory=now_wib_iso)
    epcis_event: Optional[EPCISEvent] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class AgentCard(BaseModel):
    """A2A Agent Discovery Card exposed at /.well-known/agent.json."""
    agent_id: str
    name: str
    enterprise: str
    role: str
    domain_model: str
    llm_model: str
    protocols: List[str] = ["A2A-EPCIS-2.0", "FIPA-CONTRACT-NET"]
    endpoint: str
    shared_capabilities: List[str]
    private_data_protected: List[str]
    autonomy_level: str


class HarvestBatch(BaseModel):
    lot_id: str
    qty_kg: float
    grade: str  # A, B, C, Reject
    shelf_life_days: int
    ask_price_rp: float
    food_safety_approved: bool = True
    harvest_date: str = "2026-11-20"
    defect_ratio: float = 0.03
    cnn_confidence: float = 0.94


class DisruptionEvent(BaseModel):
    event_type: str  # COLD_STORAGE_FAILURE | DEMAND_SURGE | FOOD_SAFETY_REJECTION | COMPOUND
    previous_capacity_kg: float = 3000.0
    effective_capacity_kg: float = 1000.0
    capacity_drop_pct: float = 66.7
    demand_surge_kg: Optional[float] = None
    affected_zones: List[str] = Field(default_factory=lambda: ["Z-2", "Z-3"])
    anomaly_score: float = 0.94
    recommended_3pl_backup_kg: float = 1500.0
    failed_food_safety_lots: List[str] = Field(default_factory=list)
