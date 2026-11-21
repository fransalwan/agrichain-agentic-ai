# Rancangan Improvement Proper — `agrichain-agentic-ai` v2.0

> **Dasar Evaluasi:** Sintesis dari `Analisis_Insight_ColdChain_AgroFarm_UIUX.md` (12 berkas rancangan ColdChain Revised, AgroFarm v2, dan 9 Menu UI/UX) dibandingkan terhadap implementasi aktual `agrichain-agentic-ai` v1.x.  
> **Tujuan:** Menyatukan keunggulan *strict domain depth* (AgroFarm v2 & ColdChain Revised) + standar *enterprise UI/UX governance* (9 Menu ColdChain) + kekuatan *full-ecosystem orchestration* (`agrichain-agentic-ai`) ke dalam rancangan peningkatan arsitektur, AI/optimasi, dan UI/UX yang *production-ready*.

---

## 1. Prinsip Arsitektur Improvement (*North Star*)

Berdasarkan temuan evaluasi, aplikasi `agrichain-agentic-ai` saat ini sudah unggul pada **koordinasi makro 5 enterprise + MILP-FEFO + 6 LLM + studi ablasi**, namun masih perlu diperdalam di 4 aspek agar benar-benar *proper* secara rekayasa perangkat lunak:
1. **Decoupled Service Boundary (UI ↔ API Nyata):** Saat ini `src/dashboard/app.py` mengimpor `AgriChainOrchestrator` langsung di dalam proses Python yang sama. Improvement proper memisahkan UI agar berkomunikasi via **FastAPI REST/HTTP** dengan header autentikasi `X-Scoped-Token` per peran.
2. **Penyelarasan Kontrak Data & Domain Biologis:** Menyelesaikan seluruh 5 konflik lintas-dokumen (topologi kanal AgroFarm–ColdChain, suhu tomat `7–12°C`, lineage ID `block_id → lot_id → shipment_id → trip_id`).
3. **Pendalaman AI & Optimasi Lokal pada 2 Enterprise Kunci (`AGT-01` & `AGT-04`):** Mengadopsi kekuatan spesifik dari `AgroFarm v2` (NDVI, 80% Quantile PI, 14-day moving average ± 2σ, sensor fallback, hujan ekstrem) dan `ColdChain Revised` (OR-Tools **VRPTW**, **XGBoost ETA**, relasi DB `trip_shipments`).
4. **Enterprise-Grade UI/UX Governance:** Menerapkan **Role-Adaptive Navigation**, **5 Mandatory UI States** (*Loading, Empty, Error, Stale/Partial Data, Success*), dan **Impact-Preview Confirmation** sebelum tombol *Approve/Reject* HITL.

---

## 2. Pillar 1 — Penyelarasan Arsitektur, Topologi API & Kontrak Data

### A. Resolusi Topologi Komunikasi (Menutup Konflik AgroFarm ↔ ColdChain)
- **Keputusan Desain:** Terapkan pola ***Brokered Single-Gate Integration***:
  - `AgroFarm (AGT-01)` hanya membuka 1 pintu keluar (`HARVEST_FORECAST`) ke `Koperasi Tani (AGT-02)` dan *authorized summary* ke `Global Orchestrator (AGT-06)`.
  - `ColdChain (AGT-04)` menerima `SHIPMENT_REQUEST` resmi dari `Koperasi Tani` dan *capacity/replanning directives* dari `Global Orchestrator` — **tidak ada kanal langsung ilegal** antara AgroFarm ↔ ColdChain yang berisiko menciptakan duplikasi atau konflik volume lot.
- **Standarisasi Biologis Komoditas Tomat:** Kunci ambang suhu optimal tomat segar secara global pada **`7,0°C – 12,0°C`** (menggantikan `2–8°C` dari draf ColdChain yang memicu *chilling injury*) di satu file konfigurasi tunggal (`config/settings.py`).

### B. Canonical Cross-Enterprise Lineage & Normalisasi Skema DB
Setiap objek panen dapat ditelusuri ujung-ke-ujung (*end-to-end traceability*) tanpa membocorkan data privat melalui rantai kunci berikut:

```text
AgroFarm (block_id: BLK-11)
   └──► Koperasi Tani (lot_id: H003)
          └──► FreshFood QC (qc_doc_id: QC-H003)
          └──► ColdChain Logistics (shipment_id: SH003 ──► trip_shipments ──► trip_id: T003 ──► vehicle_id: V001)
                 └──► SuperMart (po_id: PO-SM01)
```

### C. Decoupling Frontend ↔ Backend (FastAPI sebagai Single Entry Point)
- Tambahkan *endpoint* khusus per modul pada `src/api/main.py`:
  - `POST /api/v1/agrofarm/predict-block` & `GET /api/v1/agrofarm/monitoring`
  - `GET /api/v1/coldchain/fleet`, `POST /api/v1/coldchain/shipments`, `POST /api/v1/coldchain/optimize-vrptw`
  - `GET /api/v1/data-explorer/{enterprise}/{table}` (dengan *server-side privacy redaction* berdasarkan token `X-Scoped-Token`, bukan hanya masking di sisi frontend!).
