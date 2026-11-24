"""Interactive supply-chain flow used as the sign-in screen.

Wide screens get an animated SVG flow (Control Center on top, five partners left→right,
goods and information flows between them). Narrow screens get a stacked, numbered list with
the same roles, so every "Masuk" button stays reachable without sideways scrolling.
Clicks are sent back to Python through a Custom Component v2 trigger.
"""
from __future__ import annotations

from html import escape
from typing import Callable, Optional

import streamlit as st

TEAL = "#0F766E"
GREEN = "#15803D"
BLUE = "#2563EB"
INK = "#1E293B"
MUTED = "#5B6B7F"

# (role key, emoji, name, role title, AI capability, one-line description)
NODES = [
    ("agrofarm", "🌱", "AgroFarm", "Manajer kebun", "Prediksi hasil panen",
     "Memantau kondisi lahan dan memperkirakan hasil serta jadwal panen."),
    ("koperasi", "🤝", "Koperasi Tani", "Manajer koperasi", "Lelang harga otomatis",
     "Mengumpulkan panen petani dan menegosiasikan harga dengan pembeli."),
    ("freshfood", "🏭", "FreshFood", "Manajer mutu & produksi", "Cek mutu via kamera",
     "Memeriksa mutu dan keamanan pangan, lalu menjadwalkan produksi."),
    ("coldchain", "🚚", "ColdChain", "Manajer armada", "Optimasi rute 7–12 °C",
     "Mengatur rute truk berpendingin dan menjaga suhu 7–12 °C."),
    ("supermart", "🛒", "SuperMart", "Manajer pembelian", "Prediksi permintaan",
     "Memperkirakan permintaan dan menerbitkan pesanan pembelian."),
]
HUB = ("global", "Pusat Kendali AgriChain", "Operator pusat kendali",
       "Agen AI menyusun rencana untuk kelima mitra; keputusan berisiko disetujui manusia.")
INFO_FLOWS = [
    ("FreshFood → AgroFarm", "umpan balik mutu panen"),
    ("FreshFood → ColdChain", "jadwal terima barang"),
    ("SuperMart → AgroFarm & Koperasi", "perkiraan permintaan 7 hari"),
]

# ---------------------------------------------------------------------------
# Wide layout (SVG)
# ---------------------------------------------------------------------------
W, H = 168, 158
Y = 150
CX = [100, 300, 500, 700, 900]
BOTTOM = Y + H
LANE1, LANE2 = BOTTOM + 38, BOTTOM + 82


def _svg_button(role: str, x: float, y: float, w: float, aria: str, light: bool = False) -> str:
    fill, text = ("#FFFFFF", TEAL) if light else (TEAL, "#FFFFFF")
    return f"""
      <g class="ac-btn" data-role="{role}" tabindex="0" role="button" aria-label="{escape(aria)}">
        <rect x="{x}" y="{y}" width="{w}" height="34" rx="9" fill="{fill}"/>
        <text x="{x + w / 2}" y="{y + 22}" font-size="14" font-weight="700" fill="{text}" text-anchor="middle">Masuk</text>
      </g>"""


def _svg_node(i: int) -> str:
    role, emoji, name, title, ai, desc = NODES[i]
    x = CX[i] - W // 2
    return f"""
    <g class="ac-node"><title>{escape(name)}: {escape(desc)}</title>
      <rect class="ac-card" x="{x}" y="{Y}" width="{W}" height="{H}" rx="14" fill="#FFFFFF" stroke="#D5DEE7" stroke-width="1.5"/>
      <circle cx="{x + W - 18}" cy="{Y + 18}" r="10" fill="#F1F5F9"/>
      <text x="{x + W - 18}" y="{Y + 22}" font-size="11" font-weight="700" fill="{MUTED}" text-anchor="middle">{i + 1}</text>
      <text x="{x + 14}" y="{Y + 34}" font-size="22">{emoji}</text>
      <text x="{x + 14}" y="{Y + 62}" font-size="16" font-weight="700" fill="{INK}">{escape(name)}</text>
      <text x="{x + 14}" y="{Y + 81}" font-size="12.5" fill="{MUTED}">{escape(title)}</text>
      <rect x="{x + 12}" y="{Y + 92}" width="{W - 24}" height="20" rx="10" fill="#E6F6F3"/>
      <text x="{CX[i]}" y="{Y + 106}" font-size="11" font-weight="600" fill="{TEAL}" text-anchor="middle">{escape(ai)}</text>
      {_svg_button(role, x + 12, Y + 116, W - 24, f"Masuk sebagai {title}, {name}")}
    </g>"""


