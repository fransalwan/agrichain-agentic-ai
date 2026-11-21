# Analisis & Rangkuman Insight: Rancangan Enterprise ColdChain Logistics, AgroFarm, dan Paket UI/UX Design (All Menus)

> **Cakupan Analisis:** 12 berkas `.docx` rancangan akademik *Case Study 6 — Smart Agriculture & Food Supply Chain Ecosystem*  
> **Tanggal Analisis:** 21 November 2026  
> **Repositori Terkait:** `agrichain-agentic-ai`

---

## 1. Ringkasan Eksekutif & Inventaris Dokumen

Analisis ini membedah secara menyeluruh **12 berkas `.docx`** (baik teks, tabel skema, kontrak JSON, maupun seluruh diagram/wireframe yang tertanam di dalamnya):

| Kelompok Dokumen | Nama Berkas | Skala Isi | Fokus Utama |
| :--- | :--- | :--- | :--- |
| **Rancangan ColdChain** | `Rancangan_ColdChain_Logistics_Fleet_Manager_Revised.docx` | 142 paragraf, 21 tabel, 4 gambar | *Intelligent Cold Chain Fleet Management System* (9 modul, `Fleet Manager`, XGBoost ETA + Isolation Forest + OR-Tools VRPTW + Fleet Orchestrator) |
| **Rancangan AgroFarm** | `Rancangan_Enterprise_AgroFarm_Formatted_v2.docx` | 162 paragraf, 22 tabel, 4 gambar | *Strict-Scope Crop Monitoring & Yield Prediction* (2 modul, `Farm Manager`, Random Forest Regression + 80% PI + aturan 14-day moving average) |
| **Paket UI/UX ColdChain (10 file)** | `ColdChain_Logistics_UIUX_Designs_All_Menus/00_Index_UIUX_Menu.docx` + `ColdChain_UIUX_01` s.d. `09` | 10 berkas, 28 tabel, 9 wireframe | Spesifikasi UI/UX per halaman untuk 9 menu `Fleet Manager` lengkap dengan KPI, input/validasi, aksi, keterkaitan AI, 5 *UI states*, dan *audit governance* |

### Inti Temuan Cepat (*Executive Takeaways*)
1. **Dua Filosofi Desain yang Saling Melengkapi:** Dokumen **AgroFarm** mengutamakan **ketepatan cakupan (*strict scope*) dan bukti adaptasi numerik yang sangat tajam** (skenario hujan ekstrem `BLK-11` dengan tabel delta 7 metrik), sedangkan dokumen **ColdChain** mengutamakan **kelengkapan operasional enterprise end-to-end** (9 menu, multi-specialist agent, VRPTW + ETA + IoT + Cold Storage + Audit).
2. **Disiplin Ilmiah & Pemisahan ML vs Optimasi Sangat Baik:** Kedua dokumen jujur memisahkan *data sintetis/usulan* dari klaim produksi, serta tegas membedakan **model ML terlatih** (Random Forest, XGBoost, Isolation Forest) dari **solver optimasi** (Google OR-Tools VRPTW) dan **aturan deterministik** (threshold crop monitoring).
3. **Ditemukan 5 Konflik & Cacat Teknis Penting yang Wajib Disinkronkan:**
   - **Konflik topologi API** antara AgroFarm (menutup kanal langsung ke ColdChain, wajib lewat Koperasi) vs ColdChain (menggambar panah API langsung dari AgroFarm).
   - **Anomali suhu domain tomat** pada ColdChain (`2–8°C`) yang berisiko *chilling injury* (standar pascapanen tomat adalah `7–12°C`).
   - **Inkonsistensi gambar lama vs teks baru** pada dokumen AgroFarm v2 (gambar masih menyebut `scheduler, negotiator, /harvest-plan, G1 cold storage` padahal teks v2 sudah mencabut modul-modul tersebut).
   - **Wireframe & tabel *boilerplate*** pada 9 dokumen UI/UX ColdChain (hanya memakai 2 template gambar generik dan kalimat tabel yang berulang identik).
   - **Ketidaksinkronan navigasi** pada wireframe Overview di dokumen utama ColdChain (memuat menu `Alerts` dan teks tabel bertumpuk `SH001`/`Status`) dibanding daftar 9 menu pada paket UI/UX (`Live Tracking`).

---

