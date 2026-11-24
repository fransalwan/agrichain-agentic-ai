"""Reusable UI building blocks for the stakeholder portal."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import altair as alt
import pandas as pd
import streamlit as st

from src.portal import core

# Page registry, filled by app.py on every run so pages can link to each other.
PAGES: Dict[str, Any] = {}

ENTERPRISE_NAMES = {
    "agrofarm": ("AgroFarm", ":material/agriculture:", "Kebun"),
    "koperasi": ("Koperasi Tani", ":material/handshake:", "Agregator & harga"),
    "freshfood": ("FreshFood", ":material/factory:", "Pengolahan & mutu"),
    "coldchain": ("ColdChain", ":material/local_shipping:", "Logistik dingin"),
    "supermart": ("SuperMart", ":material/storefront:", "Ritel"),
}


@st.fragment(run_every="0.3s")
def _continue_loading() -> None:
    # First (inline) call just arms; the timed call after this run finishes triggers the real load.
    if st.session_state.get("_load_armed"):
        st.session_state["_load_armed"] = False
        st.rerun(scope="app")
    st.session_state["_load_armed"] = True


# ---------------------------------------------------------------------------
# Models / algorithms behind each page (shown as tags under the page title)
# ---------------------------------------------------------------------------
_KIND = {
    "ml": ("ML", "blue", ":material/model_training:"),
    "llm": ("LLM", "orange", ":material/smart_toy:"),
    "opt": ("Optimasi", "violet", ":material/tune:"),
    "rule": ("Aturan", "gray", ":material/rule:"),
}
_LLM_NOTE = " Berjalan live bila API key Groq/Gemini/OpenRouter diisi di .env; jika tidak, memakai mode simulasi."

MODEL_TAGS: Dict[str, List[Tuple[str, str, str]]] = {
    # (kind, short label shown on the badge, full name + explanation shown on hover)
    "ringkasan": [
        ("opt", "LangGraph", "Orkestrasi LangGraph: alur kerja 7 langkah antar-agen yang menyusun rencana setiap siklus."),
        ("opt", "MILP", "Mixed-Integer Linear Programming (PuLP + CBC): membagi tomat ke tiap mitra dengan laba maksimal dan susut minimal."),
        ("rule", "Jain's Index", "Jain's Fairness Index: mengukur seberapa merata keuntungan antar-mitra (0–1)."),
    ],
    "persetujuan": [
        ("rule", "Gerbang risiko", "Aturan NIST AI RMF: keputusan wajib disetujui manusia bila melewati ambang (misalnya kapasitas turun > 40%)."),
        ("opt", "MILP", "Mixed-Integer Linear Programming: membandingkan rencana dengan dan tanpa penyesuaian."),
    ],
    "lahan": [
        ("ml", "Random Forest", "Random Forest Regression: 250 pohon keputusan memperkirakan hasil panen; rentang 80% dari sebaran prediksi antar-pohon."),
        ("rule", "NDVI ±2σ", "Blok ditandai bila NDVI hari ini di bawah rata-rata 14 hari dikurangi 2× simpangan baku, atau hujan > 90 mm."),
        ("rule", "Fallback historis", "Rata-rata panen historis dipakai bila sensor lahan mati ≥ 3 hari."),
    ],
    "masukan": [
        ("rule", "Umpan balik mutu", "Aturan: FreshFood mengirim temuan bila cacat ≥ 12% atau uji keamanan gagal."),
        ("ml", "XGBoost", "XGBoost Regression: perkiraan permintaan 7 hari dari SuperMart."),
    ],
    "harga": [
        ("ml", "LightGBM", "LightGBM Regression: memperkirakan harga pasar per grade."),
        ("rule", "Contract Net", "Contract Net Protocol: lelang antar-agen dengan batas harga minimum rahasia koperasi."),
        ("llm", "LLM Groq", "Groq GPT-OSS 20B: penalaran agen koperasi saat negosiasi." + _LLM_NOTE),
    ],
    "mutu": [
        ("rule", "Keamanan pangan", "Aturan hard-block: ambang pH, residu pestisida, mikroba, dan cacat; satu pelanggaran langsung memblokir lot."),
        ("ml", "CNN + MLP", "Fitur konvolusi 2D (filter tetap Sobel, Laplacian, blur) + jaringan saraf MLP 128-64 untuk menilai grade dari foto."),
        ("llm", "LLM Gemini", "Gemini 3.5 Flash-Lite: penalaran agen FreshFood." + _LLM_NOTE),
    ],
    "produksi": [
        ("opt", "FEFO", "First-Expired, First-Out (greedy): lot dengan umur simpan terpendek diproses lebih dulu."),
    ],
    "rute": [
        ("opt", "OR-Tools VRPTW", "Vehicle Routing Problem with Time Windows (Google OR-Tools): Path Cheapest Arc + Guided Local Search."),
        ("ml", "XGBoost", "XGBoost Regression: memperkirakan lama perjalanan (ETA) tiap rute."),
    ],
    "armada": [
        ("rule", "Validasi data", "Tanpa model: input dicek terhadap aturan suhu 7–12 °C dan format jadwal."),
    ],
    "suhu": [
        ("ml", "Isolation Forest", "Isolation Forest: deteksi anomali suhu gudang dingin tanpa label."),
        ("ml", "XGBoost", "XGBoost Regression: memperkirakan waktu tempuh dari jarak, lalu lintas, singgah, dan cuaca."),
    ],
    "permintaan": [
        ("ml", "XGBoost", "XGBoost Regression: memperkirakan permintaan tomat 7 hari ke depan."),
        ("opt", "Newsvendor", "Model Newsvendor: jumlah pesan optimal yang menyeimbangkan risiko kehabisan stok dan risiko busuk."),
    ],
    "penerimaan": [
        ("rule", "Aturan SLA", "Barang diterima bila suhu 7–12 °C dan tiba sebelum batas waktu; jika tidak, klaim atau ditolak."),
    ],
    "data": [
        ("rule", "RBAC", "Redaksi berbasis peran: server menyembunyikan kolom rahasia milik mitra lain."),
    ],
    "aktivitas": [
        ("opt", "LangGraph", "Orkestrasi LangGraph: jejak 7 langkah keputusan antar-agen."),
        ("rule", "SHA-256", "Rantai hash SHA-256: perubahan tidak sah pada log audit terdeteksi."),
        ("llm", "LLM hibrida", "Groq + Gemini + OpenRouter, dipakai agen Koperasi, FreshFood, dan Pusat Kendali." + _LLM_NOTE),
    ],
}


def model_tags(url_path: str) -> None:
    """Show which ML / LLM / optimisation / rule methods power the current page."""
    tags = MODEL_TAGS.get(url_path.split("-")[-1])
    if not tags:
        return
    with st.container(horizontal=True, gap="small", vertical_alignment="center"):
        st.caption("Teknologi:", width="content")
        for kind, name, desc in tags:
            label, color, icon = _KIND[kind]
            st.badge(name, color=color, icon=icon, help=f"**{label}** · {desc}")


def require_cycle() -> Dict[str, Any]:
    """Load the current planning cycle or show a friendly error and stop the page.

    When data is not loaded yet, this run only draws a loading skeleton and finishes, so the
    previous page is cleared right away; a follow-up run then performs the slow request.
    """
    if not core.cycle_loaded() and not st.session_state.get("_loading_pass"):
        st.session_state["_loading_pass"] = True
        st.session_state["_load_armed"] = False
        st.caption(":material/hourglass_top: Agen sedang menyusun rencana rantai pasok…")
        with st.container(horizontal=True):
            for _ in range(4):
                st.container(border=True, height=110)
        st.container(border=True, height=280)
        _continue_loading()
        st.stop()
    st.session_state["_loading_pass"] = False
    state = core.get_cycle()
    if state is None:
        with st.container(border=True):
            st.error("Data rencana belum bisa dimuat.", icon=":material/cloud_off:")
            st.caption(st.session_state.get("cycle_error", "Terjadi kesalahan yang tidak diketahui."))
            if st.button("Coba lagi", icon=":material/refresh:", type="primary"):
                core.clear_cycles()
                st.rerun()
        st.stop()
    return state


def go_to(page_key: str, label: str, icon: str = ":material/arrow_forward:", primary: bool = False) -> None:
    page = PAGES.get(page_key)
    if page is not None:
        if st.button(label, icon=icon, type="primary" if primary else "secondary", key=f"goto_{page_key}_{label}"):
            st.switch_page(page)


def section(title: str, caption: Optional[str] = None, icon: Optional[str] = None) -> None:
    st.subheader(title, icon=icon)
    if caption:
        st.caption(caption)


# Default work page per partner (url path of its first operational page).
PARTNER_HOME = {"agrofarm": "lahan", "koperasi": "harga", "freshfood": "mutu", "coldchain": "rute", "supermart": "permintaan"}


def can_open(ent: str) -> bool:
    """The Control Center can open every partner; a partner only its own workspace."""
    return core.role_key() in ("global", ent)


def open_partner(ent: str, path: Optional[str] = None) -> None:
    """Navigate to a partner's work page (inside 'Operasional mitra' for the Control Center)."""
    path = path or PARTNER_HOME[ent]
    if core.role_key() == "global":
        st.session_state["mitra_ent"] = ent
        st.session_state.setdefault("mitra_sub", {})[ent] = path
        st.switch_page(PAGES["mitra"])
    elif path in PAGES:
        st.switch_page(PAGES[path])