- Mode `app.py` memakai `httpx` memanggil FastAPI (dengan opsi *fallback* lokal bila API mati, menampilkan banner *Degraded Local Mode*).

---

## 3. Pillar 2 — Pendalaman Model AI & Optimasi (Adopsi AgroFarm v2 & ColdChain Revised)

### A. Upgrade Modul AgroFarm (`AGT-01`)
| Fitur | Kondisi Sekarang (`v1.x`) | Improvement Proper (`v2.0`) |
| :--- | :--- | :--- |
| **Fitur Input & Monitoring** | 6 fitur statis (`area_ha`, `temp`, `moisture`, `rain`, `fert`, `age`) | Tambah **`NDVI`**, **`pest_score`**, **`variety`**, serta tabel `blok_lahan`, `sensor_harian`, `penandaan_blok` |
| **Deteksi Penyimpangan Lahan** | Belum ada aturan khusus | **Rule-Based Crop Monitoring Engine:** perbandingan harian terhadap *14-day moving average ± 2σ* + ambang agronomis `Farm Manager` |
| **Uncertainty Quantification** | CI 95% normal (`mean ± 1.96·std`) | **80% Quantile Prediction Interval** (persentil ke-10 & ke-90 sebaran 400 pohon RF) + grafik **Feature Importance** |
| **Safety Fallback** | Belum ada | Jika sensor blok mati ≥ 3 hari atau MAE model kalah dari baseline historis → otomatis turun ke `FALLBACK_MODE`, lebarkan interval, dan beri label *Meragukan* di UI |
| **Skenario Adaptif Baru** | Hanya *Harvest Deferral* saat hilir rusak | Tambah skenario **Hujan Ekstrem (`EXTREME_RAIN`)**: estimasi `BLK-11` turun (-13,9%), jendela panen **maju 2 hari**, otomatis kirim revisi `HARVEST_FORECAST` ke Koperasi & picu re-solve MILP global |

### B. Upgrade Modul ColdChain (`AGT-04`)
| Fitur | Kondisi Sekarang (`v1.x`) | Improvement Proper (`v2.0`) |
| :--- | :--- | :--- |
| **Optimasi Rute** | OR-Tools **CVRP** (kapasitas & jarak saja) | Upgrade ke OR-Tools **VRPTW** (*ready_time*, *deadline*, *service_time*, *late_penalty*, kompatibilitas suhu reefer, multi-bobot objektif `α·Dist + β·Time + γ·Cost + δ·Late`) |
| **Prediksi ETA** | Belum ada model ML ETA | Tambah **XGBoost ETA Regressor** (`distance_km`, `traffic_level`, `stops`, `weather`, `departure_hour`) dengan evaluasi *chronological split* (`MAE`, `RMSE`) |
| **Manajemen Operasional** | Read-only chart + 1 demo CVRP | Tambah CRUD master **Fleet & Drivers** (`vehicles`), **Shipments Inbox** (`shipments` + validasi `deadline > ready_time`), dan **Cold Storage Slot** |
| **Auditability Model** | Log per siklus global | Tabel `agent_decisions` lengkap dengan **`model_version`**, **`input_reference`**, **`output_before`**, **`output_after`**, **`rationale`**, dan **`human_approval`** |

---

## 4. Pillar 3 — Improvement UI/UX Proper (*Enterprise Workspace Standard*)

### A. Navigasi Adaptif Berbasis Peran (*Role-Adaptive Navigation*)
Alih-alih menampilkan 8 tab yang sama persis untuk semua peran (yang membuat `Farm Manager` atau `Fleet Manager` kewalahan melihat menu enterprise lain), terapkan **Sidebar Navigation dinamis berbasis Peran Login**:

- **Login sebagai `Global Control Center Operator (AGT-06)`:**
  - *Global Overview (Before/After Delta)* · *Live Agent Status & Decision Trace* · *Negotiation Feed & HITL* · *Cross-Enterprise Data Explorer (Privacy Redacted)* · *Benchmark & Ablation Explorer*.
- **Login sebagai `Farm Manager (AGT-01)` (Mengadopsi 4 Menu AgroFarm v2):**
  - *AgroFarm Overview (KPI Panen + Prediksi vs Realisasi)* · *Crop Monitoring (NDVI & 14-Day Deviation)* · *Yield Prediction (RF + 80% PI + Feature Importance + Jendela Panen)* · *Agent Activity & Audit*.
- **Login sebagai `Fleet Manager (AGT-04)` (Mengadopsi 9 Menu ColdChain UI/UX yang Dirampingkan Jadi 5 Sub-Tab Rapi):**
  - *Fleet Overview & Live Tracking (Peta + XGBoost ETA)* · *Fleet & Shipments Management (Form + Validasi)* · *Route Planning (VRPTW + Scenario Comparison)* · *Cold Chain Monitor & Storage Slots (Isolation Forest)* · *Agent Activity & Audit*.
- **Login sebagai `Koperasi / FreshFood / SuperMart Manager`:** Menampilkan *dedicated cockpit* masing-masing dengan data privat lokal terbuka penuh + ringkasan *shared status* ekosistem.