## 2. Analisis Mendalam: Rancangan ColdChain Logistics (`Fleet Manager`)

**Sumber:** `Rancangan_ColdChain_Logistics_Fleet_Manager_Revised.docx`

### 2.1 Ruang Lingkup & Stakeholder
- **Single Primary Stakeholder:** **Fleet Manager** sebagai satu-satunya pengguna dashboard dan pemegang otoritas persetujuan (*human approval*).
- **Batasan Tegas:** Driver dan staf *cold storage* dimodelkan sebagai **objek/data operasional** (bukan pengguna dashboard), sedangkan 4 perusahaan lain (*AgroFarm, Koperasi Tani, FreshFood Processing, SuperMart*) diperlakukan sebagai **external integration partners** via API terotorisasi.

### 2.2 Arsitektur Multi-Agent & Pemisahan Model AI/Algoritma
Dokumen ini merancang **6 komponen agentic/AI** yang tersusun dalam arsitektur 6 lapis (*Fleet Manager UI → FastAPI Gateway → Fleet Orchestrator → Specialist Agents → Operational Services → PostgreSQL Local DB*):

| Komponen / Agent | Algoritma / Model | Kategori | Peran & Output Utama |
| :--- | :--- | :--- | :--- |
| **ETA Prediction Agent** | **XGBoost Regressor** | Supervised Regression | Memprediksi `actual_duration_minutes` / ETA dari jarak, kecepatan, traffic, cuaca, jumlah stop, dan jam/hari (`MAE`, `RMSE`, `MAPE`) |
| **Cold Chain Monitoring Agent** | **Isolation Forest** | Unsupervised Anomaly | Mendeteksi anomali suhu/humidity/pintu/reefer; **tidak** langsung mendiagnosis kerusakan produk melainkan digabung dengan threshold SOP & durasi *excursion* |
| **Route Optimization Agent** | **Google OR-Tools (VRPTW)** | Operations Research | Menyusun rute multi-kendaraan dengan *time windows* (`min α·Dist + β·Time + γ·Cost + δ·LatePenalty`); secara eksplisit ditegaskan sebagai *solver*, bukan model terlatih |
| **Fleet Allocation Agent** | **Constraint Programming** | Assignment Optimization | Menyaring & memasangkan kendaraan berdasarkan status `Available`, kapasitas kg, rentang suhu produk, dan jadwal |
| **Vehicle Health Agent *(Opsional)*** | Random Forest / Isolation Forest | Classification / Anomaly | Estimasi risiko kerusakan reefer; jika belum ada label kegagalan, *fallback* ke *rule-based maintenance* |
| **Fleet Orchestrator** | Policy Engine + Agent Workflow | Reasoning & Coordination | Validasi API, memanggil specialist agents, cek *deadline/shelf-life*, minta *human approval*, picu *replanning*, dan menulis *audit trail* |

### 2.3 Skema Data, Dataset & Skenario Adaptif
- **8 Tabel Relasional (PostgreSQL):** `vehicles`, `shipments`, `trips`, `trip_shipments` (*many-to-many*), `gps_logs`, `sensor_logs`, `maintenance_history`, `agent_decisions`.
- **Strategi Dataset Hybrid:** Memisahkan dataset ML (*Delivering Data* + trip sintetis untuk ETA, *cold-chain telemetry* untuk Isolation Forest), benchmark OR (*Solomon VRPTW instances*), dan skenario bisnis tomat (`H001–H003`).
- **4 Skenario Gangguan Adaptif:**
  1. *Temperature excursion* → incident + inspeksi reefer / opsi transfer muatan.
  2. *Vehicle breakdown* → cari kendaraan pengganti + hitung ulang rute OR-Tools + kirim ETA baru ke mitra.
  3. *Road disruption* → perbarui travel-time matrix + optimasi ulang rute.
  4. *Cold storage capacity drop* → prioritaskan lot dengan *shelf life* terpendek (*FEFO*) + alihkan slot.
- **7 KPI Evaluasi:** *On-Time Delivery (OTD)*, *ETA MAE*, *Temperature Compliance*, *Vehicle Utilization*, *Total Distance*, *Replanning Time*, dan *Food Loss Rate*.