def partner_strip(state: Dict[str, Any], highlight: Optional[str] = None) -> None:
    """One-glance status of the five partners in supply-chain order, each linking to its detail."""
    health = core.enterprise_health(state)
    with st.container(horizontal=True, gap="small"):
        for ent in core.ENTERPRISES:
            name, icon, sub = ENTERPRISE_NAMES[ent]
            level, text = health[ent]
            label, color, licon = core.LEVEL_STYLE[level]
            with st.container(border=True, width="stretch"):
                st.markdown(f"{icon} **{name}**")
                st.caption(f"{sub} · **posisi Anda**" if ent == highlight else sub)
                st.badge(label, color=color, icon=licon)
                st.caption(text)
                if can_open(ent) and st.button("Lihat detail", key=f"strip_{ent}", type="tertiary",
                                               icon=":material/arrow_forward:", icon_position="right"):
                    open_partner(ent)


def attention_list(items: List[tuple]) -> None:
    """items: (level, text) or (level, text, (enterprise, page_path)) with level in ok|warn|alert|info."""
    if not items:
        st.success("Tidak ada hal yang perlu ditindaklanjuti saat ini.", icon=":material/task_alt:")
        return
    icons = {
        "alert": ":red[:material/error:]",
        "warn": ":orange[:material/warning:]",
        "info": ":blue[:material/info:]",
        "ok": ":green[:material/check_circle:]",
    }
    with st.container(border=True):
        for i, item in enumerate(items):
            level, text = item[0], item[1]
            target = item[2] if len(item) > 2 else None
            with st.container(horizontal=True, vertical_alignment="center"):
                st.markdown(f"{icons.get(level, '')} {text}")
                if target and can_open(target[0]) and st.button(
                        "Lihat", key=f"att_{i}", type="tertiary", icon=":material/arrow_forward:",
                        icon_position="right", width="content"):
                    open_partner(*target)


