"""
utils/style.py
==============
Shared CSS, layout helpers, and constants for the EU Economic Monitor dashboard.
Tableau-inspired dark theme — clean, professional, data-forward.
"""

from __future__ import annotations
import streamlit as st

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ALL_COUNTRIES: dict[str, str] = {
    "AT": "Austria",     "BE": "Belgium",     "CZ": "Czechia",
    "DE": "Germany",     "DK": "Denmark",     "EL": "Greece",
    "ES": "Spain",       "FI": "Finland",     "FR": "France",
    "HU": "Hungary",     "IE": "Ireland",     "IT": "Italy",
    "NL": "Netherlands", "PL": "Poland",      "PT": "Portugal",
    "RO": "Romania",     "SE": "Sweden",      "SK": "Slovakia",
}

FLAG_MAP: dict[str, str] = {
    "AT": "🇦🇹", "BE": "🇧🇪", "CZ": "🇨🇿", "DE": "🇩🇪", "DK": "🇩🇰",
    "EL": "🇬🇷", "ES": "🇪🇸", "FI": "🇫🇮", "FR": "🇫🇷", "HU": "🇭🇺",
    "IE": "🇮🇪", "IT": "🇮🇹", "NL": "🇳🇱", "PL": "🇵🇱", "PT": "🇵🇹",
    "RO": "🇷🇴", "SE": "🇸🇪", "SK": "🇸🇰",
}

