import base64
import json
from html import escape
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


PALETTE = {
    "background": "#080D18",
    "sidebar": "#101827",
    "card": "#151F30",
    "card_alt": "#111A29",
    "orange": "#FF6B35",
    "amber": "#FFB547",
    "red": "#FF4545",
    "green": "#22C55E",
    "text": "#F1F5F9",
    "muted": "#94A3B8",
    "border": "rgba(148, 163, 184, .14)",
}


def inject_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
          color-scheme: dark;
          --pc-bg: #080D18;
          --pc-sidebar: #101827;
          --pc-card: #151F30;
          --pc-orange: #FF6B35;
          --pc-amber: #FFB547;
          --pc-red: #FF4545;
          --pc-green: #22C55E;
          --pc-text: #F1F5F9;
          --pc-muted: #94A3B8;
          --pc-border: rgba(148, 163, 184, .14);
        }
        html, body, [class*="css"] { font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
        .stApp { background: #080D18; color: #F1F5F9; }
        [data-testid="stAppViewContainer"] { background:
          radial-gradient(ellipse at 70% -15%, rgba(255,107,53,.09), transparent 36%),
          #080D18; }
        [data-testid="stHeader"] { background: rgba(8,13,24,.82); }
        [data-testid="stToolbar"] { right: 1.5rem; }
        .block-container { max-width: 1600px; padding: 3.6rem 2rem 3rem; }
        [data-testid="stSidebar"] {
          background: #0B1424; border-right: 1px solid rgba(148,163,184,.12);
        }
        /* Reduce the sidebar header height and top padding. */
        [data-testid="stSidebarHeader"] {
          height:2.25rem !important; min-height:2.25rem !important;
          padding-top:.4rem !important; padding-bottom:0 !important; margin-bottom:0 !important;
        }
        [data-testid="stSidebarUserContent"] { padding-top:0 !important; }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
          color: #94A3B8;
        }
        .st-key-sidebar_nav { gap:.3rem; }
        .pc-nav-brand { color:#F1F5F9; font-weight:760; font-size:1.05rem;
          letter-spacing:-.02em; padding:0 .2rem .6rem; line-height:1.25; }
        .pc-nav-brand span { display:block; color:#94A3B8; font-size:.7rem; font-weight:500;
          letter-spacing:.02em; margin-top:.15rem; }
        .pc-nav-label { color:#64748B; font-size:.66rem; font-weight:700; letter-spacing:.16em;
          padding:0 .2rem; margin-bottom:1.15rem; }
        /* Keep the first navigation button below its label. */
        .st-key-sidebar_nav [data-testid="stElementContainer"]:has(.pc-nav-label) {
          margin-bottom:0 !important;
        }
        .st-key-sidebar_nav button {
          justify-content:flex-start !important; min-height:2.45rem; padding:0 .75rem !important;
          border:1px solid transparent !important; border-radius:10px !important;
          background:transparent !important; box-shadow:none !important;
          transition:background .15s ease, border-color .15s ease;
        }
        .st-key-sidebar_nav button > div {
          justify-content:flex-start; gap:.65rem; width:100%; min-width:0;
        }
        /* Keep navigation labels on one line and truncate narrow layouts. */
        .st-key-sidebar_nav button [data-testid="stMarkdownContainer"] { min-width:0; }
        .st-key-sidebar_nav button p {
          font-size:.86rem; font-weight:600; text-align:left;
          white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
        }
        .st-key-sidebar_nav button,
        .st-key-sidebar_nav button * { color:#AEB9C9 !important; }
        .st-key-sidebar_nav button:hover {
          background:rgba(148,163,184,.08) !important; border-color:rgba(148,163,184,.14) !important;
        }
        .st-key-sidebar_nav button:hover * { color:#F1F5F9 !important; }
        /* Highlight the active page with the orange accent. */
        .st-key-sidebar_nav [data-testid="stBaseButton-primary"] {
          background:linear-gradient(90deg,rgba(255,107,53,.22),rgba(255,107,53,.06)) !important;
          border-color:rgba(255,107,53,.45) !important;
          box-shadow:inset 3px 0 0 #FF6B35 !important;
        }
        .st-key-sidebar_nav [data-testid="stBaseButton-primary"] p { color:#FFFFFF !important; }
        .st-key-sidebar_nav [data-testid="stBaseButton-primary"] [data-testid="stIconMaterial"],
        .st-key-sidebar_nav [data-testid="stBaseButton-primary"] span { color:#FF8A4C !important; }
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
          color: #CBD5E1; font-size: .79rem; font-weight: 600;
        }
        #stMain [data-testid="stWidgetLabel"] p {
          color:#E2E8F0 !important; font-size:.84rem; font-weight:650;
        }
        #stMain [data-testid="stSelectbox"] [data-baseweb="select"] {
          color:#F1F5F9 !important;
        }
        #stMain [role="radiogroup"] label {
          color:#CBD5E1 !important; font-weight:600; padding:.35rem .8rem;
          border:1px solid rgba(148,163,184,.28); border-radius:9px; background:#172235;
        }
        #stMain [role="radiogroup"] label * { color:#CBD5E1 !important; }
        #stMain [role="radiogroup"] label:hover {
          border-color:rgba(255,107,53,.6); background:#22314A;
        }
        #stMain [role="radiogroup"] label:hover * { color:#FFB547 !important; }
        #stMain [role="radiogroup"] label:has(input:checked) {
          color:#FFFFFF !important; background:#C2481F; border-color:#FF6B35;
        }
        #stMain [role="radiogroup"] label:has(input:checked) * { color:#FFFFFF !important; }
        [data-testid="stSelectbox"], [data-testid="stMultiSelect"],
        [data-testid="stDateInput"], [data-testid="stSlider"],
        [data-testid="stTextInput"] { margin-bottom: .35rem; }
        [data-testid="stBaseButton-secondary"], [data-testid="stDownloadButton"] button {
          background: #172235; border: 1px solid var(--pc-border); color: #F1F5F9;
          border-radius: 9px; transition: all .18s ease;
        }
        [data-testid="stBaseButton-secondary"]:hover,
        [data-testid="stDownloadButton"] button:hover {
          border-color: rgba(255,107,53,.55); color: #FFB547;
        }
        [data-testid="stBaseButton-primary"] {
          background: linear-gradient(120deg, #FF6B35, #E8502B); border: 0;
          border-radius: 9px; color: white;
        }
        [data-testid="stMetric"] {
          background: transparent; padding: 0; border: 0;
        }
        [data-testid="stMetricLabel"] { color: #94A3B8; }
        [data-testid="stMetricValue"] { color: #F1F5F9; }
        [data-testid="stTabs"] [role="tablist"] { gap: .35rem; }
        [data-testid="stTabs"] button[role="tab"] {
          color: #94A3B8; border-radius: 9px 9px 0 0;
        }
        [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
          color: #FFB547; border-bottom-color: #FF6B35;
        }
        [data-testid="stDataFrame"], [data-testid="stTable"] {
          border: 1px solid var(--pc-border); border-radius: 10px; overflow: hidden;
        }
        /* "Regional fire patterns": white panel with dark text */
        .st-key-regional_panel {
          background:#FFFFFF; border-radius:13px; padding:.4rem 1.1rem 1rem;
          box-shadow:0 8px 22px rgba(0,0,0,.18);
        }
        .st-key-regional_panel .pc-section-title { color:#0F172A; }
        .st-key-regional_panel .pc-section-note { color:#475569; }
        .st-key-regional_panel [data-testid="stTable"] { border:1px solid #E2E8F0; }
        .st-key-regional_panel table { background:#FFFFFF; color:#0F172A; width:100%; }
        .st-key-regional_panel th, .st-key-regional_panel td {
          background:#FFFFFF !important; color:#0F172A !important;
          border-color:#E2E8F0 !important;
        }
        .st-key-regional_panel thead th { background:#F1F5F9 !important; color:#334155 !important;
          font-weight:700; }
        .st-key-regional_panel tbody tr:hover th,
        .st-key-regional_panel tbody tr:hover td { background:#FFF4EE !important; }
        [data-testid="stExpander"] {
          background: rgba(21,31,48,.58); border: 1px solid var(--pc-border);
          border-radius: 10px;
        }
        [data-testid="stAlert"] { border-radius: 10px; }
        hr { border-color: var(--pc-border); }
        h1, h2, h3 { letter-spacing: -.025em; }
        h2 { font-size: 1.18rem; }
        h3 { font-size: 1rem; }
        /* Animate top-bar items in sequence. */
        .st-key-pc_topbar { flex-wrap:wrap; gap:.6rem !important; margin:.1rem 0 1.3rem; }
        /* "FIRMS DATA CONNECTED" and everything after it sit on the right. */
        .st-key-pc_topbar [data-testid="stElementContainer"]:has(.pc-push) { margin-left:auto; }
        /* Every top-bar box (and the megaphone button) is exactly 50px tall so the row lines up. */
        .st-key-pc_topbar .pc-item { height:50px; box-sizing:border-box; padding-top:0; padding-bottom:0; }
        /* Align top-bar boxes and the notification button. */
        .st-key-pc_topbar [data-testid="stMarkdownContainer"] { margin-bottom:0 !important; }
        /* Megaphone notification button: same box style + slide-in turn (5th). */
        .st-key-topbar_alerts button {
          height:50px; min-height:50px; box-sizing:border-box;
          padding:0 .8rem 0 2.75rem !important;
          border:1px solid rgba(148,163,184,.22) !important; border-radius:11px !important;
          background:
            url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23FFB547' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M8.2 9.3H5.1A1.6 1.6 0 0 0 3.5 10.9v2.2a1.6 1.6 0 0 0 1.6 1.6h3.1z'/%3E%3Cpath d='M8.2 9.3l6.3-3a1.1 1.1 0 0 1 1.6 1v9.4a1.1 1.1 0 0 1-1.6 1l-6.3-3'/%3E%3Cpath d='M5.3 14.7v2.6a1 1 0 0 0 2 0v-2.6'/%3E%3Cpath d='M18.4 8.4l2-.8M18.9 12h2.1M18.4 15.6l2 1.1'/%3E%3C/svg%3E")
              no-repeat .7rem center / 27px 27px,
            linear-gradient(110deg,rgba(21,31,48,.96),rgba(14,22,36,.94)) !important;
          box-shadow:0 8px 20px rgba(0,0,0,.16);
          opacity:0; animation:pc-slide-in .55s cubic-bezier(.2,.7,.2,1) forwards;
          animation-delay:.56s;
          transition:border-color .18s ease, transform .18s ease;
        }
        .st-key-topbar_alerts button:hover {
          border-color:rgba(255,107,53,.6) !important; transform:translateY(-1px);
        }
        .st-key-topbar_alerts button p {
          font-size:0; line-height:0;
        }
        @media (prefers-reduced-motion: reduce) {
          .st-key-topbar_alerts button { animation:none; opacity:1; }
        }
        .pc-item {
          display:flex; align-items:center; gap:.5rem; padding:.55rem .9rem;
          border:1px solid rgba(148,163,184,.22); border-radius:11px;
          background:linear-gradient(110deg,rgba(21,31,48,.96),rgba(14,22,36,.94));
          box-shadow:0 8px 20px rgba(0,0,0,.16);
          opacity:0; animation:pc-slide-in .55s cubic-bezier(.2,.7,.2,1) forwards;
          animation-delay:calc(var(--i) * .14s);
          transition:border-color .18s ease, transform .18s ease;
        }
        .pc-item:hover { border-color:rgba(255,107,53,.5); transform:translateY(-1px); }
        @keyframes pc-slide-in {
          from { opacity:0; transform:translateX(-28px); }
          to   { opacity:1; transform:translateX(0); }
        }
        @media (prefers-reduced-motion: reduce) {
          .pc-item { animation:none; opacity:1; }
        }
        .pc-push { margin-left:auto; }  /* Align status and following items to the right. */
        .pc-brand-name { color:#F1F5F9; font-weight:750; font-size:1.03rem; }
        .pc-brand-sub { color:#94A3B8; font-size:.72rem; letter-spacing:.04em; }
        .pc-sync { flex-direction:column; align-items:flex-end; justify-content:center; gap:0;
          color:#94A3B8; font-size:.74rem; line-height:1.4; }
        .pc-sync strong { color:#CBD5E1; font-weight:600; }
        .pc-status { white-space:nowrap; color:#C2CBD8;
          font-size:.72rem; letter-spacing:.055em; text-transform:uppercase; }
        .pc-dot { width:8px; height:8px; border-radius:50%; background:#22C55E;
          box-shadow:0 0 0 4px rgba(34,197,94,.12); animation:pc-pulse 2.2s ease-out infinite; }
        .pc-dot.offline { background:#FFB547; box-shadow:0 0 0 4px rgba(255,181,71,.12); }
        @keyframes pc-pulse { 50% { box-shadow:0 0 0 7px rgba(34,197,94,0); } }
        .pc-notifications { position:relative; color:#FFB547; font-size:1rem; }
        .pc-notification-count { display:grid; place-items:center; min-width:19px; height:19px;
          padding:0 5px; border-radius:10px; background:#FF4545; color:#fff;
          font-size:.66rem; font-weight:700; }
        .pc-profile { color:#F1F5F9; font-size:.78rem; }
        .pc-avatar { display:grid; place-items:center; width:29px; height:29px; border-radius:50%;
          background:#24334A; color:#FFB547; font-weight:700; font-size:.75rem; }
        .pc-hero { margin:.25rem 0 1.1rem; }
        .pc-eyebrow { color:#FF9A64; font-size:.7rem; font-weight:700; letter-spacing:.16em;
          text-transform:uppercase; }
        .pc-hero-title { margin:.25rem 0 .35rem; color:#F1F5F9; font-size:1.8rem;
          line-height:1.2; font-weight:760; letter-spacing:-.04em; }
        .pc-hero-copy { margin:0; color:#94A3B8; font-size:.9rem; }
        .pc-kpis { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.8rem;
          margin:1.15rem 0 1.3rem; }
        .pc-kpi { position:relative; min-height:126px; overflow:hidden; padding:1rem 1.05rem;
          border:1px solid var(--pc-border); border-radius:13px;
          background:linear-gradient(145deg,rgba(21,31,48,.98),rgba(17,26,41,.96));
          box-shadow:0 8px 22px rgba(0,0,0,.13); transition:transform .18s ease,border-color .18s ease; }
        .pc-kpi:hover { transform:translateY(-2px); border-color:rgba(255,107,53,.34); }
        .pc-kpi:after { content:""; position:absolute; width:115px; height:115px; right:-42px; top:-48px;
          border-radius:50%; background:var(--pc-glow); filter:blur(38px); opacity:.24; }
        .pc-kpi-top { position:relative; z-index:1; display:flex; align-items:center;
          justify-content:space-between; color:#94A3B8; font-size:.78rem; font-weight:600; }
        .pc-kpi-icon { display:grid; place-items:center; width:30px; height:30px; border-radius:9px;
          color:var(--pc-accent); background:color-mix(in srgb,var(--pc-accent) 13%,transparent); }
        .pc-kpi-value { position:relative; z-index:1; margin:.68rem 0 .23rem; color:#F1F5F9;
          font-size:1.8rem; line-height:1; font-weight:760; letter-spacing:-.04em; }
        .pc-kpi-detail { position:relative; z-index:1; color:#94A3B8; font-size:.7rem; }
        .pc-section-head { display:flex; align-items:flex-end; justify-content:space-between;
          gap:1rem; margin:1.2rem 0 .7rem; }
        .pc-section-title { margin:0; color:#F1F5F9; font-weight:700; font-size:1rem; }
        .pc-section-note { color:#94A3B8; font-size:.75rem; }
        .pc-panel { padding:1rem 1.05rem; border:1px solid var(--pc-border); border-radius:13px;
          background:rgba(21,31,48,.78); }
        .pc-map-legend { display:flex; flex-wrap:wrap; gap:.8rem; color:#CBD5E1; font-size:.72rem; }
        .pc-legend-item { display:flex; align-items:center; gap:.35rem; }
        .pc-legend-dot { width:8px; height:8px; border-radius:50%; background:var(--legend-color); }
        .pc-alert-row { padding:.76rem .85rem; margin:.48rem 0; border:1px solid var(--pc-border);
          border-left:3px solid var(--alert-color); border-radius:9px;
          background:rgba(21,31,48,.68); }
        /* Match compact alert boxes to the button width. */
        .pc-alert-row.pc-alert-compact { padding:.45rem .7rem; margin:0 0 .4rem; border-radius:8px; }
        /* Two signal boxes per row; equal heights within a row; one per row on phones. */
        .pc-signal-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.5rem; }
        .pc-signal-grid .pc-alert-row.pc-alert-compact { margin:0; }
        @media (max-width:640px) { .pc-signal-grid { grid-template-columns:1fr; } }
        .pc-alert-compact .pc-alert-title { font-size:.76rem; }
        .pc-alert-compact .pc-alert-copy { font-size:.68rem; margin-top:.12rem; line-height:1.35; }
        .st-key-priority_signals [data-testid="stElementContainer"]:has(.pc-alert-compact) {
          margin-bottom:0 !important;
        }
        .pc-alert-title { color:#F1F5F9; font-size:.8rem; font-weight:650; }
        .pc-alert-copy { color:#94A3B8; font-size:.73rem; margin-top:.22rem; }
        .pc-muted { color:#94A3B8; font-size:.78rem; }
        @media (max-width:900px) {
          .block-container { padding:1rem 1rem 2rem; }
          .pc-kpis { grid-template-columns:repeat(2,minmax(0,1fr)); }
          .pc-sync { display:none; }
          .pc-brand-sub { display:none; }
          .pc-profile span:last-child { display:none; }
        }
        @media (max-width:520px) {
          .pc-kpis { grid-template-columns:1fr 1fr; gap:.5rem; }
          .pc-kpi { min-height:112px; padding:.78rem; }
          .pc-kpi-value { font-size:1.45rem; }
          .pc-status { font-size:.62rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


FLAME_ICON = Path(__file__).resolve().parents[1] / "assets" / "flame.png"

_FLAME_FAVICON_JS = """
(() => {
  // One animation per browser tab, even though Streamlit reruns the app script.
  if (window.__pcFlame) return;
  window.__pcFlame = true;
  const img = new Image();
  img.onload = () => {
    const size = 64, canvas = document.createElement('canvas');
    canvas.width = canvas.height = size;
    const ctx = canvas.getContext('2d');
    const draw = (t, mirror, alpha, sx, sy, skew) => {
      ctx.save();
      ctx.globalAlpha = alpha;
      ctx.translate(size / 2, size);                 // anchor at the base of the flame
      ctx.transform(sx * (mirror ? -1 : 1), 0, skew, sy, 0, 0);
      ctx.drawImage(img, -29, -58, 58, 58);
      ctx.restore();
    };
    const start = performance.now();
    setInterval(() => {
      const t = (performance.now() - start) / 1000;
      const sy = 1 + 0.06 * Math.sin(t * 5.3) + 0.03 * Math.sin(t * 11.7);
      const sx = 1 + 0.025 * Math.sin(t * 4.1 + 1);
      const skew = 0.07 * Math.sin(t * 2.7) + 0.03 * Math.sin(t * 6.9);
      ctx.clearRect(0, 0, size, size);
      ctx.filter = `brightness(${1 + 0.12 * Math.sin(t * 9.1)}) saturate(1.1)`;
      draw(t, false, 1, sx, sy, skew);
      // A mirrored copy fading in and out makes the tongues of flame shift.
      draw(t, true, 0.3 + 0.3 * Math.sin(t * 3.3), sx * 0.98, sy * 1.02, -skew);
      const href = canvas.toDataURL('image/png');
      let links = document.querySelectorAll('link[rel~="icon"]');
      if (!links.length) {
        const link = document.createElement('link');
        link.rel = 'icon';
        document.head.appendChild(link);
        links = [link];
      }
      links.forEach((link) => { link.type = 'image/png'; link.href = href; });
    }, 90);
  };
  img.src = '__FLAME_SRC__';
})();
"""


def animate_favicon() -> None:
    """Make the browser-tab icon a continuously burning flame (assets/flame.png).

    A zero-height component copies the animation script into the main page, so the
    animation lives in the page itself and survives reruns and page switches.
    """
    if not FLAME_ICON.exists():
        return
    src = "data:image/png;base64," + base64.b64encode(FLAME_ICON.read_bytes()).decode()
    code = json.dumps(_FLAME_FAVICON_JS.replace("__FLAME_SRC__", src))
    components.html(
        "<script>(() => { const doc = window.parent.document;"
        " if (window.parent.__pcFlame) return;"
        " const s = doc.createElement('script');"
        f" s.textContent = {code}; doc.head.appendChild(s); }})();</script>",
        height=0,
    )


def render_topbar(sync_label: str, connected: bool, on_alerts_click=None) -> None:
    """Top bar built from Streamlit elements so the megaphone notification is a real
    button: clicking it runs `on_alerts_click` (opens Emberwatch Alerts) without a page
    reload, so session state such as alert statuses and filters is kept."""
    status_class = "" if connected else "offline"
    status_text = "FIRMS DATA CONNECTED" if connected else "NO DATA FEED"

    def item(html: str) -> None:
        st.markdown(html, unsafe_allow_html=True, width="content")

    with st.container(key="pc_topbar", horizontal=True, gap="small",
                      vertical_alignment="center"):
        item('<div class="pc-item" style="--i:0"><span class="pc-brand-name">PyroWatch</span></div>')
        item('<div class="pc-item pc-brand-sub" style="--i:1">'
             'EARTH OBSERVATION · WILDFIRE INTELLIGENCE</div>')
        item(f'<div class="pc-item pc-status pc-push" style="--i:2">'
             f'<span class="pc-dot {status_class}"></span>{status_text}</div>')
        item(f'<div class="pc-item pc-sync" style="--i:3"><strong>Last file sync</strong>'
             f'<span>{escape(sync_label)}</span></div>')
        # The alert control is icon-only; its label remains available to assistive technology.
        st.button(
            "Alerts",
            key="topbar_alerts",
            help="Open Emberwatch Alerts",
            on_click=on_alerts_click,
        )
        item('<div class="pc-item pc-profile" style="--i:5"><span class="pc-avatar">GH</span>'
             '<span>Ghana Operations</span></div>')


def render_hero(title: str, subtitle: str, eyebrow: str = "Operational picture") -> None:
    st.markdown(
        f"""
        <div class="pc-hero">
          <div class="pc-eyebrow">{escape(eyebrow)}</div>
          <div class="pc-hero-title">{escape(title)}</div>
          <p class="pc-hero-copy">{escape(subtitle)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpis(cards: list[dict[str, str]]) -> None:
    items = []
    for card in cards:
        accent = card["accent"]
        items.append(
            f'<div class="pc-kpi" style="--pc-accent:{escape(accent)};--pc-glow:{escape(accent)}">'
            f'<div class="pc-kpi-top"><span>{escape(card["label"])}</span></div>'
            f'<div class="pc-kpi-value">{escape(card["value"])}</div>'
            f'<div class="pc-kpi-detail">{escape(card["detail"])}</div></div>'
        )
    st.markdown(f'<div class="pc-kpis">{"".join(items)}</div>', unsafe_allow_html=True)


def section_heading(title: str, note: str = "") -> None:
    st.markdown(
        f"""
        <div class="pc-section-head">
          <div class="pc-section-title">{escape(title)}</div>
          <div class="pc-section-note">{escape(note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def style_chart(fig, height: int = 320):
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#151F30",
        font={"family": "Inter, system-ui, sans-serif", "color": "#CBD5E1", "size": 11},
        margin={"l": 12, "r": 12, "t": 22, "b": 12},
        legend={"bgcolor": "rgba(0,0,0,0)", "font": {"color": "#CBD5E1"}},
        hoverlabel={"bgcolor": "#101827", "bordercolor": "#34445D", "font": {"color": "#F1F5F9"}},
        xaxis={
            "gridcolor": "rgba(148,163,184,.10)",
            "linecolor": "rgba(148,163,184,.16)",
            "zerolinecolor": "rgba(148,163,184,.14)",
            "tickfont": {"color": "#94A3B8"},
        },
        yaxis={
            "gridcolor": "rgba(148,163,184,.10)",
            "linecolor": "rgba(148,163,184,.16)",
            "zerolinecolor": "rgba(148,163,184,.14)",
            "tickfont": {"color": "#94A3B8"},
        },
    )
    return fig