### 2.4 Kekuatan & Catatan Kritis ColdChain
- **Kekuatan:** Sangat komprehensif, membedakan ML vs OR dengan sangat akurat, skema DB sudah ternormalisasi (`trip_shipments` *many-to-many*), tahapan implementasi jelas (`P1 Core → P2 Predictive → P3 Adaptive`), dan pemetaan rubrik Bagian D sangat rapi.
- **Catatan Kritis:**
  1. **Belum ada tabel perbandingan angka *Before vs After* yang konkret** untuk 1 skenario gangguan (seperti yang dimiliki AgroFarm di Bagian 7.3) — baru berupa tabel konseptual *Event → Respons*.
  2. **Rentang suhu tomat `2–8°C`** pada payload `SH001` dan tabel sensor dummy (`4,5°C` dianggap normal) kurang tepat untuk tomat (*Solanum lycopersicum* optimal di `7–12°C`; di bawah 7°C berisiko *chilling injury*).
  3. **Ketidaksinkronan tampilan wireframe** pada Gambar 3 dokumen utama: teks `SH001` menabrak header `Status` di bagian bawah, dan daftar menu menampilkan `Alerts` (bukan `Live Tracking`).

---

## 3. Analisis Mendalam: Rancangan Enterprise AgroFarm (`Farm Manager`)

**Sumber:** `Rancangan_Enterprise_AgroFarm_Formatted_v2.docx`

### 3.1 Filosofi Desain: *Strict Scope* & Disiplin Batasan
- **Single Primary Stakeholder:** **Farm Manager** (agronomis lapangan & petani mitra bukan pengguna dashboard).
- **Hanya 2 Modul Inti (Persis Spesifikasi Tugas):**
  1. **Crop Monitoring:** Registrasi blok lahan, sensor harian (`NDVI`, kelembapan tanah, suhu, curah hujan), dan **aturan penandaan berbasis deviasi diri sendiri** (*moving average 14 hari ± 2 simpangan baku* + ambang agronomis Farm Manager) — bukan model ML terpisah.
  2. **Yield Prediction:** **Random Forest Regression** (`n_estimators=400`, `max_depth=12`, `min_samples_leaf=3`, `max_features=0.6`, `random_state=42`) dengan keluaran **prediksi titik + Interval Keyakinan 80%** (persentil ke-10 & ke-90 sebaran antar-pohon) + **Feature Importance** + **rekomendasi jendela panen** berbasis indeks kematangan (`umur tanaman + NDVI`).
- **Mekanisme *Model Safety Fallback*:** Model RF hanya dipakai jika mengungguli 2 baseline (*rata-rata historis per blok* & *regresi linear*) dan *coverage interval 80%* berada di rentang `0,75–0,85`; jika gagal (atau sensor mati ≥ 3 hari), agen otomatis turun ke *mode fallback* dan menandai prediksi sebagai meragukan.
- **Arsitektur Satu Pintu (*Single-Gate Integration*):** AgroFarm hanya berkomunikasi dengan **Koperasi Tani** (`HARVEST_FORECAST` keluar, `FORECAST_ACK` + `actual_yield_kg` masuk untuk menghitung *MAPE berjalan*). Tidak membuka kanal langsung ke FreshFood, ColdChain, atau SuperMart.

### 3.2 Bukti Adaptif Terukur (Keunggulan Terbesar Dokumen Ini)
AgroFarm menetapkan **1 skenario tolok ukur yang terukur penuh** — *Hujan Ekstrem pada Blok `BLK-11` (curah hujan 14 hari = 96 mm > ambang 90 mm; NDVI turun 0,23)*:

| Metrik Terukur | Sebelum (Prediksi H-7) | Sesudah (Prediksi H-2) | Perubahan Nyata |
| :--- | :---: | :---: | :--- |
| Estimasi hasil `BLK-11` | 1.010 kg | **870 kg** | **Turun 140 kg (-13,9%)** |
| Interval keyakinan 80% | 820 – 1.265 kg | **610 – 1.190 kg** | **Melebar +135 kg** |
| Rekomendasi jendela panen | 21 – 23 November | **19 – 20 November** | **Maju 2 hari** |
| Status blok | Normal | **Menyimpang (curah hujan)** | Berubah |
| Total estimasi 3 blok | 4.630 kg | **4.490 kg** | Turun 140 kg |
| Pesan API ke Koperasi | 1 `HARVEST_FORECAST` | +1 revisi + alasan | Bertambah 1 pesan |
| Waktu reaksi agen | — | **1,8 detik** | Adaptasi otomatis + *decision trace* |