def _svg_goods(i: int) -> str:
    x1, x2, y = CX[i] + W // 2 + 3, CX[i + 1] - W // 2 - 6, Y + 70
    return (f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="#BBF7D0" stroke-width="5" stroke-linecap="round"/>'
            f'<line class="ac-goods" x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{GREEN}" stroke-width="5" '
            f'stroke-linecap="round" marker-end="url(#ac-ah-g)"/>')


def _svg_hub_link(i: int) -> str:
    return (f'<path class="ac-hub" d="M500 94 C500 126, {CX[i]} 118, {CX[i]} {Y - 2}" fill="none" '
            f'stroke="{TEAL}" stroke-width="1.6" stroke-opacity="0.7"/>')


def _svg_info(path: str, label: str, lx: float, ly: float, tip: str) -> str:
    text = (f'<text x="{lx}" y="{ly}" font-size="12.5" fill="{BLUE}" text-anchor="middle" font-weight="600" '
            f'paint-order="stroke" stroke="#FFFFFF" stroke-width="5">{label}</text>') if label else ""
    return (f'<g><title>{escape(tip)}</title><path class="ac-info" d="{path}" fill="none" stroke="{BLUE}" '
            f'stroke-width="2" marker-end="url(#ac-ah-b)"/>{text}</g>')


def _svg() -> str:
    demand = "SuperMart membagikan perkiraan permintaan agar AgroFarm dan Koperasi merencanakan panen dan harga."
    info = "".join([
        _svg_info(f"M480 {BOTTOM} V{LANE1} H120 V{BOTTOM + 8}", "umpan balik mutu", 400, LANE1 - 6,
                  "FreshFood mengirim temuan mutu (cacat, residu) ke AgroFarm agar cara panen diperbaiki."),
        _svg_info(f"M520 {BOTTOM} V{LANE1} H680 V{BOTTOM + 8}", "jadwal terima barang", 600, LANE1 - 6,
                  "FreshFood membagikan jam buka dok bongkar agar rute ColdChain tiba tepat waktu."),
        _svg_info(f"M900 {BOTTOM} V{LANE2} H80 V{BOTTOM + 8}", "perkiraan permintaan 7 hari", 500, LANE2 - 6, demand),
        _svg_info(f"M300 {LANE2} V{BOTTOM + 8}", "", 0, 0, demand),
    ])
    ly = LANE2 + 40
    role, hub_name, hub_title, hub_desc = HUB
    return f"""
<svg class="ac-svg" viewBox="0 0 1000 {ly + 12}" role="group" aria-label="Alur rantai pasok tomat dan pilihan peran">
  <defs>
    <marker id="ac-ah-g" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="4" markerHeight="4" orient="auto">
      <path d="M0 0 L10 5 L0 10 z" fill="{GREEN}"/></marker>
    <marker id="ac-ah-b" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M0 0 L10 5 L0 10 z" fill="{BLUE}"/></marker>
  </defs>
  {''.join(_svg_hub_link(i) for i in range(5))}
  <g class="ac-node"><title>{escape(hub_desc)}</title>
    <rect class="ac-card" x="290" y="8" width="420" height="86" rx="16" fill="{TEAL}"/>
    <text x="314" y="42" font-size="17" font-weight="700" fill="#FFFFFF">{hub_name}</text>
    <text x="314" y="64" font-size="12.5" fill="#CCFBF1">{hub_title}</text>
    <text x="314" y="81" font-size="12.5" fill="#CCFBF1">Koordinasi &amp; persetujuan</text>
    {_svg_button(role, 590, 34, 100, "Masuk sebagai operator pusat kendali", light=True)}
  </g>
  {''.join(_svg_goods(i) for i in range(4))}
  {''.join(_svg_node(i) for i in range(5))}
  {info}
  <g font-size="12.5" fill="{MUTED}">
    <line x1="215" y1="{ly}" x2="247" y2="{ly}" stroke="{GREEN}" stroke-width="5" stroke-linecap="round"/>
    <text x="255" y="{ly + 4}">Aliran tomat</text>
    <line x1="380" y1="{ly}" x2="412" y2="{ly}" stroke="{BLUE}" stroke-width="2" stroke-dasharray="6 5"/>
    <text x="420" y="{ly + 4}">Aliran informasi antar-mitra</text>
    <line x1="630" y1="{ly}" x2="662" y2="{ly}" stroke="{TEAL}" stroke-width="1.6" stroke-dasharray="2 5"/>
    <text x="670" y="{ly + 4}">Koordinasi pusat</text>
  </g>
</svg>"""


