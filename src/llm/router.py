"""LiteLLM-Compatible Heterogeneous 6-LLM Router with Token, Cost, and Latency Telemetry.

Supports dual execution:
- LIVE mode: invokes real cloud/Ollama API endpoints when keys/endpoints are configured.
- SIMULATED mode (default offline benchmark): executes deterministic policy-grounded
  structured reasoning with calibrated per-model token accounting & latency profiles.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import httpx
import numpy as np

from config.settings import AGENT_MODEL_PROFILES, HOMOGENEOUS_FRONTIER_PROFILE, ModelProfile, settings
from src.llm.prompts import AGENT_SYSTEM_PROMPTS


@dataclass
class LLMCallRecord:
    agent_id: str
    llm_model: str
    provider: str
    deployment: str
    task_label: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    simulated_api_latency_ms: float
    actual_compute_ms: float
    mode: str


class HeterogeneousLLMRouter:
    def __init__(self, homogeneous_frontier: bool = False, seed: int = settings.random_seed):
        self.homogeneous_frontier = homogeneous_frontier
        self.mode = settings.llm_execution_mode.upper()
        self.rng = np.random.default_rng(seed)
        self.call_log: List[LLMCallRecord] = []

    def get_profile(self, agent_id: str) -> ModelProfile:
        if self.homogeneous_frontier:
            base = AGENT_MODEL_PROFILES[agent_id]
            return HOMOGENEOUS_FRONTIER_PROFILE.model_copy(
                update={"agent_id": agent_id, "agent_name": base.agent_name, "enterprise": base.enterprise}
            )
        return AGENT_MODEL_PROFILES[agent_id]

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        # Standard ~4 chars/token approximation for multilingual/JSON prompts
        return max(24, int(round(len(text) / 3.8)))

    def _try_live_provider_call(self, profile: ModelProfile, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Attempt a real LLM API completion across all 6 configured providers when LIVE mode & keys exist."""
        if self.mode != "LIVE":
            return None
        try:
            # 1. OpenAI (AGT-06: GPT-4o) or Local Ollama (AGT-01: Qwen 2.5, AGT-04: Llama 3.1)
            if profile.provider == "openai" and settings.openai_api_key:
                resp = httpx.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                    json={
                        "model": "gpt-4o",
                        "temperature": profile.temperature,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    },
                    timeout=15.0,
                )
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"]
            elif profile.provider == "ollama":
                model_name = "qwen2.5:14b" if "Qwen" in profile.llm_model else "llama3.1:8b"
                resp = httpx.post(
                    f"{settings.ollama_base_url.rstrip('/')}/chat/completions",
                    json={
                        "model": model_name,
                        "temperature": profile.temperature,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    },
                    timeout=12.0,
                )
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"]
            # 2. Anthropic (AGT-02: Claude 3.5 Sonnet)
            elif profile.provider == "anthropic" and settings.anthropic_api_key:
                resp = httpx.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": settings.anthropic_api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-3-5-sonnet-20241022",
                        "max_tokens": 512,
                        "temperature": profile.temperature,
                        "system": system_prompt + " Respond strictly in valid JSON.",
                        "messages": [{"role": "user", "content": user_prompt}],
                    },
                    timeout=15.0,
                )
                if resp.status_code == 200:
                    return resp.json()["content"][0]["text"]
            # 3. Google Gemini (AGT-03: Gemini 2.5 Flash)
            elif profile.provider == "gemini" and settings.gemini_api_key:
                resp = httpx.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={settings.gemini_api_key}",
                    json={
                        "systemInstruction": {"parts": [{"text": system_prompt}]},
                        "contents": [{"parts": [{"text": user_prompt}]}],
                        "generationConfig": {
                            "temperature": profile.temperature,
                            "responseMimeType": "application/json",
                        },
                    },
                    timeout=15.0,
                )
                if resp.status_code == 200:
                    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            # 4. Mistral AI (AGT-05: Mistral Small 3)
            elif profile.provider == "mistral" and settings.mistral_api_key:
                resp = httpx.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.mistral_api_key}"},
                    json={
                        "model": "mistral-small-latest",
                        "temperature": profile.temperature,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    },
                    timeout=15.0,
                )
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"]
        except Exception:
            return None
        return None

    def invoke_structured(
        self,
        agent_id: str,
        task_label: str,
        context_payload: Dict[str, Any],
        policy_resolver: Callable[[Dict[str, Any]], Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Invoke agent's assigned LLM model with structured JSON output and telemetry logging."""
        profile = self.get_profile(agent_id)
        sys_prompt = AGENT_SYSTEM_PROMPTS[agent_id]
        user_prompt = json.dumps({"task": task_label, "context": context_payload}, default=str)

        t0 = time.perf_counter()
        live_raw = self._try_live_provider_call(profile, sys_prompt, user_prompt)
        if live_raw is not None:
            try:
                result = json.loads(live_raw)
                exec_mode = "LIVE_API"
            except Exception:
                result = policy_resolver(context_payload)
                exec_mode = "POLICY_GROUNDED_FALLBACK"
        else:
            result = policy_resolver(context_payload)
            exec_mode = "POLICY_GROUNDED_SIMULATED"
        actual_ms = (time.perf_counter() - t0) * 1000.0

        out_str = json.dumps(result, default=str)
        in_toks = self._estimate_tokens(sys_prompt + user_prompt)
        out_toks = self._estimate_tokens(out_str)

        cost_usd = (in_toks / 1_000_000.0) * profile.input_cost_per_1m_usd + (
            out_toks / 1_000_000.0
        ) * profile.output_cost_per_1m_usd

        # Calibrated realistic API/Edge inference latency (base + token generation + small jitter)
        jitter = float(self.rng.normal(1.0, 0.06))
        sim_latency_ms = max(
            35.0,
            (profile.base_latency_ms + out_toks * profile.ms_per_output_token) * jitter,
        )

        self.call_log.append(
            LLMCallRecord(
                agent_id=agent_id,
                llm_model=profile.llm_model,
                provider=profile.provider,
                deployment=profile.deployment,
                task_label=task_label,
                input_tokens=in_toks,
                output_tokens=out_toks,
                cost_usd=cost_usd,
                simulated_api_latency_ms=round(sim_latency_ms, 2),
                actual_compute_ms=round(actual_ms, 3),
                mode=exec_mode,
            )
        )
        return result

    def summarize_telemetry(self) -> Dict[str, Any]:
        by_agent: Dict[str, Dict[str, Any]] = {}
        total_in = 0
        total_out = 0
        total_cost = 0.0
        total_lat_ms = 0.0
        for rec in self.call_log:
            total_in += rec.input_tokens
            total_out += rec.output_tokens
            total_cost += rec.cost_usd
            total_lat_ms += rec.simulated_api_latency_ms
            if rec.agent_id not in by_agent:
                by_agent[rec.agent_id] = {
                    "llm_model": rec.llm_model,
                    "deployment": rec.deployment,
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                    "total_latency_ms": 0.0,
                }
            b = by_agent[rec.agent_id]
            b["calls"] += 1
            b["input_tokens"] += rec.input_tokens
            b["output_tokens"] += rec.output_tokens
            b["cost_usd"] += rec.cost_usd
            b["total_latency_ms"] += rec.simulated_api_latency_ms

        for b in by_agent.values():
            b["cost_usd"] = round(b["cost_usd"], 6)
            b["avg_latency_ms"] = round(b["total_latency_ms"] / max(b["calls"], 1), 2)
            b["total_latency_ms"] = round(b["total_latency_ms"], 2)

        return {
            "routing_mode": "HOMOGENEOUS_GPT4O" if self.homogeneous_frontier else "HETEROGENEOUS_6_LLM",
            "total_calls": len(self.call_log),
            "total_input_tokens": total_in,
            "total_output_tokens": total_out,
            "total_cost_usd": round(total_cost, 6),
            "total_serial_latency_ms": round(total_lat_ms, 2),
            "by_agent": by_agent,
            "calls": [
                {
                    "agent_id": r.agent_id,
                    "llm_model": r.llm_model,
                    "provider": r.provider,
                    "deployment": r.deployment,
                    "task_label": r.task_label,
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "cost_usd": round(r.cost_usd, 6),
                    "latency_ms": r.simulated_api_latency_ms,
                    "mode": r.mode,
                }
                for r in self.call_log
            ],
        }

    def reset_log(self) -> None:
        self.call_log.clear()