### 3.3 Skema Data, Paket Kode & Petunjuk VS Code
- **8 Tabel SQLite Lokal:** `blok_lahan`, `sensor_harian`, `perlakuan`, `panen_historis`, `prediksi_yield`, `penandaan_blok`, `pesan_agen`, `agent_decisions`.
- **8 KPI Terukur:** *Yield Forecast MAPE* (< 12%), *Forecast Interval Coverage* (0,75–0,85), *Forecast Lead Time* (≥ 7 hari), *Forecast Revision Rate*, *Flag Precision* (> 0,7), *Sensor Data Completeness* (> 95%), *Reaction Time* (< 5 detik), dan *Decision Traceability* (100%).
- **Siap Eksekusi:** Sudah memuat struktur folder `agrofarm/`, paket `agrofarm_kelompok5.zip`, perintah uji `pytest -q --cov=agent --cov=api` (target coverage ≥ 80%), langkah rinci **VS Code** (`uvicorn --port 8001` + `streamlit --port 8501`), serta **skrip demo 7 langkah**.

### 3.4 Catatan Kritis / Inkonsistensi Internal pada AgroFarm v2
Temuan audit dokumen + pemeriksaan gambar tertanam menunjukkan **artefak versi lama belum dibersihkan**:
1. **Gambar 1 (`agrofarm_main_img4.png`) & Gambar 4 (`agrofarm_main_img6.png`)** masih menampilkan agen `predictor, scheduler, negotiator (contract net)` dan endpoint `/harvest-plan`, padahal **teks Bagian 1.1, 4, dan 7.1** menegaskan bahwa penjadwalan volume harian dan negosiasi *berada di luar batasan sistem* dan endpoint-nya adalah `/monitor, /predict, /inbox, /outbox`.
2. **Gambar 3 Wireframe (`agrofarm_main_img5.png`)** masih menampilkan **5 menu** (`Dashboard, Monitoring, Prediksi, Jadwal panen, Status agen`) dan skenario `G1 cold storage (BLK-03 ditunda 2 hari)`, sedangkan **teks Bagian 6.1 & 7.3** menetapkan **4 menu** (`Overview, Crop Monitoring, Yield Prediction, Agent Activity & Audit`) dan skenario *Hujan Ekstrem `BLK-11` maju 2 hari*.
3. **Media Sisa Template:** Di dalam zip XML `.docx` AgroFarm masih terselip file gambar diagram ColdChain (`image3.png` — *Fleet Manager UI → ColdChain API Server*) yang kemungkinan terbawa saat menyalin gaya dokumen ColdChain.

---

## 4. Analisis Paket UI/UX Design ColdChain (`All Menus` — 10 Dokumen)

**Sumber:** `ColdChain_Logistics_UIUX_Designs_All_Menus/00_Index_UIUX_Menu.docx` & `ColdChain_UIUX_01` s.d. `09`

### 4.1 Matriks Lengkap 9 Menu Dashboard `Fleet Manager`

