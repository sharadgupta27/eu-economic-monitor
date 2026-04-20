"""
pages/2_Unemployment.py
=======================
Unemployment rate trends, heatmaps and country comparisons.
"""

import streamlit as st
import pandas as pd
import plotly.express as px

from utils.bigquery_client import get_unemployment
from utils.charts import line_trend, bar_ranking, heatmap_country_year
from utils.style import (
    inject_css, page_header, section_header, sidebar_logo, sb_divider, sb_label,
    FLAG_MAP, ALL_COUNTRIES,
)

st.set_page_config(page_title="Unemployment · EU Monitor", page_icon="👷", layout="wide")
inject_css()



ALL = {
    "AT":"Austria","BE":"Belgium","CZ":"Czechia","DE":"Germany","DK":"Denmark",
    "EL":"Greece","ES":"Spain","FI":"Finland","FR":"France","HU":"Hungary",
    "IE":"Ireland","IT":"Italy","NL":"Netherlands","PL":"Poland","PT":"Portugal",
    "RO":"Romania","SE":"Sweden","SK":"Slovakia",
}

with st.sidebar:
    sidebar_logo()
    sb_divider()

    sb_label("Filters")
    sel_countries = st.multiselect(
        "Countries",
        options=list(ALL.keys()),
        default=list(ALL.keys()),
        format_func=lambda c: f"{c} — {ALL[c]}",
    )
    year_range = st.slider("Year range", 2000, 2023, (2005, 2023))

@st.cache_data(ttl=300)
def load_unemp(countries, y0, y1):
    return get_unemployment(countries=countries, start_year=y0, end_year=y1)

try:
    with st.spinner("Fetching unemployment data…"):
        df = load_unemp(sel_countries, year_range[0], year_range[1])
except Exception as e:
    err = str(e)
    if any(k in err for k in ("Not found", "not found", "404", "does not exist")):
        st.warning(
            "⏳ **BigQuery tables not yet available.** "
            "Run `make pipeline` (or `make ingest` → `make spark-batch` → `make dbt-run`) to populate data.",
            icon="⚠️",
        )
    else:
        st.error(f"**Data load error:** {err}", icon="🚨")
    st.stop()

page_header(
    icon="👷",
    title="Unemployment Analysis",
    subtitle="Source: Eurostat — une_rt_a · Total unemployment rate as % of active population",
)

# KPIs
if not df.empty:
    latest = df[df["reference_year"] == df["reference_year"].max()]
    avg_unemp = latest["unemployment_rate"].dropna().mean()
    lowest = latest.dropna(subset=["unemployment_rate"]).nsmallest(1, "unemployment_rate").iloc[0] if not latest.empty else None
    highest = latest.dropna(subset=["unemployment_rate"]).nlargest(1, "unemployment_rate").iloc[0] if not latest.empty else None
    yoy_avg = latest["unemp_yoy_change"].dropna().mean() if "unemp_yoy_change" in latest.columns else None

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("EU Average (latest)", f"{avg_unemp:.1f}%")
    with c2:
        if lowest is not None:
            st.metric("Lowest Rate", f"{lowest['country_name']}",
                      f"{lowest['unemployment_rate']:.1f}%")
    with c3:
        if highest is not None:
            st.metric("Highest Rate", f"{highest['country_name']}",
                      f"{highest['unemployment_rate']:.1f}%")
    with c4:
        if yoy_avg is not None:
            delta_sym = "▲" if yoy_avg > 0 else "▼"
            st.metric("Avg YoY Change", f"{yoy_avg:+.2f} pp",
                      help="Percentage point change vs previous year")

tab1, tab2, tab3, tab4 = st.tabs(["📉 Trend Lines", "🔥 Heatmap", "🏆 Rankings", "📋 Data"])

with tab1:
    section_header("Unemployment Rate Over Time")
    if not df.empty:
        fig = line_trend(
            df, x="reference_year", y="unemployment_rate", color="country_name",
            title="Unemployment Rate (% of active population)",
            yaxis_title="Unemployment Rate (%)",
        )
        fig.update_layout(height=500)

        # Add reference lines
        fig.add_hline(
            y=df["unemployment_rate"].dropna().mean(),
            line_dash="dash", line_color="rgba(255,204,0,0.6)",
            annotation_text="EU avg", annotation_position="top right",
        )
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("📌 Key Labour Market Events"):
            st.markdown("""
            - **2008–2013** — Financial crisis caused unemployment to surge across southern Europe
            - **2013** — Euro-area peak unemployment (~12%); Greece and Spain exceeded 25%
            - **2020** — COVID-19 — temporary spike followed by government job-retention schemes limiting impact
            - **2022–2023** — Record-low unemployment in many EU states driven by tight labour markets
            """)
    else:
        st.info("No data available.")

with tab2:
    section_header("Unemployment Heatmap — Country × Year")
    if not df.empty:
        fig_heat = heatmap_country_year(
            df, value_col="unemployment_rate",
            title="Unemployment Rate (%) — Darker = Higher",
            colorscale="YlOrRd",
        )
        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("No heatmap data.")

with tab3:
    section_header("Country Rankings — Latest Year")
    if not df.empty:
        col_a, col_b = st.columns(2)
        latest = df[df["reference_year"] == df["reference_year"].max()].copy()

        with col_a:
            fig_rank = bar_ranking(
                latest.dropna(subset=["unemployment_rate"]),
                x="unemployment_rate", y="country_name",
                color_val="unemployment_rate",
                title="Unemployment Rate — Best to Worst",
                xaxis_title="% of active population",
                colorscale="RdYlGn_r",
            )
            st.plotly_chart(fig_rank, use_container_width=True)

        with col_b:
            if "unemp_yoy_change" in latest.columns:
                fig_yoy = bar_ranking(
                    latest.dropna(subset=["unemp_yoy_change"]),
                    x="unemp_yoy_change", y="country_name",
                    color_val="unemp_yoy_change",
                    title="YoY Change (pp) — Improvement vs Deterioration",
                    xaxis_title="Percentage point change",
                    colorscale="RdYlGn_r",
                )
                st.plotly_chart(fig_yoy, use_container_width=True)

with tab4:
    section_header("Full Dataset")
    if not df.empty:
        disp = df[[c for c in ["country_name", "reference_year", "unemployment_rate", "unemp_yoy_change"]
                   if c in df.columns]].copy()
        disp.columns = [c.replace("_"," ").title() for c in disp.columns]
        st.dataframe(disp, use_container_width=True, height=480)
        st.download_button(
            "⬇️ Download CSV",
            df.to_csv(index=False).encode("utf-8"),
            "eu_unemployment.csv", "text/csv",
        )
    else:
        st.info("No data loaded.")