# ---------------------------------------------------------------------------
# Narrow layout (stacked list)
# ---------------------------------------------------------------------------
def _stack() -> str:
    role, hub_name, hub_title, hub_desc = HUB
    items = [f"""
  <div class="m-hub">
    <div class="m-text"><b>{hub_name}</b><span>{hub_title}</span><p>{escape(hub_desc)}</p></div>
    <button type="button" class="m-btn light" data-role="{role}" aria-label="Masuk sebagai operator pusat kendali">Masuk</button>
  </div>
  <div class="m-sep">mengoordinasikan kelima mitra di bawah</div>"""]
    for i, (role, emoji, name, title, ai, desc) in enumerate(NODES):
        if i:
            items.append('<div class="m-flow"><span class="m-arrow">↓</span> aliran tomat</div>')
        items.append(f"""
  <div class="m-card">
    <div class="m-step">{i + 1}</div>
    <div class="m-text"><b>{emoji} {escape(name)}</b><span>{escape(title)} · <em>{escape(ai)}</em></span><p>{escape(desc)}</p></div>
    <button type="button" class="m-btn" data-role="{role}" aria-label="Masuk sebagai {escape(title)}, {escape(name)}">Masuk</button>
  </div>""")
    flows = "".join(f"<li><b>{a}</b>: {b}</li>" for a, b in INFO_FLOWS)
    items.append(f'<div class="m-info"><b>Informasi yang dibagikan antar-mitra</b><ul>{flows}</ul></div>')
    return f'<div class="ac-stack">{"".join(items)}</div>'