| No | Menu | Tujuan Operasional | Komponen Utama | 4 KPI Utama | Aksi Fleet Manager | Keterkaitan AI / Optimasi |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| **01** | **Overview** | Ringkasan armada, shipment, alert & status agent | Peta kendaraan/rute, alert queue, status agent, tabel shipment | Active Vehicles, Active Shipments, On-Time Delivery, Temperature Alerts | Buka detail, acknowledge alert, buka decision trace, refresh | Agregasi Orchestrator (Allocation + OR-Tools + XGBoost + IForest) |
| **02** | **Fleet & Drivers** | Master armada & referensi penugasan driver | Tabel kendaraan, detail kendaraan, histori trip/sensor/maintenance, modal Add/Edit | Total Vehicles, Available, In Transit, Maintenance | Tambah/edit kendaraan, ubah status, assign driver, blokir armada | Input *constraints* Fleet Allocation + opsional Vehicle Health |
| **03** | **Shipments** | Inbox order dari mitra eksternal & validasi kesiapan | API request inbox, tabel shipment, payload validator, form create/edit | New Requests, Ready for Planning, In Transit, Exception | Validasi request, koreksi, atur prioritas, tandai Ready, cancel + alasan | Mapping ke VRPTW (*quantity→demand, deadline→time window, shelf-life→priority, temp→constraint*) |
| **04** | **Route Planning** | Optimasi multi-kendaraan & perbandingan skenario | Peta rute, daftar stop, ringkasan per truk, *scenario comparison*, *feasibility panel* | Unassigned Shipments, Planned Vehicles, Estimated Distance, Time Window Violations | Generate plan, bandingkan skenario, save draft, approve/reject dispatch, re-optimize | **OR-Tools VRPTW** + Fleet Allocation + XGBoost ETA |
| **05** | **Live Tracking** | Pantau GPS, progres trip, deviasi rute & delta ETA | Peta GPS vs planned route, vehicle list, trip panel, timeline, exception panel | Vehicles Online, Trips In Progress, Delayed Trips, Route Deviations | Pilih trip, tinjau GPS trace, cek ETA, buat incident, kirim update ETA ke mitra, replan | **XGBoost ETA** real-time + pemicu ulang VRPTW jika *deadline* berisiko |
| **06** | **Cold Chain Monitor** | Pantau suhu/humidity, skor anomali & manajemen alert | Grafik suhu/humidity + threshold band, latest readings, alert queue, incident drawer | Sensors Reporting, Active Alerts, Temperature Compliance, Open Excursions | Acknowledge alert, buat incident, minta cek reefer, ajukan transfer/replanning, tutup alert | **Isolation Forest** + SOP threshold & durasi *excursion* (fallback: rule-based) |
| **07** | **Cold Storage** | Visibilitas kapasitas, okupansi, suhu ruang & slot | Capacity cards, facility status, suhu ruang, jadwal inbound/outbound, alokasi lot, alerts | Total Capacity, Occupied, Available Capacity, Facility Alerts | Lihat kapasitas, tinjau/update kapasitas resmi, minta alternatif fasilitas, evaluasi ulang rute | Parameter/constraint kapasitas bagi Orchestrator (prioritas lot umur pendek) |
| **08** | **Agent Activity** | Transparansi status eksekusi agent, model & approval | Agent health cards, task log, decision detail, approval queue, execution timeline | Running Tasks, Completed, Failed, Pending Approval | Cek status agent, buka trace, retry task aman, approve/reject, pause/escalate, catat alasan | Observabilitas 5 komponen (bukan halaman training model) |
| **09** | **Reports & Audit** | Evaluasi KPI historis, komparasi aktual vs prediksi & audit | KPI summary, trend charts, report table, audit log, decision detail timeline | OTD, ETA MAE, Temp Compliance, Utilization, Total Distance, Replanning Time, FLR | Filter laporan, ekspor CSV/PDF, telusuri trace, tambah anotasi, bandingkan prediksi vs aktual | Evaluasi *post-hoc* XGBoost (MAE), IForest (P/R/F1), OR-Tools (jarak/feasibility) |

### 4.2 Prinsip UX & Tata Kelola Unggulan (Konsisten di Semua 9 Dokumen)
- **Standar 5 *UI States* Wajib:** Setiap halaman secara eksplisit mendefinisikan perilaku untuk `Loading` (*skeleton + cegah double-submit*), `Empty` (*next-step guidance*), `Error` (*pesan actionable + timestamp data terakhir + safe retry*), `Stale/Partial Data` (**dilarang menampilkan data lama seolah-olah real-time**), dan `Success` (*konfirmasi + simpan ke audit trail*).
- **Human-in-the-Loop & Dampak Sebelum Konfirmasi:** Setiap aksi yang mengubah *dispatch*, rute, atau penanganan insiden **wajib menampilkan pratinjau dampak** (delta ETA, delta biaya/jarak, pelanggan terdampak) dan meminta konfirmasi eksplisit `Fleet Manager`.
- **Keterlacakan Data di UI:** Mewajibkan tampilan *timestamp*, satuan (`kg`, `°C`, `km`), sumber data, status sinkronisasi, dan catatan alasan pada setiap *approve/reject/override*.

