# 🍅 agrichain-agentic-ai

**Smart Agriculture & Food Supply Chain — *Heterogeneous Multi-Enterprise Agentic AI Ecosystem* untuk Optimasi Produksi Pertanian, Distribusi Pangan, Negosiasi Lintas Perusahaan, dan *Adaptive Replanning***

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph%20StateGraph-1F4E79)
![Optimization](https://img.shields.io/badge/Optimization-PuLP%20MILP--FEFO%20%2B%20OR--Tools%20CVRP-2B6CB0)
![Tests](https://img.shields.io/badge/Pytest-6%2F6%20Passed-2E7D32)
![Standards](https://img.shields.io/badge/Standards-A2A%20%7C%20FIPA--ACL%20%7C%20GS1%20EPCIS%202.0%20%7C%20NIST%20AI%20RMF%201.0-0F766E)

> **Proyek Magister Ilmu Komputer (S2 — Konsentrasi Kecerdasan Artifisial)**  
> **Mata Kuliah:** *AI Agentic Technology Systems for Digital Enterprise Ecosystem*  
> **Laporan Lengkap (Bab 1–11, 45 Halaman):** [`Laporan_Bab1_11_Smart_Agriculture_Agentic_AI.pdf`](./Laporan_Bab1_11_Smart_Agriculture_Agentic_AI.pdf) · [`DOCX`](./Laporan_Bab1_11_Smart_Agriculture_Agentic_AI.docx) · [`Markdown`](./Laporan_Bab1_11_Smart_Agriculture_Agentic_AI.md)

---

## Ringkasan Proyek

`agrichain-agentic-ai` adalah implementasi lengkap ekosistem **Multi-Enterprise Agentic AI** untuk rantai pasok pangan mudah rusak (*perishable agri-food supply chain*, studi kasus komoditas **tomat** Grade A, B, C) yang mengoordinasikan **5 perusahaan independen** melalui **Global Agentic Control Center** dengan prinsip **Zero-Direct-DB-Access (*Data Sovereignty*)**.

Berbeda dari arsitektur agen tunggal (*single-agent*) maupun *homogeneous LLM*, sistem ini menerapkan **heterogenitas model ganda**:
1. **6 Model Domain ML / Optimasi Berbeda** yang dilatih pada dataset dummy terisolasi lintas 5 perusahaan (**19.575 rekaman terstruktur + 3.000 citra RGB tomat**).
2. **6 Keluarga LLM Berbeda** yang dirutekan sesuai kebutuhan modalitas, latensi *edge*, privasi *on-premise*, dan kedalaman penalaran negosiasi/orkestrasi.
3. **Orkestrator *Neuro-Symbolic*** berbasis **LangGraph `StateGraph`** + **PuLP MILP-FEFO** + negosiasi terbatas *Contract Net Protocol* (maksimal 3 putaran) + gerbang **Human-in-the-Loop (HITL)** berbasis **NIST AI RMF 1.0** + **SHA-256 Hash-Chained Audit Trail**.

---

## Arsitektur 6 Agen Otonom (Heterogenitas Model Ganda)

| ID Agen | Enterprise / Layer | Model Domain AI / Optimasi | Model LLM Backbone | Basis Data Lokal |
| :--- | :--- | :--- | :--- | :--- |
| `AGT-01` | **AgroFarm** | Random Forest Regression | **Qwen 2.5 14B Instruct** *(On-Premise)* | PostgreSQL |
| `AGT-02` | **Koperasi Tani** | LightGBM + Contract Net Auction | **Claude 3.5 Sonnet** | MySQL |
| `AGT-03` | **FreshFood Processing** | 2D-Conv Visual CNN + Food Safety Hard-Block + FEFO | **Gemini 2.5 Flash** *(Multimodal VLM)* | MongoDB |
| `AGT-04` | **ColdChain Logistics** | Isolation Forest + Google OR-Tools CVRP | **Llama 3.1 8B Instruct** *(Edge)* | TimescaleDB |
| `AGT-05` | **SuperMart** | XGBoost Regression + Newsvendor Safety-Stock | **Mistral Small 3 (24B)** | MySQL |
| `AGT-06` | **Global Control Center** | MILP-FEFO Solver (PuLP / CBC) | **GPT-4o** *(LangGraph Orchestrator)* | Redis + Hash-Chained Audit Log |

---

## Hasil Evaluasi Empiris (Aktual dari Eksekusi Kode)

Seluruh angka di bawah ini direkam langsung dari eksekusi [`src/models/train_all.py`](./src/models/train_all.py) (`results/ml_metrics.json`) dan [`src/experiments/run_experiments.py`](./src/experiments/run_experiments.py) (`results/experiment_results.json`, `seed = 42`, 30 siklus berpasangan per kondisi).

### 1. Kinerja 5 Model AI Domain Lokal & Optimasi
| Agen & Enterprise | Model | Hasil Uji Aktual | Target KPI | Status |
| :--- | :--- | :--- | :--- | :---: |
| `AGT-01` AgroFarm | Random Forest Regression | MAE **93,09 kg (7,24% mean)**, RMSE 120,14 kg, R² **0,9393** | MAE ≤ 10% | Lulus |
| `AGT-02` Koperasi Tani | LightGBM Regressor | MAE **Rp240,1/kg**, MAPE **4,28%**, R² **0,9853** | MAPE ≤ 8% | Lulus |
| `AGT-03` FreshFood | 2D-Conv Spatial-Spectral CNN | Accuracy **98,67%**, Macro-F1 **0,9878**, Reject Recall **100,0%** | Acc ≥ 90% | Lulus |
| `AGT-04` ColdChain | Isolation Forest + OR-Tools CVRP | Anomaly F1 **95,32%** (Recall **100,0%**, AUC **1,0000**); CVRP 382 → 263 km (**-31,15%**) | F1 ≥ 90%, Rute ≥ 10% | Lulus |
| `AGT-05` SuperMart | XGBoost Regression | MAE **26,71 kg**, MAPE **3,72%**, R² **0,9215** | MAPE ≤ 15% | Lulus |
| `AGT-06` Control Center | PuLP CBC MILP-FEFO | Normal & Disrupt Adaptive: FLR **0,0%**, OFR **100,0%**, solve **29,21 ms** | FLR ≤ 5%, OFR ≥ 95% | Lulus |

### 2. Perbandingan 4 Kondisi Eksperimen (30 Siklus Berpasangan)
| Global KPI | Kondisi 0: Siloed Baseline | Kondisi 1: Normal Agentic | Kondisi 2: Disrupt Tanpa Replan | Kondisi 3: Disrupt + Adaptive Replan | Dampak Adaptive (K3 vs K2) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Food Loss Rate (FLR, %)** | 13,38 ± 2,63 | **0,00 ± 0,00** | 15,47 ± 2,44 | **0,00 ± 0,00** | **-15,47 poin %** |
| **Order Fulfillment Rate (OFR, %)** | 98,72 ± 2,11 | 98,72 ± 2,11 | 92,92 ± 7,24 | **98,25 ± 2,79** | **+5,33 poin %** |
| **Total Supply Chain Cost (Rp Juta)** | 29,58 ± 1,25 | 29,52 ± 1,51 | 31,36 ± 1,78 | **29,06 ± 1,72** | **-Rp2,31 Jt (-7,35%)** |
| **Net Ecosystem Profit (Rp Juta)** | 21,74 ± 1,01 | **27,38 ± 1,16** | 20,21 ± 1,64 | **28,16 ± 1,51** | **+Rp7,94 Jt (+39,3%)** |
| **Jain's Fairness Index** | 0,9367 | **0,9607** | 0,8286 | **0,9332** | **+0,1046 (+12,6%)** |
| **Replanning Time (dtk)** | — | 2,24 ± 0,06 | — | **4,23 ± 0,09** | **< 5 detik** |
| **Privacy Leaks (Field Privat)** | 0 | **0** | 0 | **0** | **Zero Leak** |

![Perbandingan Kinerja Ekosistem pada 4 Kondisi Eksperimen](./results/figures/fig_9_1_conditions.png)

### 3. Hasil Tiga Studi Ablasi & Efisiensi Biaya/Latensi
- **Ablasi 1 (*Multi-Agent 6 Agen* vs *Single-Agent Monolitik*):** Menjaga **0 kebocoran data privat** (vs **15 field privat terekspos**) dan menaikkan *Jain's Fairness Index* dari **0,8355 → 0,9332**.
- **Ablasi 2 (*Heterogeneous 6-LLM* vs *Homogeneous 6× GPT-4o*):** Mempertahankan kualitas keputusan identik sembari **menghemat biaya token 41,71%** (`USD 17,50` → `USD 10,20` per 1.000 siklus) dan **menurunkan latensi *replanning* 10,19%** (`4,71 s` → `4,23 s`; latensi *edge alert* ColdChain turun **-78,2%** menjadi `181,02 ms`).
- **Ablasi 3 (*Neuro-Symbolic MILP-FEFO + LLM* vs *Pure LLM*):** Menurunkan pelanggaran kendala dari **100,0% (1,70 pelanggaran/siklus) → 0,0%** dan menekan FLR dari **1,52% → 0,00%**.
- **3 Skenario Analisis Kegagalan (NIST AI RMF 1.0):** *Food Safety Hard-Block* (`H003` dialokasikan **0 kg**, HITL aktif), *3-Round Negotiation Deadlock* (berhenti deterministik di ronde ke-3, **0 privacy leak**, HITL aktif), dan *Compound Disruption* (FLR **0,00%**, substitusi Grade B `800 kg` ≤ batas 30%, HITL aktif) dengan **SHA-256 audit chain terverifikasi 100%**.

![Hasil Tiga Studi Ablasi Arsitektur Multi-Agent](./results/figures/fig_9_2_ablation_comparison.png)

![Analisis Biaya Token dan Latensi per Agen](./results/figures/fig_9_3_agent_cost_latency.png)

---

## Struktur Repositori

```text
agrichain-agentic-ai/
├── config/
│   └── settings.py                      # Registri 6 profil LLM heterogen & ambang HITL NIST AI RMF
├── src/
│   ├── data/
│   │   ├── generate_dummy_data.py       # Generator 19.575 rekaman dummy + 3.000 citra RGB tomat
│   │   └── db_adapter.py                # Materialisasi 5 basis data lokal terisolasi
│   ├── protocols/
│   │   ├── fipa_epcis.py                # Skema A2A, FIPA-ACL performatives, GS1 EPCIS 2.0, AgentCard
│   │   └── security.py                  # Data Sovereignty Firewall, Scoped Tokens, Hash-Chained Audit Trail
│   ├── models/
│   │   ├── agrofarm_rf.py               # AGT-01: Random Forest Regression
│   │   ├── koperasi_lgbm.py             # AGT-02: LightGBM Regressor + Contract Net Auction
│   │   ├── freshfood_cnn.py             # AGT-03: 2D-Conv Visual CNN + Food Safety Hard-Block + FEFO
│   │   ├── coldchain_iforest_cvrp.py    # AGT-04: Isolation Forest + Google OR-Tools CVRP
│   │   ├── supermart_xgb.py             # AGT-05: XGBoost Demand Forecasting + Newsvendor PO
│   │   ├── milp_fefo.py                 # AGT-06: PuLP CBC MILP-FEFO Global Allocation Solver
│   │   └── train_all.py                 # Orkestrasi generasi data, pelatihan 5 ML, & verifikasi MILP
│   ├── llm/
│   │   ├── prompts.py                   # 6 System Prompts terstruktur
│   │   └── router.py                    # Dual-Mode (LIVE / Policy-Grounded Simulated) 6-LLM Router
│   ├── agents/
│   │   ├── base.py                      # BaseEnterpriseAgent + Outbound Privacy Sanitizer
│   │   ├── enterprise_agents.py         # 5 Autonomous Enterprise Agents (AGT-01 s.d. AGT-05)
│   │   └── orchestrator.py              # LangGraph StateGraph Global Orchestrator (AGT-06)
│   ├── api/
│   │   └── main.py                      # FastAPI Gateway (/.well-known/agent.json, /run-cycle, /hitl)
│   ├── experiments/
│   │   └── run_experiments.py           # Benchmark 4 Kondisi x 30 siklus + 3 Ablasi + 3 Failure Cases
│   └── dashboard/
│       └── app.py                       # Streamlit Control Center (Sankey, Disruption Injector, HITL)
├── tests/
│   └── test_ecosystem.py                # 6 Unit & FastAPI Integration Tests (pytest)
├── data/                                # Dataset dummy tergenerasi & 5 database lokal terisolasi
├── results/                             # Artefak model (.pkl), metrik JSON, audit_trail.jsonl, & 3 grafik 300-DPI
├── docker-compose.yml                   # Stack PostgreSQL 16, MySQL 8, MongoDB 7, TimescaleDB, Redis 7
├── .env.example                         # Template kredensial API LLM (mode LIVE) & parameter sistem
├── requirements.txt                     # Dependensi Python
├── Laporan_Bab1_11_Smart_Agriculture_Agentic_AI.{md,docx,pdf}  # Laporan Lengkap (Bab 1–11, 45 halaman)
└── Laporan_Bab1_7_Smart_Agriculture_Agentic_AI.{md,docx,pdf}   # Laporan Rancangan Awal (Bab 1–7, 35 halaman)
```

---

## Cara Menjalankan

```bash
# 1. Klon repositori & instal dependensi
git clone https://github.com/fransalwan/agrichain-agentic-ai.git
cd agrichain-agentic-ai
pip install -r requirements.txt

# 2. (Opsional) Konfigurasi API Key LLM (OpenAI/Anthropic/Gemini/Mistral/Ollama) untuk mode LIVE
cp .env.example .env

# 3. Bangkitkan dataset dummy (19.575 rekaman + 3.000 citra RGB) & latih seluruh 5 model ML + MILP/CVRP
python src/models/train_all.py

# 4. Jalankan benchmark eksperimen lengkap (4 kondisi x 30 siklus + 3 ablasi + 3 failure cases + grafik)
python src/experiments/run_experiments.py

# 5. Jalankan pengujian otomatis (unit + FastAPI integration tests)
pytest tests/test_ecosystem.py -v

# 6. Jalankan FastAPI Gateway (http://127.0.0.1:8000/docs)
uvicorn src.api.main:app --reload --port 8000

# 7. Jalankan Streamlit Global Control Center Dashboard (http://127.0.0.1:8501)
streamlit run src/dashboard/app.py
```

### *Endpoint* Utama FastAPI Gateway (`src/api/main.py`)
| Method | Endpoint | Fungsi |
| :---: | :--- | :--- |
| `GET` | `/api/v1/health` | Status layanan, jumlah agen aktif, dan integritas *audit chain* |
| `GET` | `/.well-known/agent.json` | A2A *Agent Discovery Cards* seluruh 6 agen otonom |
| `POST` | `/api/v1/orchestrator/run-cycle` | Menjalankan 1 siklus penuh LangGraph Orchestrator (Normal / *Cold Storage Failure* / *Demand Surge* / *Compound* / *Food Safety Block* / *Deadlock*) |
| `POST` | `/api/v1/orchestrator/hitl/{cycle_id}/approve` | Persetujuan/penolakan operator manusia (HITL) yang dicatat ke *hash-chained audit log* |

### Infrastruktur Basis Data Heterogen (Opsional via Docker)
```bash
docker compose up -d
```
Menjalankan 5 layanan basis data heterogen terisolasi (`agrofarm_postgres`, `koperasi_mysql`, `freshfood_mongodb`, `coldchain_timescaledb`, `supermart_mysql`) serta `global_redis`.

---

## Dokumen Laporan

- **Laporan Lengkap (Bab 1–11 + Daftar Pustaka — 45 Halaman):**
  - [Laporan_Bab1_11_Smart_Agriculture_Agentic_AI.pdf](./Laporan_Bab1_11_Smart_Agriculture_Agentic_AI.pdf)
  - [Laporan_Bab1_11_Smart_Agriculture_Agentic_AI.docx](./Laporan_Bab1_11_Smart_Agriculture_Agentic_AI.docx)
  - [Laporan_Bab1_11_Smart_Agriculture_Agentic_AI.md](./Laporan_Bab1_11_Smart_Agriculture_Agentic_AI.md)
- **Laporan Rancangan Awal (Bab 1–7 — 35 Halaman):**
  - [Laporan_Bab1_7_Smart_Agriculture_Agentic_AI.pdf](./Laporan_Bab1_7_Smart_Agriculture_Agentic_AI.pdf)
  - [Laporan_Bab1_7_Smart_Agriculture_Agentic_AI.docx](./Laporan_Bab1_7_Smart_Agriculture_Agentic_AI.docx)
  - [Laporan_Bab1_7_Smart_Agriculture_Agentic_AI.md](./Laporan_Bab1_7_Smart_Agriculture_Agentic_AI.md)
