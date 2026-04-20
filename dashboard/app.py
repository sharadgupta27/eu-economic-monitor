"""
app.py  EU Economic Monitor    Main Dashboard
================================================
Streamlit multi-page dashboard for European economic statistics.
Run:  streamlit run app.py
"""

from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from utils.bigquery_client import (
    get_country_latest,
    get_composite_index,
    get_anomaly_alerts,
)
from utils.charts import eu_choropleth
from utils.style import (
    inject_css, page_header, section_header, kpi_card,
    sidebar_logo, sb_divider, sb_label, FLAG_MAP, ALL_COUNTRIES,
)

#  Page config 
st.set_page_config(
    page_title="EU Economic Monitor",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

#  Sidebar 
with st.sidebar:
    sidebar_logo()
    sb_divider()

    sb_label("Filters")
    selected_country_codes = st.multiselect(
        "Countries",
        options=list(ALL_COUNTRIES.keys()),
        default=list(ALL_COUNTRIES.keys()),
        format_func=lambda c: f"{FLAG_MAP.get(c,'')} {c}  {ALL_COUNTRIES[c]}",
    )
    year_range = st.slider("Year range", 2000, 2023, (2010, 2023))

    sb_divider()
    sb_label("Data Pipeline")
    st.markdown(
        """<div class="pipeline-box">
            <span class="pip-dot" style="background:#58A6FF;"></span><b style="color:#58A6FF;">dlt</b> Ingestion  BigQuery<br>
            <span class="pip-dot" style="background:#A371F7;"></span><b style="color:#A371F7;">Spark</b> Batch Processing<br>
            <span class="pip-dot" style="background:#3FB950;"></span><b style="color:#3FB950;">dbt</b> Transformations<br>
            <span class="pip-dot" style="background:#E6EDF3;"></span><b style="color:#E6EDF3;">Streamlit</b> Dashboard
        </div>""",
        unsafe_allow_html=True,
    )
    sb_divider()
    st.caption("Source: [Eurostat](https://ec.europa.eu/eurostat)  Data Engineering Zoomcamp")

#  Page header 
page_header(
    icon="",
    title="EU Economic Monitor",
    subtitle="GDP  Unemployment  Energy Intensity  Composite Index  18 EU Countries",
    badge=f"Updated {datetime.now().strftime('%b %Y')}",
)

#  Load data 
@st.cache_data(ttl=300)
def load_latest(countries):
    return get_country_latest(countries)

@st.cache_data(ttl=300)
def load_composite(start, end):
    return get_composite_index(start_year=start, end_year=end)

@st.cache_data(ttl=60)
def load_alerts(limit=8):
    return get_anomaly_alerts(limit=limit)

with st.spinner(""):
    try:
        df_latest    = load_latest(selected_country_codes)
        df_composite = load_composite(year_range[0], year_range[1])
        df_alerts    = load_alerts()
    except Exception as e:
        err_msg = str(e)
        if "Not found" in err_msg or "not found" in err_msg or "404" in err_msg:
            st.warning(
                "**BigQuery tables not yet available.** "
                "Run `make pipeline` to populate data. Showing empty placeholders.",
                icon="",
            )
        else:
            st.error(f"**Data load error:** {err_msg}", icon="")
        df_latest    = pd.DataFrame()
        df_composite = pd.DataFrame()
        df_alerts    = pd.DataFrame()

#  KPI row 
section_header("Economic Snapshot", f"{len(selected_country_codes)} countries")

latest_year_df = (
    df_latest[df_latest["country_code"].isin(selected_country_codes)]
    if not df_latest.empty else df_latest
)

def _mean(series) -> float:
    s = pd.Series(series).dropna()
    return float(s.mean()) if len(s) > 0 else 0.0

avg_gdp_growth = _mean(latest_year_df.get("gdp_yoy_growth_pct", pd.Series([])))
avg_unemp      = _mean(latest_year_df.get("unemployment_rate",  pd.Series([])))
avg_energy     = _mean(latest_year_df.get("energy_intensity",   pd.Series([])))
avg_composite  = _mean(latest_year_df.get("composite_score",    pd.Series([])))

top_country, top_score = "", 0.0
if not latest_year_df.empty and "composite_score" in latest_year_df.columns:
    best = latest_year_df.dropna(subset=["composite_score"]).nlargest(1, "composite_score")
    if not best.empty:
        top_country = str(best.iloc[0].get("country_name", ""))
        top_score   = float(best.iloc[0].get("composite_score", 0))

c1, c2, c3, c4, c5 = st.columns(5, gap="small")
with c1:
    kpi_card("GDP Growth (Avg)", f"{avg_gdp_growth:+.1f}%",
             delta="Year-on-Year avg", delta_up=avg_gdp_growth >= 0,
             icon="", accent="blue")
with c2:
    kpi_card("Unemployment", f"{avg_unemp:.1f}%",
             delta="Active population", icon="", accent="purple")
with c3:
    kpi_card("Energy Intensity", f"{avg_energy:.1f}",
             delta="kgoe / 1 000 EUR GDP", icon="", accent="teal")
with c4:
    kpi_card("Composite Score", f"{avg_composite:.0f}",
             delta="Scale 0  100", icon="", accent="amber")
with c5:
    kpi_card("Top Performer", top_country,
             delta=f"Score {top_score:.0f} / 100",
             delta_up=True, icon="", accent="green")

st.markdown("<div style='height:.65rem'></div>", unsafe_allow_html=True)

#  Map + Rankings 
col_map, col_rank = st.columns([3, 2], gap="medium")

with col_map:
    section_header("Composite Index  EU Map")

    map_df = pd.DataFrame()
    if not df_composite.empty and "composite_score" in df_composite.columns:
        latest_y = df_composite["reference_year"].max()
        map_df = df_composite[
            (df_composite["reference_year"] == latest_y) &
            (df_composite["country_code"].isin(selected_country_codes))
        ].copy()

    if not map_df.empty and "iso2" in map_df.columns:
        fig_map = eu_choropleth(
            map_df,
            value_col="composite_score",
            title="",
            colorscale="Blues",
            range_color=(0, 100),
        )
        fig_map.update_layout(height=430, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.info("Map data unavailable for the selected filters.")

with col_rank:
    section_header("Country Rankings")

    if not latest_year_df.empty and "composite_score" in latest_year_df.columns:
        rank_df = (
            latest_year_df[["country_code", "country_name", "composite_score",
                            "gdp_yoy_growth_pct", "unemployment_rate"]]
            .dropna(subset=["composite_score"])
            .sort_values("composite_score", ascending=False)
            .reset_index(drop=True)
        )
        max_score = rank_df["composite_score"].max() or 100

        rows_html = ""
        for i, row in rank_df.iterrows():
            flag    = FLAG_MAP.get(row["country_code"], "")
            pct     = int(row["composite_score"] / max_score * 100)
            gdp_d   = row.get("gdp_yoy_growth_pct", None)
            gdp_str = f"{gdp_d:+.1f}%" if pd.notna(gdp_d) else ""
            gdp_col = "#3FB950" if (pd.notna(gdp_d) and gdp_d >= 0) else "#F85149"
            rows_html += f"""
            <div class="rank-row">
                <span class="rank-num">#{i+1}</span>
                <span class="rank-flag">{flag}</span>
                <span class="rank-name">{row['country_name']}</span>
                <div class="rank-bar-track"><div class="rank-bar-fill" style="width:{pct}%"></div></div>
                <span class="rank-score">{row['composite_score']:.0f}</span>
                <span class="rank-gdp" style="color:{gdp_col}">{gdp_str}</span>
            </div>"""

        st.html(
            f"""<div style="background:#161B22;border:1px solid #21262D;border-radius:14px;
                            padding:.6rem .4rem;max-height:440px;overflow-y:auto;">
                <div style="display:flex;gap:.5rem;padding:.2rem .65rem .45rem;
                             color:#6E7681;font-size:.65rem;font-weight:700;
                             text-transform:uppercase;letter-spacing:.08em;
                             border-bottom:1px solid #21262D;margin-bottom:.3rem;">
                    <span style="width:1.4rem"></span>
                    <span style="width:1.4rem"></span>
                    <span style="flex:1">Country</span>
                    <span style="width:70px;text-align:right">Score</span>
                    <span style="width:3.2rem;text-align:right">GDP</span>
                </div>
                {rows_html}
            </div>"""
        )
    else:
        st.info("Ranking data unavailable.")

#  Composite score bar chart 
section_header("Composite Score by Country", "Latest available year  ranked")

if not map_df.empty and "composite_score" in map_df.columns and "country_name" in map_df.columns:
    bar_df = map_df.sort_values("composite_score", ascending=True)
    fig_bar = go.Figure(go.Bar(
        x=bar_df["composite_score"],
        y=bar_df["country_name"],
        orientation="h",
        text=[f"{v:.0f}" for v in bar_df["composite_score"]],
        textposition="outside",
        textfont=dict(color="#6E7681", size=11),
        marker=dict(
            color=bar_df["composite_score"],
            colorscale=[[0, "#0D2545"], [0.45, "#1F6FEB"], [1, "#79C0FF"]],
            cmin=0, cmax=100,
            line=dict(width=0),
        ),
    ))
    fig_bar.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#8B949E", family="Inter, sans-serif", size=12),
        height=max(300, len(bar_df) * 27),
        margin=dict(l=10, r=60, t=10, b=10),
        xaxis=dict(
            range=[0, 115], gridcolor="#21262D", showgrid=True,
            zeroline=False, tickfont=dict(color="#6E7681", size=11),
        ),
        yaxis=dict(
            gridcolor="rgba(0,0,0,0)",
            tickfont=dict(color="#E6EDF3", size=12),
        ),
        showlegend=False,
        bargap=0.22,
    )
    st.plotly_chart(fig_bar, use_container_width=True)

#  Anomaly alerts 
section_header("Anomaly Alerts", "Redpanda stream")

if not df_alerts.empty:
    for _, row in df_alerts.iterrows():
        sev       = str(row.get("severity", "LOW")).upper()
        country   = str(row.get("country_code", ""))
        flag      = FLAG_MAP.get(country, "")
        indicator = row.get("indicator", row.get("metric", ""))
        value     = row.get("value", row.get("z_score", ""))
        ts        = row.get("alert_timestamp", row.get("detected_at", ""))
        val_str   = f"{value:.2f}" if isinstance(value, (int, float)) else str(value)
        ts_str    = str(ts)[:16] if ts else ""
        st.markdown(
            f"""<div class="alert-card alert-{sev}">
                <span class="alert-pill alert-{sev}">{sev}</span>
                <div>
                    <div class="alert-title">{flag} {country}  {indicator}</div>
                    <div class="alert-meta">Value: {val_str} &nbsp;&nbsp; {ts_str}</div>
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
else:
    st.markdown(
        """<div style="background:#161B22;border:1px solid #21262D;border-left:3px solid #3FB950;
                       border-radius:10px;padding:.8rem 1rem;color:#3FB950;font-weight:600;
                       font-size:.86rem;display:flex;align-items:center;gap:.5rem;">
             &nbsp;No anomalies detected in the current data window.
        </div>""",
        unsafe_allow_html=True,
    )

#  Footer 
st.markdown(
    """<div class="dash-footer">
        EU Economic Monitor &nbsp;&nbsp; Data Engineering Zoomcamp Final Project &nbsp;&nbsp;
        Source: <a href="https://ec.europa.eu/eurostat">Eurostat</a>
    </div>""",
    unsafe_allow_html=True,
)