# ---------------------------------------------------------------------------
# CSS — Tableau-inspired dark theme
# ---------------------------------------------------------------------------
SHARED_CSS = """
<style>
/* ═══ FONTS ═══════════════════════════════════════════════════════════════ */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif !important; }

/* ═══ GLOBAL ═══════════════════════════════════════════════════════════════ */
.stApp { background: #0D1117; }
.main .block-container {
    padding-top: 1.25rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: none !important;
}
* { box-sizing: border-box; }

/* ═══ SIDEBAR ══════════════════════════════════════════════════════════════ */
section[data-testid="stSidebar"] {
    background: #0D1117 !important;
    border-right: 1px solid rgba(255,255,255,0.07) !important;
}
section[data-testid="stSidebar"] > div { background: #0D1117 !important; }
section[data-testid="stSidebar"] .stMarkdown p { color: #8B949E; font-size: 0.85rem; }
section[data-testid="stSidebar"] label {
    color: #8B949E !important; font-size: 0.82rem !important;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 { color: #E6EDF3 !important; }

section[data-testid="stSidebarNav"] { background: #0D1117 !important; }
section[data-testid="stSidebarNav"] a {
    border-radius: 8px; margin: 2px 0; padding: 5px 10px; transition: background 0.15s;
}
section[data-testid="stSidebarNav"] a:hover { background: rgba(88,166,255,0.08) !important; }
section[data-testid="stSidebarNav"] a[aria-selected="true"] { background: rgba(88,166,255,0.14) !important; }
section[data-testid="stSidebarNav"] a span,
section[data-testid="stSidebarNav"] a p { color: #8B949E !important; font-size: 0.86rem !important; }
section[data-testid="stSidebarNav"] a:hover span,
section[data-testid="stSidebarNav"] a:hover p { color: #58A6FF !important; }
section[data-testid="stSidebarNav"] a[aria-selected="true"] span,
section[data-testid="stSidebarNav"] a[aria-selected="true"] p {
    color: #58A6FF !important; font-weight: 600 !important;
}
section[data-testid="stSidebar"] ::-webkit-scrollbar { width: 4px; }
section[data-testid="stSidebar"] ::-webkit-scrollbar-track { background: transparent; }
section[data-testid="stSidebar"] ::-webkit-scrollbar-thumb { background: #30363D; border-radius: 2px; }

/* ═══ WIDGETS ══════════════════════════════════════════════════════════════ */
[data-baseweb="select"] > div,
[data-baseweb="select"] > div:focus-within {
    background-color: #161B22 !important; border-color: #30363D !important;
}
[data-baseweb="tag"] {
    background-color: rgba(88,166,255,0.12) !important;
    border: 1px solid rgba(88,166,255,0.25) !important;
}
[data-baseweb="tag"] span { color: #58A6FF !important; }
[data-baseweb="tag"] [role="presentation"] { color: #58A6FF !important; }

/* ═══ TABS ══════════════════════════════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {
    background: #161B22; border-radius: 10px; padding: 4px; gap: 4px;
    border: 1px solid #21262D;
}
.stTabs [data-baseweb="tab"] {
    background: transparent; border-radius: 8px; color: #8B949E;
    padding: 6px 18px; font-weight: 500; font-size: 0.86rem;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: #1F6FEB !important; color: #FFFFFF !important;
}
.stTabs [data-baseweb="tab"]:hover { color: #E6EDF3 !important; background: rgba(255,255,255,0.05) !important; }
.stTabs [data-baseweb="tab-border"],
.stTabs [data-baseweb="tab-highlight"] { display: none !important; }

/* ═══ METRICS ══════════════════════════════════════════════════════════════ */
div[data-testid="metric-container"] {
    background: #161B22 !important; border: 1px solid #21262D !important;
    border-radius: 12px !important; padding: 1rem 1.2rem !important;
}
div[data-testid="metric-container"] label {
    color: #8B949E !important; font-size: 0.75rem !important;
    font-weight: 700 !important; text-transform: uppercase !important; letter-spacing: 0.06em !important;
}
div[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #E6EDF3 !important; font-size: 1.75rem !important; font-weight: 700 !important;
}

/* ═══ DATAFRAME ════════════════════════════════════════════════════════════ */
.stDataFrame { border: 1px solid #21262D !important; border-radius: 10px !important; overflow: hidden; }

/* ═══ PAGE HEADER ══════════════════════════════════════════════════════════ */
.page-header {
    display: flex; align-items: center; gap: 1rem;
    padding: 1.1rem 1.5rem;
    background: linear-gradient(135deg, #161B22 0%, #1C2128 100%);
    border-radius: 14px; border: 1px solid #21262D;
    margin-bottom: 1.5rem; box-shadow: 0 4px 24px rgba(0,0,0,0.35);
    position: relative; overflow: hidden;
}
.page-header::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, #1F6FEB 0%, #58A6FF 50%, #79C0FF 100%);
}
.page-header-icon { font-size: 2.4rem; line-height: 1; flex-shrink: 0; }
.page-header-content { flex: 1; }
.page-header-title {
    color: #E6EDF3; font-size: 1.55rem; font-weight: 700;
    margin: 0 0 0.15rem; letter-spacing: -0.3px;
}
.page-header-subtitle { color: #8B949E; font-size: 0.83rem; margin: 0; }
.page-header-badge {
    background: rgba(31,111,235,0.12); border: 1px solid rgba(31,111,235,0.28);
    color: #58A6FF; padding: 0.2rem 0.75rem; border-radius: 20px;
    font-size: 0.72rem; font-weight: 700; white-space: nowrap; letter-spacing: 0.04em;
}

/* ═══ KPI CARDS ════════════════════════════════════════════════════════════ */
.kpi-card {
    background: #161B22; border: 1px solid #21262D; border-radius: 14px;
    padding: 1.2rem 1.4rem; position: relative; overflow: hidden;
    transition: border-color 0.2s, transform 0.2s, box-shadow 0.2s; height: 100%;
}
.kpi-card:hover {
    border-color: rgba(88,166,255,0.25); transform: translateY(-2px);
    box-shadow: 0 8px 28px rgba(0,0,0,0.3);
}
.kpi-card::after {
    content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 2px;
    background: var(--kpi-accent, #1F6FEB); opacity: 0.7;
}
.kpi-accent-blue   { --kpi-accent: #1F6FEB; }
.kpi-accent-teal   { --kpi-accent: #0D9488; }
.kpi-accent-purple { --kpi-accent: #8B5CF6; }
.kpi-accent-amber  { --kpi-accent: #D97706; }
.kpi-accent-green  { --kpi-accent: #059669; }
.kpi-icon  { font-size: 1.5rem; margin-bottom: 0.6rem; opacity: 0.8; }
.kpi-label {
    color: #6E7681; font-size: 0.7rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.09em; margin-bottom: 0.35rem;
}
.kpi-value {
    color: #E6EDF3; font-size: 1.95rem; font-weight: 800;
    line-height: 1.05; letter-spacing: -1px; margin-bottom: 0.35rem;
}
.kpi-value-sm {
    color: #E6EDF3; font-size: 1.45rem; font-weight: 800;
    line-height: 1.1; letter-spacing: -0.5px; margin-bottom: 0.35rem;
}
.kpi-delta { font-size: 0.76rem; font-weight: 500; color: #6E7681; display: flex; align-items: center; gap: 0.2rem; }
.kpi-delta.delta-up   { color: #3FB950; }
.kpi-delta.delta-down { color: #F85149; }

/* ═══ SECTION HEADERS ══════════════════════════════════════════════════════ */
.section-header {
    display: flex; align-items: center; justify-content: space-between;
    margin: 1.4rem 0 0.7rem; padding-bottom: 0.55rem;
    border-bottom: 1px solid #21262D;
}
.section-title {
    color: #E6EDF3; font-size: 0.82rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.09em;
    display: flex; align-items: center; gap: 0.5rem;
}
.section-title::before {
    content: ''; display: inline-block; width: 3px; height: 13px;
    background: #1F6FEB; border-radius: 2px;
}
.section-badge {
    background: #161B22; border: 1px solid #21262D; color: #6E7681;
    padding: 2px 9px; border-radius: 12px; font-size: 0.7rem; font-weight: 600;
}

/* ═══ PANEL CARD (chart wrappers) ══════════════════════════════════════════ */
.panel-card {
    background: #161B22; border: 1px solid #21262D; border-radius: 14px; padding: 1.25rem;
}
.panel-title {
    color: #6E7681; font-size: 0.72rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.1em;
    margin-bottom: 0.85rem; padding-bottom: 0.5rem; border-bottom: 1px solid #21262D;
}

/* ═══ ALERT CARDS ══════════════════════════════════════════════════════════ */
.alert-card {
    display: flex; align-items: flex-start; gap: 0.75rem;
    padding: 0.8rem 1rem; background: #161B22;
    border-radius: 10px; border: 1px solid #21262D;
    border-left: 3px solid #21262D; margin-bottom: 0.45rem;
}
.alert-card.alert-HIGH   { border-left-color: #F85149; }
.alert-card.alert-MEDIUM { border-left-color: #E3B341; }
.alert-card.alert-LOW    { border-left-color: #3FB950; }
.alert-pill {
    font-size: 0.62rem; font-weight: 800; text-transform: uppercase;
    letter-spacing: 0.1em; padding: 0.15rem 0.55rem; border-radius: 4px; white-space: nowrap; margin-top: 0.1rem;
}
.alert-pill.alert-HIGH   { background: rgba(248,81,73,0.14);  color: #F85149; }
.alert-pill.alert-MEDIUM { background: rgba(227,179,65,0.14); color: #E3B341; }
.alert-pill.alert-LOW    { background: rgba(63,185,80,0.14);  color: #3FB950; }
.alert-title { color: #E6EDF3; font-size: 0.86rem; font-weight: 600; margin-bottom: 0.1rem; }
.alert-meta  { color: #6E7681; font-size: 0.74rem; }

/* ═══ RANK TABLE ═══════════════════════════════════════════════════════════ */
.rank-row {
    display: flex; align-items: center; gap: 0.5rem;
    padding: 0.45rem 0.65rem; border-radius: 8px; margin-bottom: 0.25rem;
    transition: background 0.12s;
}
.rank-row:hover { background: rgba(255,255,255,0.04); }
.rank-num  { color: #6E7681; font-size: 0.75rem; font-weight: 700; width: 1.4rem; text-align: center; flex-shrink: 0; }
.rank-flag { font-size: 1.05rem; flex-shrink: 0; }
.rank-name { color: #E6EDF3; font-size: 0.84rem; font-weight: 500; flex: 1; }
.rank-bar-track { flex: 1; height: 4px; background: #21262D; border-radius: 2px; overflow: hidden; max-width: 70px; }
.rank-bar-fill  { height: 100%; background: linear-gradient(90deg, #1F6FEB, #58A6FF); border-radius: 2px; }
.rank-score { color: #58A6FF; font-size: 0.85rem; font-weight: 700; width: 2.8rem; text-align: right; flex-shrink: 0; }
.rank-gdp   { font-size: 0.74rem; font-weight: 600; width: 3.2rem; text-align: right; flex-shrink: 0; }

/* ═══ PIPELINE LEGEND ══════════════════════════════════════════════════════ */
.pipeline-box {
    background: #161B22; border: 1px solid #21262D; border-radius: 10px;
    padding: 0.75rem 1rem; font-size: 0.78rem; color: #8B949E; line-height: 1.85;
}
.pip-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 5px; vertical-align: middle; }

/* ═══ SIDEBAR LABEL ════════════════════════════════════════════════════════ */
.sb-label {
    color: #6E7681; font-size: 0.68rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.1em; margin: 0 0 0.5rem;
}
.sb-divider { height: 1px; background: rgba(255,255,255,0.06); margin: 0.9rem 0; }
/* ╣══ SCORE PILL ═════════════════════════════════════════════════════ */
.score-pill {
    display: inline-block; padding: .2rem .7rem; border-radius: 20px;
    font-weight: 700; font-size: .88rem;
}
/* ═══ FOOTER ═══════════════════════════════════════════════════════════════ */
.dash-footer {
    text-align: center; color: #6E7681; font-size: 0.76rem;
    padding: 1rem 0 0.5rem; border-top: 1px solid #21262D; margin-top: 2rem;
}
.dash-footer a { color: #58A6FF; text-decoration: none; }
.dash-footer a:hover { text-decoration: underline; }

/* ═══ SCROLLBAR ════════════════════════════════════════════════════════════ */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0D1117; }
::-webkit-scrollbar-thumb { background: #30363D; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #484F58; }

/* ═══ EXPANDER ═════════════════════════════════════════════════════════════ */
[data-testid="stExpander"] {
    background: #161B22 !important; border: 1px solid #21262D !important; border-radius: 10px !important;
}
[data-testid="stExpanderDetails"] { background: #161B22 !important; }
</style>
"""


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------
def inject_css() -> None:
    """Inject shared CSS into the current Streamlit page."""
    st.markdown(SHARED_CSS, unsafe_allow_html=True)


