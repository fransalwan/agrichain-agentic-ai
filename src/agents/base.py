"""Base Enterprise Agent with Tool Invocation & Data Sovereignty Firewall."""
from __future__ import annotations

from typing import Any, Dict, List

from config.settings import AGENT_MODEL_PROFILES
from src.llm.router import HeterogeneousLLMRouter
from src.protocols.fipa_epcis import A2AMessage, AgentCard, EPCISEvent, FIPAPerformative
from src.protocols.security import sanitize_outbound_payload


class BaseEnterpriseAgent:
    def __init__(self, agent_id: str, router: HeterogeneousLLMRouter):
        self.agent_id = agent_id
        self.profile = AGENT_MODEL_PROFILES[agent_id]
        self.enterprise = self.profile.enterprise
        self.router = router
        self.blocked_leak_attempts: int = 0

    def get_agent_card(self, endpoint: str, capabilities: List[str], private_fields: List[str], autonomy: str) -> AgentCard:
        return AgentCard(
            agent_id=self.agent_id,
            name=self.profile.agent_name,
            enterprise=self.enterprise,
            role=self.profile.agent_name,
            domain_model=self.profile.domain_model,
            llm_model=self.router.get_profile(self.agent_id).llm_model,
            endpoint=endpoint,
            shared_capabilities=capabilities,
            private_data_protected=private_fields,
            autonomy_level=autonomy,
        )

    def build_safe_message(
        self,
        conversation_id: str,
        receiver: str,
        performative: FIPAPerformative,
        payload: Dict[str, Any],
        protocol: str = "A2A-EPCIS-2.0",
        negotiation_round: int = 0,
        epcis_event: EPCISEvent | None = None,
    ) -> A2AMessage:
        safe_payload, blocked = sanitize_outbound_payload(self.enterprise, payload)
        self.blocked_leak_attempts += len(blocked)
        return A2AMessage(
            conversation_id=conversation_id,
            sender=f"{self.agent_id}:{self.enterprise.replace(' ', '')}",
            receiver=receiver,
            performative=performative,
            protocol=protocol,
            negotiation_round=negotiation_round,
            epcis_event=epcis_event,
            payload=safe_payload,
        )