### B. Penerapan Wajib 5 *UI States* (Dari Standar Paket UI/UX ColdChain)
Setiap panel data dan form wajib menangani 5 *state* secara eksplisit:
1. **`Loading State`:** Tampilkan `st.status(...)` / *skeleton placeholder* dan kunci tombol submit (`disabled=True`) untuk mencegah klik ganda.
2. **`Empty State`:** Tampilkan kartu informatif *"Belum ada shipment / event gangguan"* beserta tombol CTA langkah berikutnya (*"Buat Shipment Baru"* / *"Jalankan Simulasi"*).
3. **`Error State`:** Tampilkan pesan error yang dapat ditindaklanjuti, *timestamp* data terakhir yang berhasil dimuat, dan tombol **`Retry Aman`**.
4. **`Stale / Partial Data Warning`:** Tampilkan badge kuning mencolok (`⚠️ DATA USANG — Terakhir sinkron 42 menit lalu` atau `⚠️ SENSOR BLK-11 OFFLINE 3 HARI — Mode Fallback`) sehingga **data lama tidak pernah tersaji seolah-olah *real-time***.
5. **`Success + Audit Feedback`:** Setiap aksi ubah data, *dispatch*, atau *HITL Approve/Reject* menampilkan toast konfirmasi + kode hash SHA-256 yang tercatat di `agent_decisions` / `audit_trail.jsonl`.

### C. *Impact-Preview Confirmation* Sebelum Otorisasi Manusia (HITL)
Sebelum `Global Operator`, `Fleet Manager`, atau `Farm Manager` menekan tombol **Approve**, tampilkan kartu **Pratinjau Dampak Keputusan** berisi:
- **Perubahan Terukur:** `FLR (Sebelum → Sesudah)`, `OFR`, `Total Jarak/Biaya`, `Delta ETA`, dan `Pergeseran Jadwal/Jendela Panen`.
- **Mitra Terdampak:** Daftar enterprise yang akan menerima notifikasi API pembaruan (`Koperasi`, `FreshFood`, `SuperMart`).
- **Tiga Opsi Aksi Nyata:** `✅ Approve & Dispatch`, `🔄 Re-Optimize dengan Batasan Baru`, atau `⛔ Reject & Catat Alasan`.

### D. Perbaikan Visual & Keterbacaan Dashboard
- Mengganti *placeholder* grafik polos dengan **Peta Geografis Interaktif** (`plotly.express.scatter_mapbox` / `pydeck` koordinat sentra tomat & gudang Yogyakarta/Jawa Tengah) untuk *Route Planning* dan *Live Tracking*.
- Menyediakan **Panel Inspektor LLM Transparan** (*System Prompt*, *Mode `LIVE_API` vs `SIMULATED`*, token in/out, dan narasi *Executive Briefing* bahasa Indonesia otomatis bagi operator HITL).

---

## 5. Roadmap Implementasi Proper (3 Fase)

| Fase | Fokus Pekerjaan | Modul Target | *Definition of Done* (DoD) |
| :--- | :--- | :--- | :--- |
| **Fase 1 — Harmonisasi Data, API & UX Governance** | Standarisasi suhu `7–12°C`, lineage ID `block→lot→shipment→trip`, *server-side privacy redaction* di FastAPI, *Role-Adaptive Navigation*, dan **5 UI States** (*Loading/Empty/Error/Stale/Success*) + *Impact-Preview HITL*. | `config/settings.py`, `src/api/main.py`, `src/dashboard/app.py` | UI memanggil FastAPI via `X-Scoped-Token`, zero *privacy leak* teruji server-side, *stale data banner* berfungsi saat sensor dimatikan. |
| **Fase 2 — Pendalaman AI Lokal (`AGT-01` & `AGT-04`)** | AgroFarm: tambah `NDVI`, *14-day ± 2σ monitor*, *80% Quantile PI*, *Feature Importance*, *sensor fallback*, skenario **Hujan Ekstrem**. ColdChain: upgrade **CVRP → VRPTW**, tambah **XGBoost ETA**, dan CRUD Fleet/Shipments. | `src/models/agrofarm_rf.py`, `src/models/coldchain_iforest_cvrp.py`, `src/agents/orchestrator.py` | Hujan ekstrem memajukan jendela panen & merevisi alokasi global; VRPTW memenuhi 100% *time windows*; XGBoost ETA teruji *chronological split*. |
| **Fase 3 — Geospasial, Live LLM Briefing & QA Penuh** | Peta rute interaktif (`pydeck`/`mapbox`), *Executive HITL Briefing* otomatis (mendukung `LIVE` API + `SIMULATED`), perluasan `pytest` dengan target *code coverage* `>= 80%` pada `src/agents` & `src/api`. | `src/dashboard/app.py`, `src/llm/router.py`, `tests/test_ecosystem.py` | `pytest --cov=src/agents --cov=src/api` lulus 100% (coverage ≥ 80%), seluruh 6+ screenshot terbarui tanpa error UI. |
