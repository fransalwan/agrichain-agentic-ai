"""Data Sovereignty Firewall, Scoped Token Auth, and NIST AI RMF Audit Trail (Bab 4.5 & 7.5)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Set

from src.protocols.fipa_epcis import now_wib_iso

# Strictly private attributes that MUST NEVER leak across enterprise API boundaries (Tabel 4.5)
STRICTLY_PRIVATE_FIELDS: Dict[str, Set[str]] = {
    "AgroFarm": {"production_cost_per_kg", "hpp_rp", "farmer_personal_id", "farmer_name", "plot_gps_private"},
    "Koperasi Tani": {"floor_price_rp", "reservation_price_rp", "coop_margin_rp", "farmer_payout_detail"},
    "FreshFood Processing": {"secret_recipe_formula", "internal_line_cost_rp", "factory_margin_rp"},
    "ColdChain Logistics": {"other_client_gps", "internal_fleet_lease_rp", "logistics_margin_rp"},
    "SuperMart": {"ceiling_price_rp", "retail_margin_pct", "customer_pii", "pos_customer_id"},
}

ALL_PRIVATE_KEYS: Set[str] = set().union(*STRICTLY_PRIVATE_FIELDS.values())

# Simulated Scoped JWT-like API tokens per enterprise
SCOPED_TOKENS: Dict[str, str] = {
    "AGT-01": "tok_agrofarm_shared_scope_v1",
    "AGT-02": "tok_koperasi_shared_scope_v1",
    "AGT-03": "tok_freshfood_shared_scope_v1",
    "AGT-04": "tok_coldchain_shared_scope_v1",
    "AGT-05": "tok_supermart_shared_scope_v1",
    "AGT-06": "tok_orchestrator_global_scope_v1",
}


def verify_scoped_token(agent_id: str, token: str) -> bool:
    return SCOPED_TOKENS.get(agent_id) == token or token == SCOPED_TOKENS["AGT-06"]


def sanitize_outbound_payload(enterprise: str, payload: Dict[str, Any]) -> tuple[Dict[str, Any], List[str]]:
    """Strip any strictly private keys recursively before data leaves an enterprise boundary.
    Returns (sanitized_payload, list_of_blocked_keys)."""
    forbidden = STRICTLY_PRIVATE_FIELDS.get(enterprise, set()) | ALL_PRIVATE_KEYS
    blocked: List[str] = []

    def _clean(obj: Any) -> Any:
        if isinstance(obj, dict):
            cleaned = {}
            for k, v in obj.items():
                if k in forbidden:
                    blocked.append(k)
                    continue
                cleaned[k] = _clean(v)
            return cleaned
        if isinstance(obj, list):
            return [_clean(item) for item in obj]
        return obj

    return _clean(payload), blocked


def detect_privacy_leak(payload: Dict[str, Any]) -> List[str]:
    """Audit helper: detect if any private field leaked into a cross-enterprise payload."""
    leaked: List[str] = []

    def _scan(obj: Any) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ALL_PRIVATE_KEYS:
                    leaked.append(k)
                _scan(v)
        elif isinstance(obj, list):
            for item in obj:
                _scan(item)

    _scan(payload)
    return leaked


class ImmutableAuditTrail:
    """Append-only cryptographic hash-chained audit log conforming to NIST AI RMF 1.0."""

    def __init__(self, log_path: Path | None = None):
        self.log_path = log_path
        self.entries: List[Dict[str, Any]] = []
        self._prev_hash = "GENESIS_0000000000000000"

    def record(self, event_type: str, actor: str, details: Dict[str, Any]) -> Dict[str, Any]:
        # Guard: ensure audit trail itself never persists private fields
        safe_details, _ = sanitize_outbound_payload("ALL", details)
        entry = {
            "seq": len(self.entries) + 1,
            "timestamp": now_wib_iso(),
            "event_type": event_type,
            "actor": actor,
            "details": safe_details,
            "prev_hash": self._prev_hash,
        }
        raw = json.dumps(entry, sort_keys=True, default=str).encode("utf-8")
        entry_hash = hashlib.sha256(raw).hexdigest()[:16]
        entry["hash"] = entry_hash
        self._prev_hash = entry_hash
        self.entries.append(entry)

        if self.log_path is not None:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        return entry

    def verify_chain(self) -> bool:
        prev = "GENESIS_0000000000000000"
        for e in self.entries:
            check = {k: v for k, v in e.items() if k != "hash"}
            if check["prev_hash"] != prev:
                return False
            expected = hashlib.sha256(json.dumps(check, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]
            if expected != e["hash"]:
                return False
            prev = e["hash"]
        return True
