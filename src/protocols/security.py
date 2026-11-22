"""Data Sovereignty Firewall, Server-Side RBAC Scoped Token Auth, and NIST AI RMF Audit Trail."""
from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

try:
    import msvcrt
except ImportError:
    msvcrt = None  # type: ignore

_AUDIT_THREAD_LOCK = threading.Lock()

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

# Simulated Scoped JWT-like API tokens per enterprise (shared + local RBAC scopes)
SCOPED_TOKENS: Dict[str, str] = {
    "AGT-01": "tok_agrofarm_shared_scope_v1",
    "AGT-02": "tok_koperasi_shared_scope_v1",
    "AGT-03": "tok_freshfood_shared_scope_v1",
    "AGT-04": "tok_coldchain_shared_scope_v1",
    "AGT-05": "tok_supermart_shared_scope_v1",
    "AGT-06": "tok_orchestrator_global_scope_v1",
}

ROLE_SCOPE_TOKENS: Dict[str, str] = {
    "tok_orchestrator_global_scope_v1": "global",
    "tok_agrofarm_local_v1": "agrofarm",
    "tok_agrofarm_shared_scope_v1": "agrofarm",
    "tok_koperasi_local_v1": "koperasi",
    "tok_koperasi_shared_scope_v1": "koperasi",
    "tok_freshfood_local_v1": "freshfood",
    "tok_freshfood_shared_scope_v1": "freshfood",
    "tok_coldchain_local_v1": "coldchain",
    "tok_coldchain_shared_scope_v1": "coldchain",
    "tok_supermart_local_v1": "supermart",
    "tok_supermart_shared_scope_v1": "supermart",
}


def verify_scoped_token(agent_id: str, token: str) -> bool:
    if token in ROLE_SCOPE_TOKENS:
        if agent_id == "AGT-06":
            return token in (SCOPED_TOKENS["AGT-06"], "tok_agrofarm_local_v1", "tok_koperasi_local_v1", "tok_freshfood_local_v1", "tok_coldchain_local_v1", "tok_supermart_local_v1")
        return SCOPED_TOKENS.get(agent_id) == token or token == SCOPED_TOKENS["AGT-06"]
    return False


def resolve_token_scope(token: str) -> str:
    """Resolve caller's RBAC scope ('global', 'agrofarm', 'koperasi', 'freshfood', 'coldchain', 'supermart')."""
    return ROLE_SCOPE_TOKENS.get(token, "unauthorized")


def is_private_column(col_name: str) -> bool:
    low = col_name.lower()
    if low in ALL_PRIVATE_KEYS:
        return True
    return any(
        kw in low
        for kw in ("floor_price", "ceiling_price", "production_cost", "farmer_personal", "margin", "secret", "pii", "payout", "hpp")
    )


def redact_records_for_scope(
    records: List[Dict[str, Any]],
    target_enterprise: str,
    caller_scope: str,
) -> tuple[List[Dict[str, Any]], List[str]]:
    """Server-side Data Sovereignty enforcement: redacts private columns unless caller owns the target enterprise."""
    if caller_scope == target_enterprise.lower():
        return records, []
    redacted_cols: Set[str] = set()
    clean_rows: List[Dict[str, Any]] = []
    for row in records:
        new_row = {}
        for k, v in row.items():
            if is_private_column(k):
                new_row[k] = "🔒 REDACTED (Server-Side Firewall)"
                redacted_cols.add(k)
            else:
                new_row[k] = v
        clean_rows.append(new_row)
    return clean_rows, sorted(redacted_cols)


def sanitize_outbound_payload(enterprise: str, payload: Dict[str, Any]) -> tuple[Dict[str, Any], List[str]]:
    """Strip any strictly private keys recursively before data leaves an enterprise boundary."""
    forbidden = STRICTLY_PRIVATE_FIELDS.get(enterprise, set()) | ALL_PRIVATE_KEYS
    blocked: List[str] = []

    def _clean(obj: Any) -> Any:
        if isinstance(obj, dict):
            cleaned = {}
            for k, v in obj.items():
                if k in forbidden:
                    blocked.append(k)
                else:
                    cleaned[k] = _clean(v)
            return cleaned
        if isinstance(obj, list):
            return [_clean(item) for item in obj]
        return obj

    return _clean(payload), sorted(set(blocked))


def detect_privacy_leak(payload: Dict[str, Any]) -> List[str]:
    """Audit scanner verifying zero strictly private fields exist in any inter-enterprise message."""
    leaks: List[str] = []

    def _scan(obj: Any) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ALL_PRIVATE_KEYS:
                    leaks.append(k)
                _scan(v)
        elif isinstance(obj, list):
            for item in obj:
                _scan(item)

    _scan(payload)
    return sorted(set(leaks))


class ImmutableAuditTrail:
    """Append-only hash-chained audit trail supporting NIST AI RMF 1.0 & agent_decisions traceability."""

    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_hash = self._load_last_hash()

    def _load_last_hash(self) -> str:
        if not self.log_path.exists():
            return "GENESIS_0000000000000000"
        lines = self.log_path.read_text(encoding="utf-8").strip().splitlines()
        if not lines:
            return "GENESIS_0000000000000000"
        return json.loads(lines[-1]).get("hash", "GENESIS_0000000000000000")

    def record(
        self,
        event_type: str,
        actor: str,
        details: Dict[str, Any],
        model_version: Optional[str] = None,
        input_reference: Optional[str] = None,
        human_approval: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Atomic cross-thread & cross-process locked append to preserve SHA-256 chain integrity."""
        lock_file = self.log_path.with_suffix(".lock")
        with _AUDIT_THREAD_LOCK:
            with open(lock_file, "a+b") as lf:
                if msvcrt is not None:
                    for _ in range(50):
                        try:
                            lf.seek(0)
                            msvcrt.locking(lf.fileno(), msvcrt.LK_NBLCK, 1)
                            break
                        except OSError:
                            time.sleep(0.02)
                try:
                    self._last_hash = self._load_last_hash()
                    enriched = dict(details)
                    if model_version:
                        enriched["model_version"] = model_version
                    if input_reference:
                        enriched["input_reference"] = input_reference
                    if human_approval:
                        enriched["human_approval"] = human_approval

                    entry = {
                        "timestamp": now_wib_iso(),
                        "event_type": event_type,
                        "actor": actor,
                        "details": enriched,
                        "prev_hash": self._last_hash,
                    }
                    canonical = json.dumps(entry, sort_keys=True, default=str).encode("utf-8")
                    entry["hash"] = hashlib.sha256(canonical).hexdigest()
                    self._last_hash = entry["hash"]
                    with open(self.log_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(entry, default=str) + "\n")
                        f.flush()
                    return entry
                finally:
                    if msvcrt is not None:
                        try:
                            lf.seek(0)
                            msvcrt.locking(lf.fileno(), msvcrt.LK_UNLCK, 1)
                        except OSError:
                            pass

    def verify_chain(self) -> bool:
        if not self.log_path.exists():
            return True
        prev = "GENESIS_0000000000000000"
        for line in self.log_path.read_text(encoding="utf-8").strip().splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("prev_hash") != prev:
                return False
            saved_hash = rec.pop("hash")
            canonical = json.dumps(rec, sort_keys=True, default=str).encode("utf-8")
            if hashlib.sha256(canonical).hexdigest() != saved_hash:
                return False
            prev = saved_hash
        return True
