# 🍅 agrichain-agentic-ai (v2.1)

**Smart Agriculture & Food Supply Chain — *Heterogeneous Multi-Enterprise Agentic AI Ecosystem* untuk Optimasi Produksi Pertanian, Distribusi Pangan, Negosiasi Lintas Perusahaan, dan *Adaptive Replanning***

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph%20StateGraph-1F4E79)
![Optimization](https://img.shields.io/badge/Optimization-PuLP%20MILP--FEFO%20%2B%20OR--Tools%20VRPTW-2B6CB0)
![Tests](https://img.shields.io/badge/Pytest-13%2F13%20Passed-2E7D32)
![Standards](https://img.shields.io/badge/Standards-A2A%20%7C%20FIPA--ACL%20%7C%20GS1%20EPCIS%202.0%20%7C%20NIST%20AI%20RMF%201.0-0F766E)

> **Program Studi:** Magister Kecerdasan Artifisial  
> **Mata Kuliah:** Agent Enterprise  
> **Laporan Lengkap v2.1 (Bab 1–11, 54 Halaman):** [`Laporan_Bab1_11_Smart_Agriculture_Agentic_AI.pdf`](./Laporan_Bab1_11_Smart_Agriculture_Agentic_AI.pdf) · [`DOCX`](./Laporan_Bab1_11_Smart_Agriculture_Agentic_AI.docx) · [`Markdown`](./Laporan_Bab1_11_Smart_Agriculture_Agentic_AI.md)

---

## Tim Penyusun & Pembagian Tugas

| No | Nama Anggota | NIM | Enterprise / Lapis Tanggung Jawab |
| :---: | :--- | :---: | :--- |
| 1 | **M. Al lail Qadrillah** | `26/590736/PPA/07413` | **Koperasi Tani** (`AGT-02`) |
| 2 | **Dimas Prabowo** | `26/590092/PPA/07382` | **ColdChain Logistics** (`AGT-04`) |
| 3 | **Monanta Alfiareza** | `26/591492/PPA/07455` | **AgroFarm** (`AGT-01`) |
| 4 | **Frans Alwan Purba** | `25/563545/PPA/07116` | **FreshFood Processing** (`AGT-03`), **SuperMart** (`AGT-05`), & **Global Orchestration** (`AGT-06`) |

---

## Ringkasan Proyek & Peningkatan v2.1 (Full 5-Enterprise Parity)

`agrichain-agentic-ai` mengoordinasikan **5 perusahaan independen** (*AgroFarm, Koperasi Tani, FreshFood Processing, ColdChain Logistics, SuperMart*) melalui **Global Agentic Control Center** menggunakan **6 agen otonom** dengan **heterogenitas model ganda** (6 model domain ML/optimasi berbeda + 6 keluarga LLM berbeda) serta prinsip **Zero-Direct-DB-Access (*Data Sovereignty*)**.

### Peningkatan Utama Versi 2.0 → 2.1
1. **Pilar 1 — Arsitektur, Kontrak Data & *Server-Side RBAC*:** Standarisasi suhu aman tomat **`7,0–12,0°C`** lintas modul, pelacakan *canonical cross-enterprise lineage* (`block_id → lot_id → qc_doc_id → shipment_id → trip_id → vehicle_id → po_ref`), redaksi data privat di **server FastAPI** berbasis header `X-Scoped-Token`, serta rantai audit kriptografi **SHA-256** (*concurrency-safe*).
2. **Pilar 2 — Pendalaman AI Lokal (`AGT-01` AgroFarm v2 & `AGT-04` ColdChain v2):**
   - **AgroFarm v2 (`rf-v2.0`):** Random Forest 250 pohon + fitur **NDVI** + **80% Quantile Prediction Interval (`p10–p90`)** + *Feature Importance* + pembanding *baseline* (*Hist Mean* & *Linear Reg*) + *Crop Monitoring Deviation Engine* (**14 hari ± 2σ**) + *Sensor Outage Safety Fallback* (offline ≥ 3 hari → `FALLBACK_HISTORICAL_MEAN`) + skenario **`EXTREME_RAIN`** (jendela panen maju `-2 hari`).
   - **ColdChain v2 (`iforest-vrptw-v2.0`):** Google OR-Tools **VRPTW (*Time Windows*)** dengan 4 skenario (`NORMAL`, `ROAD_DISRUPTION`, `VEHICLE_BREAKDOWN`, `COLD_STORAGE_DROP`) & koordinat geospasial Yogyakarta/Sleman/Bantul + **XGBoost ETA Regressor** (`MAE 7,66 menit`) + deteksi anomali suhu **Isolation Forest** berbasis SOP `7–12°C`.
3. **Pilar 3 — *Decoupled FastAPI Multi-Enterprise Gateway v2.1 (Full 5-Enterprise Parity, 20 Endpoint)*:** Endpoint REST lokal lengkap untuk **seluruh 5 enterprise** — AgroFarm (`/monitoring`, `/predict`), Koperasi (`/price-forecast`), FreshFood (`/qc-inspect`, `/schedule`), ColdChain (`/fleet` & `/shipments` CRUD, `/vrptw`, `/eta`), SuperMart (`/forecast-7d`, `/po` CRUD, `/goods-receipt-sla`), *Server-Side Privacy Data Explorer*, serta LangGraph Orchestrator dengan *Closed-Loop Handshakes* (VRPTW *dynamic dock sync*, *QC Feedback → AgroFarm*, *7-Day Demand Horizon → Hulu*, *Flash-Promo Absorption*, & *Goods Receipt SLA*).
4. **Pilar 4 — *Role-Adaptive Enterprise Cockpit v2.1 (High-Contrast Light Mode)*:** UI terpisah via HTTP (`ApiBridge` + `X-Scoped-Token`), tema **Light Mode berkontras tinggi** (`.streamlit/config.toml` + WCAG AAA `#0F172A` di atas `#F8FAFC`/`#FFFFFF`), *dedicated workspace* untuk **seluruh 6 peran** (1 stakeholder utama per enterprise + 1 operator global), **5 UI State Wajib**, **Impact-Preview HITL Confirmation Console**, dan **Peta Geospasial VRPTW Interaktif**.

| ID Agen | Enterprise / Layer | Primary Stakeholder (1 per Enterprise) | Model Domain AI / Optimasi (v2.1) | Model LLM Backbone | Basis Data Lokal |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `AGT-01` | **AgroFarm** | **Farm Manager** | Random Forest 250 Trees + NDVI + 80% Quantile PI + 14d ± 2σ Monitor | **Qwen 2.5 14B Instruct** *(On-Premise)* | PostgreSQL (`agrofarm_pg.sqlite`) |
| `AGT-02` | **Koperasi Tani** | **Cooperative Manager** | LightGBM + Contract Net Auction | **Claude 3.5 Sonnet** | MySQL (`koperasi_mysql.sqlite`) |
| `AGT-03` | **FreshFood Processing** | **Quality Control & Production Manager** | 2D-Conv Visual CNN + Food Safety Hard-Block + FEFO | **Gemini 2.5 Flash** *(Multimodal VLM)* | MongoDB (`freshfood_tomato_qc.json` + RGB NPZ) |
| `AGT-04` | **ColdChain Logistics** | **Fleet & Cold Chain Manager** | Isolation Forest (7–12°C) + XGBoost ETA + OR-Tools VRPTW | **Llama 3.1 8B Instruct** *(Edge)* | TimescaleDB (`coldchain_timescaledb.sqlite`) |
| `AGT-05` | **SuperMart** | **Purchasing Manager** | XGBoost Regression + Newsvendor Safety-Stock | **Mistral Small 3 (24B)** | MySQL (`supermart_mysql.sqlite`) |
| `AGT-06` | **Global Control Center** | **Global Control Center Operator** | MILP-FEFO Solver (PuLP / CBC) + Cross-Enterprise Lineage | **GPT-4o** *(LangGraph Orchestrator)* | Redis + SHA-256 Audit Trail |

---

## Galeri Screenshot Aplikasi Aktual (v2.1 — High-Contrast Light Mode)

### 1. Global Command Center — Executive Briefing, Impact-Preview HITL Console, KPI Delta, Sankey & Decision Shift
![Global Control Center](./docs/screenshots/01_global_control_center.png)

### 2. LangGraph Decision Trace, Canonical Lineage (`block_id → po_ref`), FIPA-ACL Feed & SHA-256 Audit Trail
![Decision Trace, Lineage and Audit Trail](./docs/screenshots/02_decision_trace_audit.png)

### 3. Modul AgroFarm v2 (`AGT-01`) — Crop Monitoring 14d ± 2σ, 80% Quantile PI, Feature Importance & Live Predictor
![AgroFarm v2 NDVI and PI80](./docs/screenshots/03_agrofarm_v2_ndvi_pi80.png)

### 4. Modul ColdChain v2 (`AGT-04`) — Peta Geospasial OR-Tools VRPTW, Fleet/Shipments CRUD, XGBoost ETA & SOP 7–12°C
![ColdChain v2 VRPTW Map and Telemetry](./docs/screenshots/04_coldchain_anomaly_cvrp.png)

### 5. Modul FreshFood (`AGT-03`), Koperasi (`AGT-02`) & SuperMart (`AGT-05`) — Galeri Citra RGB CNN, Harga & Permintaan
![FreshFood Koperasi SuperMart](./docs/screenshots/05_freshfood_koperasi_supermart.png)

### 6. Server-Side Privacy Data Explorer (`🔒 REDACTED` via `X-Scoped-Token`) & Grafik Benchmark Bab 9
![Server-Side Data Explorer and Privacy Firewall](./docs/screenshots/06_data_explorer_privacy.png)

### 7. FastAPI Multi-Enterprise Gateway v2.1 — Swagger UI (20 Endpoint, `:8000/docs`)
![FastAPI Swagger Gateway v2.1](./docs/screenshots/07_fastapi_swagger_gateway.png)

---

## Hasil Evaluasi Empiris (Aktual dari Eksekusi Kode v2.0)

Seluruh angka terekam langsung dari [`src/models/train_all.py`](./src/models/train_all.py) (`results/ml_metrics.json`) dan [`src/experiments/run_experiments.py`](./src/experiments/run_experiments.py) (`results/experiment_results.json`, `seed = 42`, 30 siklus berpasangan per kondisi).

### 1. Kinerja 5 Model AI Domain Lokal & Optimasi (v2.0)
| Agen & Enterprise | Model | Hasil Uji Aktual (v2.0) | Target KPI | Status |
| :--- | :--- | :--- | :--- | :---: |
| `AGT-01` AgroFarm | Random Forest 250 Trees + NDVI + 80% PI | MAE **87,84 kg (6,83% mean)**, RMSE 114,47 kg, R² **0,9449**, PI80 Cov **91,67%** (unggul vs Hist Mean 421,47 kg & LinReg 125,00 kg) | MAE ≤ 10% | Lulus |
| `AGT-02` Koperasi Tani | LightGBM Regressor | MAE **Rp240,1/kg**, MAPE **4,28%**, R² **0,9853** | MAPE ≤ 8% | Lulus |
| `AGT-03` FreshFood | 2D-Conv Spatial-Spectral CNN | Accuracy **98,67%**, Macro-F1 **0,9878**, Reject Recall **100,0%** | Acc ≥ 90% | Lulus |
| `AGT-04` ColdChain | Isolation Forest (7–12°C) + XGBoost ETA + OR-Tools VRPTW | Anomaly F1 **95,32%** (Recall **100%**, AUC **1,0000**); ETA MAE **7,66 mnt** (MAPE **5,35%**); VRPTW 382 → 263 km (**-31,15%**, **0 TW violations**) | F1 ≥ 90%, Rute ≥ 10% | Lulus |
| `AGT-05` SuperMart | XGBoost Regression | MAE **26,71 kg**, MAPE **3,72%**, R² **0,9215** | MAPE ≤ 15% | Lulus |
| `AGT-06` Control Center | PuLP CBC MILP-FEFO | Normal & Disrupt Adaptive: FLR **0,0%**, OFR **100,0%**, solve **20,67 ms** | FLR ≤ 5%, OFR ≥ 95% | Lulus |

### 2. Perbandingan 4 Kondisi Eksperimen & 3 Studi Ablasi (30 Siklus Berpasangan)
| Global KPI | Kondisi 0: Siloed Baseline | Kondisi 1: Normal Agentic | Kondisi 2: Disrupt Tanpa Replan | Kondisi 3: Disrupt + Adaptive Replan | Dampak Adaptive (K3 vs K2) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Food Loss Rate (FLR, %)** | 13,38 ± 2,63 | **0,00 ± 0,00** | 15,47 ± 2,44 | **0,00 ± 0,00** | **-15,47 poin %** |
| **Order Fulfillment Rate (OFR, %)** | 98,72 ± 2,11 | 98,72 ± 2,11 | 92,92 ± 7,24 | **98,25 ± 2,79** | **+5,33 poin %** |
| **Total Supply Chain Cost (Rp Juta)** | 29,58 ± 1,25 | 29,52 ± 1,51 | 31,36 ± 1,78 | **29,06 ± 1,72** | **-Rp2,31 Jt (-7,35%)** |
| **Net Ecosystem Profit (Rp Juta)** | 21,74 ± 1,01 | **27,38 ± 1,16** | 20,21 ± 1,64 | **28,16 ± 1,51** | **+Rp7,94 Jt (+39,3%)** |
| **Jain's Fairness Index** | 0,9367 | **0,9607** | 0,8286 | **0,9332** | **+0,1046 (+12,6%)** |
| **Replanning Time (dtk)** | — | 2,24 ± 0,06 | — | **4,23 ± 0,09** | **< 5 detik** |
| **Privacy Leaks (Field Privat)** | 0 | **0** | 0 | **0** | **Zero Leak** |

- **Ablasi 1 (*Multi-Agent 6 Agen* vs *Single-Agent Monolitik*):** Menjaga **0 kebocoran data privat** (vs **15 field privat terekspos**) dan menaikkan *Jain's Fairness Index* dari **0,8355 → 0,9332**.
- **Ablasi 2 (*Heterogeneous 6-LLM* vs *Homogeneous 6× GPT-4o*):** Menghemat biaya token **41,71%** (`USD 17,50` → `USD 10,20` per 1.000 siklus) dan mempercepat *replanning* **10,19%** (`4,71 s` → `4,23 s`; *edge alert* ColdChain turun **-78,2%**).
- **Ablasi 3 (*Neuro-Symbolic MILP-FEFO + LLM* vs *Pure LLM*):** Menurunkan pelanggaran kendala dari **100,0% → 0,0%** dan menekan FLR dari **1,52% → 0,00%**.

![Perbandingan Kinerja Ekosistem pada 4 Kondisi Eksperimen](./results/figures/fig_9_1_conditions.png)
![Hasil Tiga Studi Ablasi Arsitektur Multi-Agent](./results/figures/fig_9_2_ablation_comparison.png)
![Analisis Biaya Token dan Latensi per Agen](./results/figures/fig_9_3_agent_cost_latency.png)

---

## Petunjuk Menjalankan di Visual Studio Code (VS Code)

Proyek ini sudah dilengkapi konfigurasi siap pakai di [`.vscode/launch.json`](./.vscode/launch.json) dan [`.vscode/tasks.json`](./.vscode/tasks.json):

1. **Buka Folder Proyek di VS Code:**
   - Pilih `File` → `Open Folder...` lalu pilih folder `agrichain-agentic-ai` (atau ekstrak `agrichain-agentic-ai_submission.zip`).
2. **Pilih Python Interpreter (Python 3.11+):**
   - Tekan `Ctrl + Shift + P` → ketik `Python: Select Interpreter` → pilih Python 3.11+ (atau virtual environment `.venv`).
3. **Instal Dependensi:**
   - Buka Terminal (`Ctrl + ~`) atau jalankan Task `AgriChain: Install Requirements`:
     ```bash
     pip install -r requirements.txt
     ```
4. **Jalankan Server dengan 1 Klik via *Run & Debug* (`Ctrl + Shift + D`):**
   - Jalankan **`AgriChain: FastAPI Gateway (Port 8000)`** terlebih dahulu (`F5`) → Swagger UI aktif di `http://127.0.0.1:8000/docs`.
   - Jalankan **`AgriChain: Streamlit Control Center (Port 8501)`** (`F5`) → Dashboard v2.0 terhubung penuh ke FastAPI di `http://127.0.0.1:8501`.
   - *(Opsional via Terminal Split)*:
     ```bash
     # Terminal 1 — FastAPI Multi-Enterprise Gateway v2.0
     python -m uvicorn src.api.main:app --reload --port 8000

     # Terminal 2 — Streamlit Decoupled Multi-Enterprise Cockpit v2.0
     python -m streamlit run src/dashboard/app.py --server.port 8501
     ```
5. **Jalankan Pengujian & Reproduksi Eksperimen:**
   ```bash
   # Pengujian otomatis (13/13 unit + closed-loop parity + server-side RBAC + FastAPI integration tests)
   pytest tests/test_ecosystem.py -v

   # Latih ulang 5 model ML v2.0 (termasuk NDVI 80% PI & XGBoost ETA + VRPTW)
   python src/models/train_all.py

   # Jalankan seluruh eksperimen Bab 9 (4 kondisi x 30 siklus + 3 ablasi + 3 grafik)
   python src/experiments/run_experiments.py
   ```
6. *(Opsional)* Mode **LIVE 6-LLM API**: salin `.env.example` menjadi `.env`, ubah `LLM_EXECUTION_MODE=LIVE`, dan isi kredensial OpenAI / Anthropic / Gemini / Mistral / Ollama lokal.

---

## Panduan Alur Demo Presentasi Kelompok (Mode Storyboard 1-Klik)

Dashboard dilengkapi **`🎬 Mode Presentasi (1-Klik Storyboard)`** di baris paling atas, **Live Closed-Loop 5-Enterprise Strip**, **Side-by-Side Live RBAC Proof**, dan tombol **`🔄 Reset`** di *sidebar* sehingga keempat anggota kelompok dapat mendemokan bagian masing-masing secara mulus:

1. **`1️⃣ Al · Koperasi` (`M. Al lail Qadrillah — AGT-02`):**
   - Otomatis masuk sebagai *Cooperative Manager* (`NORMAL`), menampilkan *LightGBM Price Forecast* + *Contract Net Auction*, lalu buka tab **`Koperasi Local DB Explorer`** untuk menampilkan bukti *Side-by-Side* 1-layar (`Token Global → 🔒 REDACTED` vs `Token Koperasi → floor_price_rp 🔓 UNLOCKED`).
2. **`2️⃣ Monanta · AgroFarm` (`Monanta Alfiareza — AGT-01`):**
   - Otomatis masuk sebagai *Farm Manager* (`EXTREME_RAIN`): tabel deviasi **NDVI 14-Hari ± 2σ** (`BLK-11` hujan 96 mm → panen maju `-2 hari`), simulator **RF + 80% Quantile PI** yang tersinkron otomatis, serta sinyal masuk *Flash-Promo SuperMart* (`+300 kg`). *(Bisa juga diuji `SENSOR_OUTAGE` untuk `FALLBACK_HISTORICAL_MEAN`.)*
3. **`3️⃣ Dimas · ColdChain` (`Dimas Prabowo — AGT-04`):**
   - Otomatis masuk sebagai *Fleet & Cold Chain Manager* (`COLD_STORAGE_FAILURE`): **Peta Geospasial OR-Tools VRPTW** otomatis tersinkron ke skenario `COLD_STORAGE_DROP` & *dock window* FreshFood/SuperMart (`0` pelanggaran TW), ditambah tab **Fleet/Shipments CRUD** serta **XGBoost ETA & Monitor 7–12°C**.
4. **`4️⃣ Frans · FreshFood` (`Frans Alwan Purba — AGT-03`):**
   - Otomatis masuk sebagai *QC & Production Manager* (`FOOD_SAFETY_FAIL`): galeri **CNN RGB 4-Kelas** berdampingan dengan **Simulator Hard-Block Lab API** (blokir mutlak `0 kg` ke pangan), tab **FEFO & Dock Window**, serta **QC Feedback → AgroFarm & Valorisasi Kompos/Biogas**.
5. **`5️⃣ Frans · SuperMart` (`Frans Alwan Purba — AGT-05`):**
   - Otomatis masuk sebagai *Purchasing Manager* (`DEMAND_SURGE`): **Proyeksi 7-Hari XGBoost (`H+1..H+7`)** ke hulu, tab **PO CRUD** (guardrail Grade C ditolak, substitusi Grade B ≤ 30% & `ceiling_price` terbuka lokal), serta tab **Goods Receipt SLA 7–12°C**.
6. **`6️⃣ Frans · Global HITL` (`Frans Alwan Purba — AGT-06`) & Swagger 20 Endpoint:**
   - Otomatis masuk sebagai *Global Control Center Operator* (`COMPOUND`): tampilkan **Live 5-Enterprise Closed-Loop Strip**, grafik **Sankey & Decision Shift** *above-the-fold*, klik **`✅ Approve & Commit`** pada *HITL Quick Bar*, verifikasi rantai **SHA-256 (`VERIFIED ✅`)** di tab *Trace, Lineage & Audit*, serta tunjukkan `http://127.0.0.1:8000/docs` (**20 endpoint**) & `pytest tests/test_ecosystem.py -v` (**13/13 PASSED**).

---

## *Endpoint* FastAPI Multi-Enterprise Gateway v2.1 (`src/api/main.py` — 20 Endpoint)

| Method | Endpoint | Fungsi |
| :---: | :--- | :--- |
| `GET` | `/api/v1/health` | Status layanan, SOP suhu tomat (`7,0–12,0°C`), jumlah agen (6), & validasi SHA-256 |
| `GET` | `/.well-known/agent.json` | A2A *Agent Discovery Cards* seluruh 6 agen heterogen |
| `GET` | `/api/v1/enterprises/{enterprise_id}/status` | Status *local microservice*, DB lokal, metrik ML aktual, & field privat yang dilindungi |
| `GET` | `/api/v1/agrofarm/monitoring` | Evaluasi deviasi 14 hari ± 2σ per blok lahan + deteksi *stale sensor* |
| `POST` | `/api/v1/agrofarm/predict` | Prediksi panen RF + NDVI + 80% Quantile PI + jendela panen & *Feature Importance* |
| `POST` | `/api/v1/koperasi/price-forecast` | Prediksi harga pasar LightGBM + *Server-Side Floor Price Redaction* |
| `POST` | `/api/v1/freshfood/qc-inspect` | Uji *Food Safety Hard-Block* + *QC Feedback → AgroFarm* + *Compost/Biogas Valorization* |
| `POST` | `/api/v1/freshfood/schedule` | Penjadwalan lini FEFO + *Dynamic Receiving Dock Window* tersinkron ke ColdChain VRPTW |
| `GET` / `POST` | `/api/v1/coldchain/fleet` | Master armada reefer & driver (CRUD berizin RBAC `coldchain`/`global` + SHA-256 audit) |
| `GET` / `POST` | `/api/v1/coldchain/shipments` | Inbox permintaan pengiriman dengan validasi ketat `deadline > ready_time` & rentang suhu |
| `POST` | `/api/v1/coldchain/vrptw` | Optimasi rute Google OR-Tools **VRPTW** (*Time Windows*) + pembandingan 4 skenario |
| `POST` | `/api/v1/coldchain/eta` | Prediksi durasi perjalanan berbasis **XGBoost ETA Regressor** + *error band* |
| `GET` | `/api/v1/supermart/forecast-7d` | *Rolling forecast* 7 hari XGBoost + *Flash-Promo Absorption* + *Server-Side Ceiling Redaction* |
| `GET` / `POST` | `/api/v1/supermart/po` | Manajemen *Purchase Order* (validasi Grade C dilarang, sub Grade B ≤ 30%, ≤ *ceiling price*) |
| `POST` | `/api/v1/supermart/goods-receipt-sla` | Verifikasi SLA kedatangan ColdChain (SOP `7,0–12,0°C` & ketepatan deadline dermaga) |
| `GET` | `/api/v1/data-explorer/{enterprise_id}/{table_name}` | Query 5 DB lokal terisolasi dengan **Server-Side Privacy Redaction** (`X-Scoped-Token`) |
| `POST` | `/api/v1/orchestrator/run-cycle` | 1 siklus LangGraph (8 skenario) + `lineage` + `vrptw_plan` + `freshfood_qc_feedback` + `supermart_horizon_7d` + `goods_receipt_sla` |
| `POST` | `/api/v1/orchestrator/hitl/{cycle_id}/approve` | Persetujuan operator HITL (tercatat hash SHA-256 ke `audit_trail.jsonl`) |
| `POST` | `/api/v1/orchestrator/hitl/{cycle_id}/reject` | Penolakan operator HITL dengan catatan audit SHA-256 |
| `GET` | `/api/v1/audit/trail` | Mengambil catatan *hash-chained audit trail* terbaru + status verifikasi kriptografi |

---

## Struktur Repositori

```text
agrichain-agentic-ai/
├── .streamlit/
│   └── config.toml                      # Tema Light Mode berkontras tinggi (WCAG AAA, navy #1F4E79)
├── .vscode/
│   ├── launch.json                      # 1-klik Run & Debug VS Code (FastAPI, Streamlit, Train, Experiments)
│   └── tasks.json                       # Task otomatis VS Code (Install, Pytest, Servers)
├── config/settings.py                   # Registri 6 profil LLM, SOP suhu 7–12°C, ambang HITL & deviasi 2σ
├── src/
│   ├── data/                            # Generator 19.575 rekaman + 3.000 citra RGB + Adapter 5 DB lokal
│   ├── protocols/                       # A2A, FIPA-ACL, GS1 EPCIS 2.0, Server-Side RBAC Firewall, SHA-256 Audit
│   ├── models/                          # 5 model ML v2.1 (RF+NDVI+PI80, LightGBM, CNN, IF+XGB-ETA+VRPTW, XGB 7d) + MILP-FEFO
│   ├── llm/                             # 6 System Prompts + Multi-Provider 6-LLM Router (LIVE & SIMULATED)
│   ├── agents/                          # 5 Enterprise Agents + LangGraph Orchestrator v2.1 (Closed-Loop Lineage & Briefing)
│   ├── api/main.py                      # FastAPI Decoupled Gateway v2.1 (20 Endpoint + Full 5-Enterprise Parity)
│   ├── experiments/run_experiments.py   # Benchmark 4 Kondisi x 30 siklus + 3 Ablasi + 3 Failure Cases
│   └── dashboard/app.py                 # Streamlit Role-Adaptive Light-Mode Cockpit v2.1 (6 Dedicated Role Views)
├── tests/test_ecosystem.py              # 13 Automated Unit, RBAC, Closed-Loop Parity & FastAPI Integration Tests
├── docs/screenshots/                    # 7 Screenshot aktual aplikasi v2.1 (Light Mode) & FastAPI Swagger UI
├── data/                                # Dataset dummy tergenerasi & 5 database lokal terisolasi
├── results/                             # Model terlatih (.pkl), metrik JSON, audit_trail.jsonl, & 3 grafik Bab 9
├── docker-compose.yml                   # Stack PostgreSQL 16, MySQL 8, MongoDB 7, TimescaleDB, Redis 7
└── Laporan_Bab1_11_Smart_Agriculture_Agentic_AI.{md,docx,pdf}    # Laporan Lengkap v2.1 (Bab 1–11, 54 halaman)
```
