"""Quick 1-Command Verifier for 100% FREE External LLM APIs (Groq + Google Gemini + OpenRouter).

Usage:
    python src/llm/test_free_llms.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import settings
from src.llm.router import HeterogeneousLLMRouter


def main() -> None:
    print("=" * 74)
    print("AgriChain v2.2 — Free External 3-LLM API Connection Tester")
    print("=" * 74)
    print(f"LLM_EXECUTION_MODE : {settings.llm_execution_mode}")
    print(f"GROQ_API_KEY       : {'SET ✅' if settings.groq_api_key else 'KOSONG ❌ (Daftar gratis: https://console.groq.com/keys)'}")
    print(f"GEMINI_API_KEY     : {'SET ✅' if settings.gemini_api_key else 'KOSONG ❌ (Daftar gratis: https://aistudio.google.com/apikey)'}")
    print(f"OPENROUTER_API_KEY : {'SET ✅' if settings.openrouter_api_key else 'OPSIONAL (https://openrouter.ai/keys)'}")
    print("-" * 74)

    if settings.llm_execution_mode.upper() != "LIVE":
        print("⚠️  Saat ini .env masih mode SIMULATED.")
        print("    Ubah LLM_EXECUTION_MODE=LIVE di file .env lalu isi GROQ_API_KEY / GEMINI_API_KEY.")
        return

    router = HeterogeneousLLMRouter(homogeneous_frontier=False)
    checks = [
        ("AGT-02", "Koperasi Tani", "verify_negotiation_ping", {"lot_id": "H002", "offer_rp": 6800}),
        ("AGT-03", "FreshFood Processing", "verify_qc_ping", {"lot_id": "H003", "ph": 4.35, "defect_ratio": 0.12}),
        ("AGT-06", "Global Orchestrator", "verify_orchestration_ping", {"scenario": "COLD_STORAGE_FAILURE", "flr_pct": 0.0}),
    ]
    for aid, name, task, ctx in checks:
        out = router.invoke_structured(
            agent_id=aid,
            task_label=task,
            context_payload=ctx,
            policy_resolver=lambda c: {"status": "OK", "llm_rationale": "Simulated fallback"},
        )
        rec = router.call_log[-1]
        icon = "✅ LIVE_API" if rec.mode == "LIVE_API" else f"⚠️ {rec.mode}"
        print(f"[{aid} {name:20s}] {icon:14s} | Model: {rec.llm_model:30s} | Latency: {rec.actual_compute_ms:7.1f} ms | Cost: ${rec.cost_usd:.4f}")
        if out.get("llm_rationale"):
            print(f"    -> Rationale: {str(out['llm_rationale'])[:110]}")
    print("=" * 74)


if __name__ == "__main__":
    main()
