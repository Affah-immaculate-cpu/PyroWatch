from html import escape

import streamlit as st


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
        /* Pull the navigation up: shrink Streamlit's 3.75rem sidebar header strip
           (it only holds the collapse button) and drop the extra top padding. */
        [data-testid="stSidebarHeader"] {
          height:2.25rem !important; min-height:2.25rem !important;
          padding-top:.4rem !important; padding-bottom:0 !important; margin-bottom:0 !important;
        }
        [data-testid="stSidebarUserContent"] { padding-top:0 !important; }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
          color: #94A3B8;
        }
        /* ---- Sidebar navigation (container key "sidebar_nav") ---- */
        .st-key-sidebar_nav { gap:.3rem; }
        .pc-nav-brand { color:#F1F5F9; font-weight:760; font-size:1.05rem;
          letter-spacing:-.02em; padding:0 .2rem .6rem; line-height:1.25; }
        .pc-nav-brand span { display:block; color:#94A3B8; font-size:.7rem; font-weight:500;
          letter-spacing:.02em; margin-top:.15rem; }
        .pc-nav-label { color:#64748B; font-size:.66rem; font-weight:700; letter-spacing:.16em;
          padding:0 .2rem; margin-bottom:1.15rem; }
        /* Streamlit pulls the element after a text block up by ~1rem; cancel that here
           so the first button doesn't slide over the NAVIGATION label. */
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
        /* One line per item: no wrapping ("Fire Detection / Map"); ellipsis if very narrow. */
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
        /* Active page: orange tint, orange left bar, white label, orange icon */
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
        /* Top bar: six separate bordered items that slide in one after another,
           left to right, starting from "PyroChronos". --i sets each item's turn. */
        .pc-topbar {
          display:flex; flex-wrap:wrap; align-items:stretch; gap:.6rem;
          margin:.1rem 0 1.3rem;
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
        .pc-push { margin-left:auto; }  /* status and everything after it sit on the right */
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


def render_topbar(sync_label: str, connected: bool, alert_count: int) -> None:
    status_class = "" if connected else "offline"
    status_text = "FIRMS DATA CONNECTED" if connected else "NO DATA FEED"
    st.markdown(
        f"""
        <div class="pc-topbar">
          <div class="pc-item" style="--i:0"><span class="pc-brand-name">PyroChronos</span></div>
          <div class="pc-item pc-brand-sub" style="--i:1">EARTH OBSERVATION · WILDFIRE INTELLIGENCE</div>
          <div class="pc-item pc-status pc-push" style="--i:2">
            <span class="pc-dot {status_class}"></span>{status_text}</div>
          <div class="pc-item pc-sync" style="--i:3">
            <strong>Last file sync</strong><span>{escape(sync_label)}</span></div>
          <div class="pc-item pc-notifications" style="--i:4"
               aria-label="{alert_count} rule-based alert signals">
            <span aria-hidden="true">🔔</span>
            <span class="pc-notification-count">{alert_count}</span>
          </div>
          <div class="pc-item pc-profile" style="--i:5"><span class="pc-avatar">GH</span>
            <span>Ghana Operations</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