WELCOME_STEPS = {
    "global": ["Cek **Ringkasan**: kondisi kelima mitra dan angka utama siklus ini.",
               "Buka **Persetujuan** bila ada rencana berisiko yang menunggu keputusan Anda.",
               "Gunakan **Operasional mitra** untuk melihat detail tiap mitra."],
    "agrofarm": ["Lihat **Perlu perhatian** untuk blok lahan yang bermasalah.",
                 "Buka **Lahan & panen** untuk memperkirakan hasil dan jadwal panen.",
                 "Cek **Masukan mitra** untuk umpan balik mutu dan perkiraan permintaan."],
    "koperasi": ["Lihat **Perlu perhatian** dan status mitra di Ringkasan.",
                 "Buka **Harga & penawaran** untuk harga pasar per grade.",
                 "Nilai tawaran pembeli terhadap harga minimum koperasi."],
    "freshfood": ["Lihat **Perlu perhatian** untuk lot yang diblokir atau bermasalah.",
                  "Buka **Kontrol mutu** untuk menjalankan inspeksi keamanan pangan.",
                  "Atur kapasitas lini dan lembur di **Jadwal produksi**."],
    "coldchain": ["Lihat **Perlu perhatian** dan kapasitas gudang dingin.",
                  "Buka **Rute pengiriman** untuk rencana rute truk.",
                  "Pantau **Suhu & waktu tempuh** agar tetap 7–12 °C."],
    "supermart": ["Lihat **Perlu perhatian** untuk penerimaan barang bermasalah.",
                  "Buka **Permintaan & pesanan** untuk perkiraan 7 hari dan pesanan pembelian.",
                  "Periksa kedatangan truk di **Penerimaan barang**."],
}


def welcome_card() -> None:
    """Dismissible 3-step orientation for first-time users of each role."""
    if st.session_state.get("welcome_closed"):
        return
    with st.container(border=True):
        with st.container(horizontal=True, vertical_alignment="center"):
            st.markdown(f":material/waving_hand: **Mulai di sini, {core.role()['title'].lower()}**")
            if st.button("Tutup", key="welcome_close", type="tertiary", icon=":material/close:", width="content"):
                st.session_state["welcome_closed"] = True
                st.rerun()
        for i, step in enumerate(WELCOME_STEPS[core.role_key()], 1):
            st.markdown(f"{i}. {step}")