_CSS = f"""
:host {{ display: block; }}
.ac-root {{ container-type: inline-size; font-family: var(--st-font, Inter), 'Segoe UI', Arial, sans-serif; color: {INK}; }}
.ac-svg {{ width: 100%; height: auto; display: block; }}
.ac-stack {{ display: none; }}

/* Motion: subtle, and off for users who ask for reduced motion */
.ac-goods {{ stroke-dasharray: 9 7; animation: ac-move 0.9s linear infinite; }}
.ac-info {{ stroke-dasharray: 6 5; animation: ac-move 1.4s linear infinite; }}
.ac-hub {{ stroke-dasharray: 2 5; animation: ac-move 1.8s linear infinite reverse; }}
@keyframes ac-move {{ to {{ stroke-dashoffset: -32; }} }}
@media (prefers-reduced-motion: reduce) {{ .ac-goods, .ac-info, .ac-hub {{ animation: none; }} }}

.ac-card {{ transition: stroke .15s, filter .15s; }}
.ac-node:hover .ac-card {{ stroke: {TEAL}; stroke-width: 2.2; filter: drop-shadow(0 6px 14px rgba(15,118,110,.16)); }}
.ac-btn {{ cursor: pointer; outline: none; }}
.ac-btn rect {{ transition: filter .15s; }}
.ac-btn:hover rect {{ filter: brightness(1.12) drop-shadow(0 2px 4px rgba(0,0,0,.18)); }}
.ac-btn:focus-visible rect {{ stroke: #F59E0B; stroke-width: 3; }}
.ac-busy {{ opacity: .55; pointer-events: none; }}

/* Narrow screens: numbered stack instead of the wide diagram */
@container (max-width: 680px) {{
  .ac-svg {{ display: none; }}
  .ac-stack {{ display: flex; flex-direction: column; gap: 8px; }}
}}
.m-hub, .m-card {{ display: flex; align-items: center; gap: 12px; padding: 14px; border-radius: 14px; }}
.m-hub {{ background: {TEAL}; color: #FFFFFF; }}
.m-hub .m-text span, .m-hub .m-text p {{ color: #D9FBF4; }}
.m-card {{ background: #FFFFFF; border: 1.5px solid #D5DEE7; }}
.m-text {{ flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }}
.m-text b {{ font-size: 15px; }}
.m-text span {{ font-size: 12.5px; color: {MUTED}; }}
.m-text em {{ font-style: normal; color: {TEAL}; font-weight: 600; }}
.m-text p {{ margin: 4px 0 0; font-size: 13px; line-height: 1.4; color: {MUTED}; }}
.m-step {{ flex: none; width: 26px; height: 26px; border-radius: 50%; background: #F1F5F9; color: {MUTED};
          font-size: 12px; font-weight: 700; display: grid; place-items: center; }}
.m-btn {{ flex: none; min-width: 84px; min-height: 40px; border: 0; border-radius: 10px; background: {TEAL};
         color: #FFFFFF; font-family: inherit; font-size: 14px; font-weight: 700; cursor: pointer; }}
.m-btn.light {{ background: #FFFFFF; color: {TEAL}; }}
.m-btn:hover {{ filter: brightness(1.1); }}
.m-btn:focus-visible {{ outline: 3px solid #F59E0B; outline-offset: 2px; }}
.m-sep, .m-flow {{ font-size: 12px; color: {MUTED}; text-align: center; }}
.m-flow {{ color: {GREEN}; font-weight: 600; }}
.m-arrow {{ font-size: 15px; }}
.m-info {{ margin-top: 6px; padding: 12px 14px; border-radius: 12px; background: #EFF6FF; font-size: 13px; }}
.m-info b {{ color: {BLUE}; }}
.m-info ul {{ margin: 6px 0 0; padding-left: 18px; color: {INK}; }}
.m-info li b {{ color: {INK}; }}
"""

_JS = """
export default function (component) {
  const { parentElement, setTriggerValue } = component
  const targets = parentElement.querySelectorAll("[data-role]")
  const go = (el) => {
    targets.forEach((t) => t.classList.add("ac-busy"))
    setTriggerValue("login", el.dataset.role)
  }
  const onClick = (e) => go(e.currentTarget)
  const onKey = (e) => {
    // SVG buttons need explicit keyboard support; native <button>s already handle it.
    if (e.currentTarget.tagName !== "BUTTON" && (e.key === "Enter" || e.key === " ")) {
      e.preventDefault(); go(e.currentTarget)
    }
  }
  targets.forEach((t) => { t.addEventListener("click", onClick); t.addEventListener("keydown", onKey) })
  return () => targets.forEach((t) => {
    t.removeEventListener("click", onClick); t.removeEventListener("keydown", onKey)
  })
}
"""

_FLOW_LOGIN = st.components.v2.component(
    "agrichain_flow_login",
    html=f'<div class="ac-root">{_svg()}{_stack()}</div>\n',
    css=_CSS,
    js=_JS,
)

KEY = "flow_login"


def flow_login(on_login: Callable[[str], None]) -> None:
    """Render the flow; `on_login(role_key)` runs when a "Masuk" button is pressed."""

    def _handle() -> None:
        state = st.session_state.get(KEY)
        role: Optional[str] = getattr(state, "login", None)
        if role is None and isinstance(state, dict):
            role = state.get("login")
        if role:
            on_login(role)

    _FLOW_LOGIN(key=KEY, data={}, on_login_change=_handle)