### 4.3 Audit Kritis Kualitas Paket 9 Dokumen UI/UX
Meskipun struktur dan standar *governance*-nya sangat baik, pemeriksaan isi dan gambar menunjukkan **kelemahan serius dari sisi kedalaman spesifikasi**:
1. **Wireframe Masih Terlalu Generik (Hanya 2 Template Berulang):** Gambar wireframe di `UIUX_01` s.d. `UIUX_09` hanya membedakan judul halaman dan item sidebar aktif, sedangkan kanvas utamanya hanya mengulang 2 pola kosong (*grafik garis biru 5 titik + kotak "• Status / value / action"* atau *5 garis tabel kosong*). Tidak ada gambar peta, kartu KPI, form input, atau panel perbandingan skenario yang spesifik per menu.
2. **Isi Tabel *Boilerplate* Identik di 9 File:**
   - Kolom `Rancangan` di Tabel 3 berbunyi *"Penempatan dan perilaku komponen pada halaman [Nama Menu]"* untuk semua baris.
   - Kolom `Definisi` di Tabel 4 berbunyi *"Ditampilkan sebagai ringkasan operasional; nilai dihitung dari data aktual yang tersedia"* untuk semua KPI (padahal rumus spesifik sudah ada di Bagian 8 dokumen utama ColdChain!).
   - Kolom `Rancangan validasi` di Tabel 5 mengulang kalimat identik *"Validasi tipe data, field wajib, rentang nilai, dan konsistensi referensi sebelum disimpan/diproses"* untuk setiap field (tidak merinci aturan konkret seperti `deadline > ready_time` atau `min_temp < max_temp`).

---

## 5. Sintesis Lintas-Dokumen: Perbandingan & Konflik Integrasi

### 5.1 Matriks Perbandingan *Head-to-Head*

| Dimensi | Rancangan AgroFarm v2 | Rancangan ColdChain Revised | Implementasi Aktual `agrichain-agentic-ai` |
| :--- | :--- | :--- | :--- |
| **Cakupan Enterprise** | 1 Enterprise (`AgroFarm` saja) | 1 Enterprise (`ColdChain` saja) | **Ekosistem Penuh 5 Enterprise + Global Control Center** |
| **Jumlah & Jenis Agen** | 1 *Crop Agent* (Monitoring rule + RF Predictor) | 1 *Fleet Orchestrator* + 4–5 *Specialist Agents* | **6 Agen Heterogen** (6 ML/OR berbeda + 6 keluarga LLM berbeda) |
| **Model AI / Optimasi** | Random Forest (400 trees, 80% PI) | XGBoost (ETA) + Isolation Forest + OR-Tools **VRPTW** + Constraint Allocation | RF + LightGBM + 2D-Conv CNN + Isolation Forest + OR-Tools **CVRP** + XGBoost (Demand) + **PuLP MILP-FEFO** |
| **Peran LLM** | Tidak wajib (rule-based orchestration) | Tidak wajib (rule/policy engine) | **6 LLM Router** (*Qwen, Claude, Gemini, Llama, Mistral, GPT-4o*) sebagai modul *policy reasoning* & negosiasi |
| **Database Lokal** | SQLite (8 tabel) | PostgreSQL (8 tabel) | 5 DB terisolasi (4 SQLite mirroring PG/MySQL/TSDB + MongoDB JSON + `docker-compose.yml`) |
| **Integrasi API** | 1 pintu hanya ke `Koperasi Tani` | 4 pintu langsung ke seluruh mitra | Hub-and-Spoke + P2P *Contract Net* lewat FastAPI Gateway (`Zero-Direct-DB-Access` + 15 field firewall) |
| **Status Implementasi** | Rancangan konseptual (belum kode) | Rancangan konseptual (belum kode) | **Sudah berjalan penuh** (Streamlit 8 Tab, FastAPI, 7/7 pytest, 19.575 rows + 3.000 RGB, 3 ablasi, Bab 1–11) |

