---
title: AgriChain Portal
emoji: 🍅
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
short_description: Portal stakeholder rantai pasok tomat multi-agen AI
---

# AgriChain — Portal Stakeholder

Portal koordinasi rantai pasok tomat untuk lima mitra (AgroFarm, Koperasi Tani, FreshFood,
ColdChain, SuperMart) dan Pusat Kendali, dengan agen AI per mitra.

- Pilih peran pada diagram di halaman masuk (akun demo, tanpa kata sandi).
- Container menjalankan FastAPI (internal, port 8000) dan portal Streamlit (port 7860).
- Model bahasa (LLM) berjalan dalam mode simulasi secara default. Untuk mode live, isi
  `GROQ_API_KEY` dan `GEMINI_API_KEY` sebagai *Secrets* di pengaturan Space lalu set
  `LLM_EXECUTION_MODE=LIVE`.
