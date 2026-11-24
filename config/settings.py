"""Central configuration for AgriChain Agentic AI Ecosystem."""
from pathlib import Path
from typing import Dict
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RESULTS_DIR = ROOT_DIR / "results"
ARTIFACTS_DIR = RESULTS_DIR / "models"


class ModelProfile(BaseModel):
    agent_id: str
    agent_name: str
    enterprise: str
    domain_model: str
    llm_model: str
    provider: str
    deployment: str  # "on-premise-ml", "edge-ml", or "cloud-api"
    uses_llm: bool = True
    temperature: float
    input_cost_per_1m_usd: float
    output_cost_per_1m_usd: float
    base_latency_ms: float
    ms_per_output_token: float


# Hybrid Selective-LLM Routing Registry (3 Cognitive LLM Agents + 3 Deterministic ML/Symbolic Agents)
# LLM applied ONLY where open-ended negotiation, multimodal synthesis, or cross-enterprise orchestration is required:
#   - AGT-02 Koperasi Tani (Claude 3.5 Sonnet)
#   - AGT-03 FreshFood Processing (Gemini 2.5 Flash Multimodal)
#   - AGT-06 Global Orchestrator (GPT-4o)
# Non-LLM Deterministic ML/Optimization Agents (0 LLM tokens, ultra-low latency, zero hallucination risk):
#   - AGT-01 AgroFarm (Random Forest 250 Trees + NDVI + 80% PI + 14d +/- 2sigma Rule Engine)
#   - AGT-04 ColdChain Logistics (Isolation Forest 7-12C + XGBoost ETA + Google OR-Tools VRPTW)
#   - AGT-05 SuperMart (XGBoost 7-Day + Newsvendor PO + Deterministic Policy/SLA Rules)
AGENT_MODEL_PROFILES: Dict[str, ModelProfile] = {
    "AGT-01": ModelProfile(
        agent_id="AGT-01",
        agent_name="AgroFarm Yield & Harvest Agent",
        enterprise="AgroFarm",
        domain_model="Random Forest 250 Trees + NDVI + 80% PI + 14d ± 2σ Rules",
        llm_model="None (Deterministic ML + Rules)",
        provider="deterministic",
        deployment="on-premise-ml",
        uses_llm=False,
        temperature=0.0,
        input_cost_per_1m_usd=0.0,
        output_cost_per_1m_usd=0.0,
        base_latency_ms=8.5,
        ms_per_output_token=0.0,
    ),
    "AGT-02": ModelProfile(
        agent_id="AGT-02",
        agent_name="Koperasi Aggregation & Negotiation Agent",
        enterprise="Koperasi Tani",
        domain_model="LightGBM Regressor + Contract Net Auction",
        llm_model="Claude 3.5 Sonnet",
        provider="anthropic",
        deployment="cloud-api",
        uses_llm=True,
        temperature=0.3,
        input_cost_per_1m_usd=3.00,
        output_cost_per_1m_usd=15.00,
        base_latency_ms=620.0,
        ms_per_output_token=4.2,
    ),
    "AGT-03": ModelProfile(
        agent_id="AGT-03",
        agent_name="FreshFood Quality & Production Agent",
        enterprise="FreshFood Processing",
        domain_model="2D-Conv CNN + Food Safety Hard-Block + FEFO Scheduler",
        llm_model="Gemini 2.5 Flash (Multimodal)",
        provider="gemini",
        deployment="cloud-api",
        uses_llm=True,
        temperature=0.1,
        input_cost_per_1m_usd=0.15,
        output_cost_per_1m_usd=0.60,
        base_latency_ms=340.0,
        ms_per_output_token=2.0,
    ),
    "AGT-04": ModelProfile(
        agent_id="AGT-04",
        agent_name="ColdChain Logistics & Monitoring Agent",
        enterprise="ColdChain Logistics",
        domain_model="Isolation Forest (7–12°C) + XGBoost ETA + OR-Tools VRPTW",
        llm_model="None (Deterministic ML + OR-Tools)",
        provider="deterministic",
        deployment="edge-ml",
        uses_llm=False,
        temperature=0.0,
        input_cost_per_1m_usd=0.0,
        output_cost_per_1m_usd=0.0,
        base_latency_ms=14.0,
        ms_per_output_token=0.0,
    ),
    "AGT-05": ModelProfile(
        agent_id="AGT-05",
        agent_name="SuperMart Demand & Procurement Agent",
        enterprise="SuperMart",
        domain_model="XGBoost 7-Day + Newsvendor PO + Deterministic SLA Rules",
        llm_model="None (Deterministic ML + Rules)",
        provider="deterministic",
        deployment="on-premise-ml",
        uses_llm=False,
        temperature=0.0,
        input_cost_per_1m_usd=0.0,
        output_cost_per_1m_usd=0.0,
        base_latency_ms=11.0,
        ms_per_output_token=0.0,
    ),
    "AGT-06": ModelProfile(
        agent_id="AGT-06",
        agent_name="Global Orchestrator & Replanning Agent",
        enterprise="Global Control Center",
        domain_model="MILP Solver (PuLP/CBC) + FEFO Spoilage Penalty",
        llm_model="GPT-4o",
        provider="openai",
        deployment="cloud-api",
        uses_llm=True,
        temperature=0.1,
        input_cost_per_1m_usd=2.50,
        output_cost_per_1m_usd=10.00,
        base_latency_ms=540.0,
        ms_per_output_token=3.8,
    ),
}

