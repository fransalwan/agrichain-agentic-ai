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
    deployment: str  # "on-premise" or "cloud-api"
    temperature: float
    input_cost_per_1m_usd: float
    output_cost_per_1m_usd: float
    base_latency_ms: float
    ms_per_output_token: float


# Heterogeneous 6-Agent Model Routing Registry (Bab 6.1)
AGENT_MODEL_PROFILES: Dict[str, ModelProfile] = {
    "AGT-01": ModelProfile(
        agent_id="AGT-01",
        agent_name="AgroFarm Yield & Harvest Agent",
        enterprise="AgroFarm",
        domain_model="Random Forest Regression",
        llm_model="Qwen 2.5 14B Instruct",
        provider="ollama",
        deployment="on-premise",
        temperature=0.1,
        input_cost_per_1m_usd=0.05,   # Amortized local GPU/compute cost
        output_cost_per_1m_usd=0.10,
        base_latency_ms=180.0,
        ms_per_output_token=1.8,
    ),
    "AGT-02": ModelProfile(
        agent_id="AGT-02",
        agent_name="Koperasi Aggregation & Negotiation Agent",
        enterprise="Koperasi Tani",
        domain_model="LightGBM Regressor + Contract Net Auction",
        llm_model="Claude 3.5 Sonnet",
        provider="anthropic",
        deployment="cloud-api",
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
        domain_model="CNN MobileNetV2-Feature Classifier + FEFO Scheduler",
        llm_model="Gemini 2.5 Flash (Multimodal)",
        provider="gemini",
        deployment="cloud-api",
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
        domain_model="Isolation Forest + Google OR-Tools CVRP",
        llm_model="Llama 3.1 8B Instruct",
        provider="ollama",
        deployment="on-premise",
        temperature=0.1,
        input_cost_per_1m_usd=0.02,   # Ultra-low edge compute cost
        output_cost_per_1m_usd=0.05,
        base_latency_ms=95.0,
        ms_per_output_token=1.1,
    ),
    "AGT-05": ModelProfile(
        agent_id="AGT-05",
        agent_name="SuperMart Demand & Procurement Agent",
        enterprise="SuperMart",
        domain_model="XGBoost Regression + Newsvendor Safety-Stock",
        llm_model="Mistral Small 3 (24B)",
        provider="mistral",
        deployment="cloud-api",
        temperature=0.1,
        input_cost_per_1m_usd=0.10,
        output_cost_per_1m_usd=0.30,
        base_latency_ms=260.0,
        ms_per_output_token=1.9,
    ),
    "AGT-06": ModelProfile(
        agent_id="AGT-06",
        agent_name="Global Orchestrator & Replanning Agent",
        enterprise="Global Control Center",
        domain_model="MILP Solver (PuLP/CBC) + FEFO Spoilage Penalty",
        llm_model="GPT-4o",
        provider="openai",
        deployment="cloud-api",
        temperature=0.1,
        input_cost_per_1m_usd=2.50,
        output_cost_per_1m_usd=10.00,
        base_latency_ms=540.0,
        ms_per_output_token=3.8,
    ),
}

# Frontier baseline profile used for Homogeneous Ablation (all 6 agents use GPT-4o)
HOMOGENEOUS_FRONTIER_PROFILE = ModelProfile(
    agent_id="HOMO",
    agent_name="Homogeneous Frontier Agent",
    enterprise="All",
    domain_model="Per-Agent ML",
    llm_model="GPT-4o (Homogeneous)",
    provider="openai",
    deployment="cloud-api",
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
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    mistral_api_key: str = ""

    # NIST AI RMF 1.0 HITL Escalation Thresholds (Tabel 7.2)
    hitl_max_flr_pct: float = 10.0
    hitl_capacity_drop_pct: float = 40.0
    hitl_cost_surge_pct: float = 15.0
    max_negotiation_rounds: int = 3
    random_seed: int = 42


settings = Settings()