def page_header(icon: str, title: str, subtitle: str, badge: str = "") -> None:
    """Render the full-width page header banner."""
    badge_html = f'<span class="page-header-badge">{badge}</span>' if badge else ""
    st.markdown(
        f"""<div class="page-header">
            <div class="page-header-icon">{icon}</div>
            <div class="page-header-content">
                <div class="page-header-title">{title}</div>
                <div class="page-header-subtitle">{subtitle}</div>
            </div>
            {badge_html}
        </div>""",
        unsafe_allow_html=True,
    )


def section_header(title: str, badge: str = "") -> None:
    """Render a styled section heading with optional badge."""
    badge_html = f'<span class="section-badge">{badge}</span>' if badge else ""
    st.markdown(
        f"""<div class="section-header">
            <span class="section-title">{title}</span>
            {badge_html}
        </div>""",
        unsafe_allow_html=True,
    )


def kpi_card(
    label: str,
    value: str,
    delta: str = "",
    delta_up: bool | None = None,
    icon: str = "",
    accent: str = "blue",
) -> None:
    """Render a single KPI card. Place inside an st.columns() cell."""
    delta_cls = "" if delta_up is None else ("delta-up" if delta_up else "delta-down")
    arrow = "" if delta_up is None else ("↑ " if delta_up else "↓ ")
    delta_html = f'<div class="kpi-delta {delta_cls}">{arrow}{delta}</div>' if delta else ""
    icon_html  = f'<div class="kpi-icon">{icon}</div>' if icon else ""
    value_cls  = "kpi-value-sm" if len(value) > 7 else "kpi-value"
    st.html(
        f"""<div class="kpi-card kpi-accent-{accent}">
            {icon_html}
            <div class="kpi-label">{label}</div>
            <div class="{value_cls}">{value}</div>
            {delta_html}
        </div>"""
    )


def sidebar_logo() -> None:
    """Render the EU Monitor logo block at the top of the sidebar."""
    st.markdown(
        """<div style="padding:0.85rem 0 0.3rem;">
            <div style="display:flex;align-items:center;gap:.7rem;margin-bottom:.5rem;">
                <span style="font-size:2rem;line-height:1;">🇪🇺</span>
                <div>
                    <div style="color:#E6EDF3;font-size:.95rem;font-weight:700;line-height:1.25;">EU Economic</div>
                    <div style="color:#6E7681;font-size:.75rem;font-weight:500;">Monitor</div>
                </div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )


def sb_divider() -> None:
    """Thin sidebar divider."""
    st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)


def sb_label(text: str) -> None:
    """Uppercase section label for sidebar."""
    st.markdown(f'<div class="sb-label">{text}</div>', unsafe_allow_html=True)