### 5.2 Lima Konflik Lintas-Dokumen yang Wajib Diselesaikan Tim
1. **Topologi Kanal AgroFarm ↔ ColdChain:** Sepakati apakah AgroFarm berkomunikasi **eksklusif lewat Koperasi Tani** (pendekatan AgroFarm v2 — lebih bersih secara rantai komando dan batas tanggung jawab) atau boleh mengirim *harvest forecast* langsung ke ColdChain (pendekatan ColdChain Bagian 3). **Rekomendasi:** Jadikan *Koperasi Tani* (atau *Global Orchestrator* via *pub-sub event* terotorisasi) sebagai perantara resmi agar tidak terjadi duplikasi/konflik volume lot.
2. **Standar Suhu Komoditas Tomat (`2–8°C` vs `7–12°C`):** Seragamkan di dokumen ColdChain & kontrak JSON `SH001` menjadi **`7–12°C`** (sesuai fisiologi tomat pascapanen dan ambang *ColdChain* di `agrichain-agentic-ai`) agar validasi sensor tidak memicu *false alarm* atau merusak mutu tomat.
3. **Penyeragaman Skema Pesan & Kunci Relasi (`lot_id` vs `block_id` vs `shipment_id`):** AgroFarm memakai `block_id` (`BLK-07`), Koperasi/Tugas memakai `lot_id` (`H001–H003`), sedangkan ColdChain memakai `shipment_id` (`SH001`) yang merujuk `lot_id`. Perlu **tabel pemetaan ID lintas enterprise** (`block_id → lot_id → shipment_id → trip_id`) dalam spesifikasi integrasi global.
4. **Sinkronisasi Diagram & Teks AgroFarm v2:** Perbarui 3 gambar di `Rancangan_Enterprise_AgroFarm_Formatted_v2.docx` agar menghapus referensi lama (`scheduler`, `negotiator`, `/harvest-plan`, `G1 cold storage`, menu ke-5 `Jadwal panen`) serta hapus `image3.png` (diagram ColdChain) yang tertinggal di dalam dokumen.
5. **Sinkronisasi Menu & Wireframe ColdChain:** Hilangkan teks bertumpuk pada wireframe Overview (`SH001`/`Status`), samakan nama menu ke-5 (`Live Tracking` vs `Alerts`), dan lengkapi kolom tabel *boilerplate* pada 9 dokumen UI/UX dengan spesifikasi validasi & definisi KPI yang konkret.

---

## 6. Rekomendasi Aksi (*Actionable Roadmap*)

### A. Quick Wins untuk Memperbaiki 12 Dokumen `.docx` (Sebelum Pengumpulan)
1. **Di `Rancangan_Enterprise_AgroFarm_Formatted_v2.docx`:**
   - Render ulang Gambar 1, 3, dan 4 agar 100% sinkron dengan teks v2 (4 menu, tanpa `negotiator/scheduler`, skenario hujan ekstrem `BLK-11` bukan `G1 cold storage`) dan buang file media ColdChain yang terselip.
2. **Di `Rancangan_ColdChain_Logistics_Fleet_Manager_Revised.docx`:**
   - Tambahkan **1 tabel bukti perubahan keputusan terukur (*Before vs After*)** untuk skenario *Temperature Excursion* atau *Cold Storage Capacity Drop* (meniru ketajaman Tabel 7.3 AgroFarm).
   - Koreksi suhu optimal tomat menjadi `7–12°C` dan perbaiki *overlap* teks pada wireframe Gambar 3.
3. **Di 9 Dokumen `ColdChain_Logistics_UIUX_Designs_All_Menus/`:**
   - Ganti kolom tabel *boilerplate* dengan definisi KPI (rumus dari Bagian 8), validasi spesifik per field (dari Tabel 6.3), dan tambahkan wireframe/mockup spesifik (atau *screenshot* aktual dari dashboard Streamlit yang sudah berjalan!).

### B. Fitur Bernilai Tinggi dari Kedua Rancangan untuk Diadopsi ke `agrichain-agentic-ai`
Jika codebase `agrichain-agentic-ai` ingin diperkaya lebih lanjut mengikuti pendalaman kedua dokumen ini:
1. **Dari AgroFarm v2 → Upgrade Modul `AGT-01`:**
   - Tambahkan fitur `NDVI`, **interval keyakinan 80% berbasis kuantil pohon RF**, grafik **Feature Importance**, aturan deteksi penyimpangan **14-day moving average ± 2σ**, *fallback* otomatis bila sensor mati ≥ 3 hari, dan skenario **Hujan Ekstrem (jendela panen maju 2 hari)**.
2. **Dari ColdChain Revised & 9 UI/UX Menu → Upgrade Modul `AGT-04`:**
   - Tingkatkan solver **OR-Tools CVRP → VRPTW** (*Time Windows* & `late_penalty`), tambahkan **XGBoost ETA Predictor** untuk *Live Tracking*, tambahkan **CRUD Armada/Shipments** sederhana di tab ColdChain, serta terapkan **5 *UI States*** (terutama indikator *stale/fresh timestamp* & pratinjau delta dampak sebelum tombol *Approve*).
