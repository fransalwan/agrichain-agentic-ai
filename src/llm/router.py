"""Hybrid Selective-LLM Router (3 Cognitive LLM Agents + 3 Deterministic ML/Rule Agents).

LLM Reasoning is strictly applied ONLY where open-ended negotiation, multimodal synthesis,
or cross-enterprise orchestration is required:
  - AGT-02 Koperasi Tani       -> Claude 3.5 Sonnet (Anthropic API)
  - AGT-03 FreshFood Processing -> Gemini 2.5 Flash Multimodal (Google Gemini API)
  - AGT-06 Global Control Center-> GPT-4o (OpenAI API)

Deterministic ML / Rule / Optimization Agents (0 LLM tokens, ~8-15 ms local execution):
  - AGT-01 AgroFarm            -> Random Forest + NDVI + 14-Day +/- 2sigma Rule Engine
  - AGT-04 ColdChain Logistics -> Isolation Forest (7-12C) + XGBoost ETA + OR-Tools VRPTW
  - AGT-05 SuperMart           -> XGBoost 7-Day + Newsvendor PO + Deterministic SLA Rules
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

    @staticmethod
    def _strip_json_fences(raw_text: str) -> str:
        txt = raw_text.strip()
        if txt.startswith("```"):
            lines = txt.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            txt = "\n".join(lines).strip()
        return txt

    def _call_openai_compat(
        self, url: str, api_key: str, model: str, system_prompt: str, user_prompt: str,
        temperature: float, extra_headers: Optional[Dict[str, str]] = None,
    ) -> Optional[tuple[str, Optional[Dict[str, int]]]]:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        if extra_headers:
            headers.update(extra_headers)
        resp = httpx.post(
            url,
            headers=headers,
            json={
                "model": model,
                "temperature": temperature,
                "max_tokens": 512,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system_prompt + " Respond strictly in valid JSON object."},
                    {"role": "user", "content": user_prompt},
                ],
            },
            timeout=18.0,
        )
        if resp.status_code == 200:
            body = resp.json()
            content = body["choices"][0]["message"]["content"]
            usage = body.get("usage")
            return content, usage
        return None

    def _call_gemini(
        self, api_key: str, model: str, system_prompt: str, user_prompt: str, temperature: float,
    ) -> Optional[tuple[str, Optional[Dict[str, int]]]]:
        resp = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
            json={
                "systemInstruction": {"parts": [{"text": system_prompt + " Respond strictly in valid JSON object."}]},
                "contents": [{"parts": [{"text": user_prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "responseMimeType": "application/json",
                },
            },
            timeout=18.0,
        )
        if resp.status_code == 200:
            body = resp.json()
            content = body["candidates"][0]["content"]["parts"][0]["text"]
            meta = body.get("usageMetadata", {})
            usage = {
                "prompt_tokens": int(meta.get("promptTokenCount", 0)),
                "completion_tokens": int(meta.get("candidatesTokenCount", 0)),
            } if meta else None
            return content, usage
        return None

    def _try_live_provider_call(
        self, profile: ModelProfile, system_prompt: str, user_prompt: str
    ) -> Optional[tuple[str, str, Optional[Dict[str, int]]]]:
        """Attempt a real external LLM API call ONLY for LLM-enabled agents (AGT-02, AGT-03, AGT-06).

        Supports 100% FREE-tier heterogeneous routing (Groq + Google Gemini + OpenRouter :free)
        as well as optional paid frontier APIs (OpenAI / Anthropic), with automatic cross-provider fallback.
        """
        if not profile.uses_llm or self.mode != "LIVE":
            return None

        aid = profile.agent_id
        # 1. Optional Paid Native Providers (if explicitly configured)
        try:
            if aid == "AGT-06" and settings.openai_api_key:
                res = self._call_openai_compat(
                    "https://api.openai.com/v1/chat/completions", settings.openai_api_key,
                    "gpt-4o", system_prompt, user_prompt, profile.temperature,
                )
                if res:
                    return res[0], "openai/gpt-4o", res[1]
            if aid == "AGT-02" and settings.anthropic_api_key:
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
                    timeout=18.0,
                )
                if resp.status_code == 200:
                    b = resp.json()
                    u = b.get("usage", {})
                    return (
                        b["content"][0]["text"],
                        "anthropic/claude-3-5-sonnet",
                        {"prompt_tokens": u.get("input_tokens", 0), "completion_tokens": u.get("output_tokens", 0)},
                    )
        except Exception:
            pass

        # 2. 100% FREE-TIER HETEROGENEOUS ROUTING (Groq Cloud + Google Gemini AI Studio + OpenRouter :free)
        #    - AGT-03 FreshFood -> Gemini Free Tier first, then Groq, then OpenRouter
        #    - AGT-02 Koperasi  -> Groq (Llama 3.3 70B / Qwen / GPT-OSS) first, then Gemini, then OpenRouter
        #    - AGT-06 Global    -> Groq (GPT-OSS 120B / Llama 3.3 70B) first, then Gemini, then OpenRouter
        groq_candidates = (
            list(dict.fromkeys([settings.groq_model_global, "openai/gpt-oss-120b", "llama-3.3-70b-versatile", "openai/gpt-oss-20b"]))
            if aid == "AGT-06"
            else list(dict.fromkeys([settings.groq_model_koperasi, "llama-3.3-70b-versatile", "openai/gpt-oss-20b", "llama-3.1-8b-instant"]))
        )
        gemini_candidates = list(dict.fromkeys([settings.gemini_model_freshfood, "gemini-2.5-flash", "gemini-2.5-flash-lite"]))

        provider_order = ("gemini", "groq", "openrouter") if aid == "AGT-03" else ("groq", "gemini", "openrouter")

        for prov in provider_order:
            if prov == "groq" and settings.groq_api_key:
                for model_id in groq_candidates:
                    try:
                        res = self._call_openai_compat(
                            "https://api.groq.com/openai/v1/chat/completions",
                            settings.groq_api_key, model_id, system_prompt, user_prompt, profile.temperature,
                        )
                        if res:
                            return res[0], f"groq/{model_id}", res[1]
                    except Exception:
                        continue
            elif prov == "gemini" and settings.gemini_api_key:
                for model_id in gemini_candidates:
                    try:
                        res = self._call_gemini(
                            settings.gemini_api_key, model_id, system_prompt, user_prompt, profile.temperature,
                        )
                        if res:
                            return res[0], f"gemini/{model_id}", res[1]
                    except Exception:
                        continue
            elif prov == "openrouter" and settings.openrouter_api_key:
                try:
                    res = self._call_openai_compat(
                        "https://openrouter.ai/api/v1/chat/completions",
                        settings.openrouter_api_key,
                        settings.openrouter_model_fallback,
                        system_prompt, user_prompt, profile.temperature,
                        extra_headers={"HTTP-Referer": "https://github.com/fransalwan/agrichain-agentic-ai", "X-Title": "AgriChain Agentic AI"},
                    )
                    if res:
                        return res[0], f"openrouter/{settings.openrouter_model_fallback}", res[1]
                except Exception:
                    continue
        return None

    def invoke_structured(
        self,
        agent_id: str,
        task_label: str,
        context_payload: Dict[str, Any],
        policy_resolver: Callable[[Dict[str, Any]], Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Execute agent's reasoning engine: Deterministic ML/Rules (0 tokens) for AGT-01/04/05,
        or LLM reasoning (Free Groq/Gemini/OpenRouter or Paid APIs) for AGT-02/03/06."""
        profile = self.get_profile(agent_id)
        t0 = time.perf_counter()

        # Non-LLM Deterministic ML / Optimization / Rule Engine path (0 LLM tokens, $0.00 cost)
        if not profile.uses_llm:
            result = policy_resolver(context_payload)
            actual_ms = (time.perf_counter() - t0) * 1000.0
            jitter = float(self.rng.normal(1.0, 0.05))
            det_latency_ms = max(4.0, profile.base_latency_ms * jitter)
            self.call_log.append(
                LLMCallRecord(
                    agent_id=agent_id,
                    llm_model=profile.llm_model,
                    provider=profile.provider,
                    deployment=profile.deployment,
                    task_label=task_label,
                    input_tokens=0,
                    output_tokens=0,
                    cost_usd=0.0,
                    simulated_api_latency_ms=round(det_latency_ms, 2),
                    actual_compute_ms=round(actual_ms, 3),
                    mode="DETERMINISTIC_ML_RULE",
                )
            )
            return result

        # Cognitive LLM path (AGT-02 Koperasi, AGT-03 FreshFood, AGT-06 Global, or All-LLM Ablation)
        sys_prompt = AGENT_SYSTEM_PROMPTS[agent_id]
        base_result = policy_resolver(context_payload)
        user_prompt = json.dumps(
            {
                "task": task_label,
                "context": context_payload,
                "required_json_keys": list(base_result.keys()) + ["llm_rationale"],
            },
            default=str,
        )

        live_out = self._try_live_provider_call(profile, sys_prompt, user_prompt)
        live_model_label = profile.llm_model
        live_provider = profile.provider
        real_usage: Optional[Dict[str, int]] = None

        if live_out is not None:
            live_raw, live_model_label, real_usage = live_out
            live_provider = live_model_label.split("/")[0]
            try:
                parsed = json.loads(self._strip_json_fences(live_raw))
                if isinstance(parsed, dict):
                    # Schema-safe merge: preserve deterministic safety/MILP invariants while incorporating live LLM reasoning
                    merged = dict(base_result)
                    for k, v in parsed.items():
                        if k in ("llm_rationale", "summary", "reasoning", "recommendation") and isinstance(v, str):
                            merged[k] = v
                    merged["llm_live_model"] = live_model_label
                    result = merged
                    exec_mode = "LIVE_API"
                else:
                    result = base_result
                    exec_mode = "POLICY_GROUNDED_FALLBACK"
            except Exception:
                result = base_result
                exec_mode = "POLICY_GROUNDED_FALLBACK"
        else:
            result = base_result
            exec_mode = "POLICY_GROUNDED_SIMULATED"
        actual_ms = (time.perf_counter() - t0) * 1000.0

        out_str = json.dumps(result, default=str)
        if real_usage and real_usage.get("prompt_tokens", 0) > 0:
            in_toks = int(real_usage["prompt_tokens"])
            out_toks = int(real_usage.get("completion_tokens", 0)) or self._estimate_tokens(out_str)
        else:
            in_toks = self._estimate_tokens(sys_prompt + user_prompt)
            out_toks = self._estimate_tokens(out_str)

        is_free_live = exec_mode == "LIVE_API" and live_provider in ("groq", "gemini", "openrouter")
        cost_usd = 0.0 if is_free_live else (
            (in_toks / 1_000_000.0) * profile.input_cost_per_1m_usd
            + (out_toks / 1_000_000.0) * profile.output_cost_per_1m_usd
        )

        # Use real network latency when LIVE_API succeeds; calibrated profile latency in SIMULATED benchmark
        if exec_mode == "LIVE_API":
            effective_latency_ms = actual_ms
        else:
            jitter = float(self.rng.normal(1.0, 0.06))
            effective_latency_ms = max(
                35.0,
                (profile.base_latency_ms + out_toks * profile.ms_per_output_token) * jitter,
            )

        self.call_log.append(
            LLMCallRecord(
                agent_id=agent_id,
                llm_model=live_model_label if exec_mode == "LIVE_API" else profile.llm_model,
                provider=live_provider,
                deployment="free-cloud-api" if is_free_live else profile.deployment,
                task_label=task_label,
                input_tokens=in_toks,
                output_tokens=out_toks,
                cost_usd=cost_usd,
                simulated_api_latency_ms=round(effective_latency_ms, 2),
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
            "routing_mode": "ALL_LLM_HOMOGENEOUS_GPT4O" if self.homogeneous_frontier else "SELECTIVE_3_LLM_HYBRID",
            "llm_agents_active": ["AGT-01", "AGT-02", "AGT-03", "AGT-04", "AGT-05", "AGT-06"] if self.homogeneous_frontier else ["AGT-02", "AGT-03", "AGT-06"],
            "deterministic_ml_agents": [] if self.homogeneous_frontier else ["AGT-01", "AGT-04", "AGT-05"],
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