# Frontier baseline profile used for All-LLM Homogeneous Ablation (all 6 agents forced onto GPT-4o)
HOMOGENEOUS_FRONTIER_PROFILE = ModelProfile(
    agent_id="HOMO",
    agent_name="Homogeneous Frontier Agent",
    enterprise="All",
    domain_model="Per-Agent ML",
    llm_model="GPT-4o (All-LLM Homogeneous)",
    provider="openai",
    deployment="cloud-api",
    uses_llm=True,
    temperature=0.1,
    input_cost_per_1m_usd=2.50,
    output_cost_per_1m_usd=10.00,
    base_latency_ms=540.0,
    ms_per_output_token=3.8,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_execution_mode: str = "SIMULATED"
    ollama_base_url: str = "http://localhost:11434/v1"

    # Free-Tier External LLM Providers (0 USD, No Credit Card Required)
    groq_api_key: str = ""
    gemini_api_key: str = ""
    openrouter_api_key: str = ""

    # Configurable Free-Tier Model IDs (3 Heterogeneous Models for AGT-02, AGT-03, AGT-06)
    groq_model_koperasi: str = "openai/gpt-oss-20b"
    gemini_model_freshfood: str = "gemini-3.5-flash-lite"
    groq_model_global: str = "openai/gpt-oss-120b"
    openrouter_model_fallback: str = "meta-llama/llama-3.3-70b-instruct:free"

    # Optional Paid Cloud Providers (if user chooses paid frontier models)
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    mistral_api_key: str = ""

    # NIST AI RMF 1.0 HITL Escalation Thresholds (Tabel 7.2)
    hitl_max_flr_pct: float = 10.0
    hitl_capacity_drop_pct: float = 40.0
    hitl_cost_surge_pct: float = 15.0
    max_negotiation_rounds: int = 3
    random_seed: int = 42

    # Standardized Biological & Operational Constants (Pillar 1 Harmonization)
    tomato_safe_temp_min_c: float = 7.0
    tomato_safe_temp_max_c: float = 12.0
    agrofarm_sensor_outage_days_threshold: int = 3
    agrofarm_rain_extreme_14d_mm: float = 90.0
    agrofarm_deviation_sigma: float = 2.0
    data_stale_threshold_minutes: int = 15
    api_base_url: str = "http://127.0.0.1:8000"


settings = Settings()
