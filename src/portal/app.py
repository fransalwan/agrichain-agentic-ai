"""AgriChain stakeholder portal — enterprise-style UI for the five partner companies.

Run (from the repository root, API must be running on port 8000):
    python -m streamlit run src/portal/app.py --server.port 8502
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from src.portal import components as ui
from src.portal import core
from src.portal import pages_common as pc
from src.portal import pages_enterprise as pe
from src.portal.flow_diagram import flow_login

ASSETS = Path(__file__).parent / "assets"

st.set_page_config(page_title="AgriChain", page_icon=str(ASSETS / "icon.svg"), layout="wide")
st.logo(str(ASSETS / "logo.svg"), icon_image=str(ASSETS / "icon.svg"), size="large")
core.init_session()
with st.spinner("Menyiapkan layanan AgriChain…"):
    core.ensure_api()

if "_toast" in st.session_state:
    msg, icon = st.session_state.pop("_toast")
    st.toast(msg, icon=icon)


# ---------------------------------------------------------------------------
# Sign-in
# ---------------------------------------------------------------------------
def _sign_in(key: str) -> None:
    st.session_state["role"] = key
    st.session_state["scenario"] = "NORMAL"
    core.clear_cycles()


def sign_in_page() -> None:
    _, mid, _ = st.columns([1, 10, 1])
    with mid:
        st.badge("Portal mitra rantai pasok tomat", icon=":material/eco:", color="primary")
        st.title("Satu portal, dari kebun hingga rak toko")
        st.markdown("Lima mitra bekerja dalam satu alur yang dikoordinasikan agen AI. "
                    "**Pilih peran Anda di bawah** untuk masuk ke ruang kerja Anda.")
        with st.container(horizontal=True, gap="medium"):
            st.markdown(":material/sync_alt: Rencana pasokan terkoordinasi otomatis")
            st.markdown(":material/verified_user: Keputusan berisiko disetujui manusia")
            st.markdown(":material/lock: Data rahasia tiap mitra tetap terlindungi")
        if not core.api_online():
            st.warning("Layanan belum siap: server API (port 8000) tidak terhubung. Jalankan server API terlebih "
                       "dahulu, lalu muat ulang halaman ini.", icon=":material/cloud_off:")
        with st.container(border=True):
            flow_login(on_login=_sign_in)
        st.caption(":material/info: Akun demo tanpa kata sandi. Hak akses data tetap diperiksa di server sesuai "
                   "peran yang dipilih.")


# ---------------------------------------------------------------------------
# Navigation per role
# ---------------------------------------------------------------------------
def _p(fn, title: str, icon: str, path: str, **kw) -> st.Page:
    return st.Page(fn, title=title, icon=icon, url_path=path, **kw)


ENTERPRISE_PAGES = {
    "agrofarm": [
        (pe.agrofarm_fields, "Lahan & panen", ":material/grass:", "lahan"),
        (pe.agrofarm_signals, "Masukan mitra", ":material/forum:", "masukan"),
    ],
    "koperasi": [
        (pe.koperasi_pricing, "Harga & penawaran", ":material/sell:", "harga"),
    ],
    "freshfood": [
        (pe.freshfood_quality, "Kontrol mutu", ":material/verified:", "mutu"),
        (pe.freshfood_schedule, "Jadwal produksi", ":material/event_note:", "produksi"),
    ],
    "coldchain": [
        (pe.coldchain_routes, "Rute pengiriman", ":material/route:", "rute"),
        (pe.coldchain_fleet, "Armada & pengiriman", ":material/local_shipping:", "armada"),
        (pe.coldchain_temperature, "Suhu & waktu tempuh", ":material/thermostat:", "suhu"),
    ],
    "supermart": [
        (pe.supermart_demand, "Permintaan & pesanan", ":material/shopping_cart:", "permintaan"),
        (pe.supermart_receiving, "Penerimaan barang", ":material/inventory_2:", "penerimaan"),
    ],
}


def build_pages(role_key: str) -> dict:
    data = _p(pc.data_page, "Data", ":material/database:", "data")
    audit = _p(pc.activity_page, "Aktivitas & audit", ":material/history:", "aktivitas")
    ui.PAGES.update({"data": data, "audit": audit})

    if role_key == "global":
        pending = (st.session_state["cycles"].get(st.session_state["scenario"], {}).get("hitl_status") == "PENDING_APPROVAL")
        home = _p(pc.global_overview, "Ringkasan", ":material/dashboard:", "ringkasan", default=True)
        approvals = _p(pc.approvals, "Persetujuan · 1" if pending else "Persetujuan", ":material/approval:", "persetujuan")
        ui.PAGES.update({"home": home, "approvals": approvals})
        partners = []
        for ent, pages in ENTERPRISE_PAGES.items():
            name = ui.ENTERPRISE_NAMES[ent][0]
            for fn, title, icon, path in pages:
                partners.append(_p(fn, f"{name} · {title}", icon, f"{ent}-{path}"))
        return {"": [home, approvals], "Operasional mitra": partners, "Lainnya": [data, audit]}

    home = _p(lambda: pc.enterprise_overview(role_key), "Ringkasan", ":material/dashboard:", "ringkasan", default=True)
    ui.PAGES["home"] = home
    ops = [_p(fn, title, icon, path) for fn, title, icon, path in ENTERPRISE_PAGES[role_key]]
    return {"": [home, *ops], "Lainnya": [data, audit]}


def _sign_out() -> None:
    for k in list(st.session_state.keys()):
        del st.session_state[k]


def _set_scenario() -> None:
    st.session_state["scenario"] = st.session_state["_scenario_widget"]


def sidebar() -> None:
    r = core.role()
    # Widget state is reset on page switches, so the chosen scenario lives in its own key.
    st.session_state["_scenario_widget"] = st.session_state["scenario"]
    with st.sidebar:
        st.selectbox("Kondisi simulasi", list(core.SCENARIOS), format_func=lambda k: core.SCENARIOS[k][0],
                     key="_scenario_widget", on_change=_set_scenario,
                     help="Pilih kondisi operasional untuk melihat bagaimana agen menyesuaikan rencana.")
        if st.button("Perbarui data", icon=":material/refresh:", width="stretch"):
            core.clear_cycles()
            core.api_online.clear()
            core._cached_call.clear()
            st.rerun()
        online = core.api_online()
        st.badge("Terhubung ke server" if online else "Server tidak terhubung",
                 color="green" if online else "red", icon=":material/cloud_done:" if online else ":material/cloud_off:")
        st.space("medium")
        with st.container(border=True):
            st.markdown(f"{r['icon']} **{r['org']}**")
            st.caption(r["title"])
            st.button("Keluar", icon=":material/logout:", on_click=_sign_out, width="stretch", type="tertiary")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if st.session_state["role"] is None:
    st.navigation([st.Page(sign_in_page, title="Masuk", icon=":material/login:", url_path="masuk")],
                  position="hidden").run()
else:
    def _pending() -> bool:
        cyc = st.session_state["cycles"].get(st.session_state["scenario"], {})
        return core.role_key() == "global" and cyc.get("hitl_status") == "PENDING_APPROVAL"

    pending_before = _pending()
    page = st.navigation(build_pages(core.role_key()), position="sidebar", expanded=True)
    sidebar()

    # A fresh placeholder replaces the previous page wholesale, so content from the
    # last page never lingers (greyed out) while slow data for this page loads.
    with st.empty().container():
        with st.container(horizontal=True, vertical_alignment="bottom"):
            st.title(page.title.split(" · 1")[0])
            scen = st.session_state["scenario"]
            if scen != "NORMAL":
                st.badge(f"Simulasi: {core.SCENARIOS[scen][0]}", color="orange", icon=":material/science:",
                         help=core.SCENARIOS[scen][1])
        ui.model_tags(page.url_path)
        page.run()
    # Refresh the menu once if this run discovered (or cleared) a pending approval.
    if _pending() != pending_before:
        st.rerun()