def hitl_notice(state: Dict[str, Any]) -> None:
    """Small banner for non-global roles when the cycle awaits central approval."""
    status = state.get("hitl_status")
    if status == "PENDING_APPROVAL":
        st.info("Rencana siklus ini sedang menunggu persetujuan pusat kendali. "
                "Angka di bawah masih berupa usulan.", icon=":material/pending_actions:")
    elif status == "HUMAN_REJECTED":
        st.warning("Rencana siklus ini ditolak pusat kendali dan akan disusun ulang.", icon=":material/cancel:")


def status_badge(status: str) -> None:
    label, color, icon = core.HITL_STATUS.get(status, (status, "gray", None))
    st.badge(label, color=color, icon=icon)


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
def allocation_frame(state: Dict[str, Any]) -> pd.DataFrame:
    rows: Dict[str, float] = {}
    for a in state["milp_result"]["allocations"]:
        if a["qty_kg"] > 0:
            lbl = core.channel_label(a["channel"])
            rows[lbl] = rows.get(lbl, 0.0) + float(a["qty_kg"])
    loss = float(state["milp_result"].get("total_loss_kg", 0))
    if loss > 0.5:
        rows["Terbuang / diblokir"] = loss
    return pd.DataFrame({"Tujuan": list(rows.keys()), "Volume (kg)": list(rows.values())})


def allocation_chart(state: Dict[str, Any]) -> None:
    df = allocation_frame(state)
    if df.empty:
        st.caption("Belum ada alokasi pada siklus ini.")
        return
    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=4)
        .encode(
            x=alt.X("Volume (kg):Q", title="Volume (kg)"),
            y=alt.Y("Tujuan:N", sort="-x", title=None, axis=alt.Axis(labelLimit=220)),
            color=alt.condition(alt.datum.Tujuan == "Terbuang / diblokir", alt.value("#DC2626"), alt.value("#0F766E")),
            tooltip=["Tujuan", alt.Tooltip("Volume (kg):Q", format=",.0f")],
        )
        .properties(height=alt.Step(34))
    )
    st.altair_chart(chart, width="stretch")


def comparison_chart(before: Dict[str, Any], after: Dict[str, Any]) -> None:
    a = allocation_frame(before).assign(Rencana="Tanpa penyesuaian")
    b = allocation_frame(after).assign(Rencana="Dengan penyesuaian")
    df = pd.concat([a, b])
    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=3)
        .encode(
            y=alt.Y("Tujuan:N", title=None, axis=alt.Axis(labelLimit=220)),
            yOffset=alt.YOffset("Rencana:N", sort=["Tanpa penyesuaian", "Dengan penyesuaian"]),
            x=alt.X("Volume (kg):Q"),
            color=alt.Color("Rencana:N", scale=alt.Scale(domain=["Tanpa penyesuaian", "Dengan penyesuaian"],
                                                          range=["#94A3B8", "#0F766E"]),
                            legend=alt.Legend(orient="bottom", title=None)),
            tooltip=["Rencana", "Tujuan", alt.Tooltip("Volume (kg):Q", format=",.0f")],
        )
    )
    st.altair_chart(chart, width="stretch")


def demand_chart(rows: List[Dict[str, Any]]) -> None:
    df = pd.DataFrame(rows)
    if df.empty:
        st.caption("Belum ada proyeksi permintaan.")
        return
    df["Hari"] = df["horizon"] + " · " + df["day_name"]
    bars = alt.Chart(df).mark_bar(color="#99D5CF", cornerRadiusEnd=3).encode(
        x=alt.X("Hari:N", sort=None, title=None),
        y=alt.Y("forecast_demand_kg:Q", title="kg"),
        tooltip=[alt.Tooltip("Hari:N"), alt.Tooltip("forecast_demand_kg:Q", title="Perkiraan permintaan", format=",.0f"),
                 alt.Tooltip("recommended_po_kg:Q", title="Saran jumlah pesan", format=",.0f")],
    )
    line = alt.Chart(df).mark_line(color="#0F766E", point=True, strokeWidth=2.5).encode(
        x=alt.X("Hari:N", sort=None), y="recommended_po_kg:Q",
    )
    st.altair_chart(bars + line, width="stretch")
    st.caption("Batang: perkiraan permintaan · Garis: saran jumlah pesan")
