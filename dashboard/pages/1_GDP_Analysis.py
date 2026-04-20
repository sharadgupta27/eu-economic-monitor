"""
pages/1_GDP_Analysis.py
=======================
GDP trends, rankings and year-on-year growth rates.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.bigquery_client import get_gdp_trends, get_country_latest
from utils.charts import line_trend, bar_ranking, heatmap_country_year, CHART_LAYOUT
from utils.style import (
    inject_css, page_header, section_header, sidebar_logo, sb_divider, sb_label,
    FLAG_MAP, ALL_COUNTRIES,
)

st.set_page_config(page_title="GDP Analysis · EU Monitor", page_icon="📈", layout="wide")
inject_css()


# ── CSS (shared dark theme) ────────────────────────────────────────────────

# ── Sidebar filters ────────────────────────────────────────────────────────
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
        default=["DE","FR","IT","ES","PL","NL","SE"],
        format_func=lambda c: f"{c} — {ALL[c]}",
    )
    year_range = st.slider("Year range", 2000, 2023, (2005, 2023))
    chart_unit = st.radio("GDP Unit", ["Billion EUR", "Annual Growth %"], horizontal=True)

# ── Load data ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_gdp(countries, y0, y1):
    return get_gdp_trends(countries=countries, start_year=y0, end_year=y1)

try:
    with st.spinner("Fetching GDP data…"):
        df = load_gdp(sel_countries, year_range[0], year_range[1])
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
    icon="📈",
    title="GDP Analysis",
    subtitle="Source: Eurostat — nama_10_gdp · Unit: Millions EUR (current prices)",
)

# ── KPI row ────────────────────────────────────────────────────────────────
if not df.empty:
    latest = df[df["reference_year"] == df["reference_year"].max()]
    avg_growth = latest["gdp_yoy_growth_pct"].dropna().mean()
    top_gdp_row = latest.dropna(subset=["gdp_beur"]).nlargest(1, "gdp_beur").iloc[0] if not latest.empty else None
    fastest_row = latest.dropna(subset=["gdp_yoy_growth_pct"]).nlargest(1, "gdp_yoy_growth_pct").iloc[0] if not latest.empty else None

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Average GDP Growth", f"{avg_growth:+.1f}%", help="Mean YoY growth across selected countries")
    with c2:
        if top_gdp_row is not None:
            st.metric("Largest Economy", f"{top_gdp_row['country_name']}",
                      f"{top_gdp_row['gdp_beur']:.0f}B EUR")
    with c3:
        if fastest_row is not None:
            st.metric("Fastest Growing", f"{fastest_row['country_name']}",
                      f"{fastest_row['gdp_yoy_growth_pct']:+.1f}%")

# ── Tabs ───────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📊 Trend Lines", "🏆 Rankings", "🔥 Growth Heatmap", "📋 Data Table"])

with tab1:
    section_header("GDP Over Time")
    if not df.empty:
        y_col = "gdp_beur" if chart_unit == "Billion EUR" else "gdp_yoy_growth_pct"
        y_label = "GDP (Billion EUR)" if chart_unit == "Billion EUR" else "GDP Growth (%)"
        fig = line_trend(df, x="reference_year", y=y_col, color="country_name",
                         title=f"{chart_unit} by Country", yaxis_title=y_label)
        fig.update_layout(height=480)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No GDP trend data available for the selected filters.")

with tab2:
    section_header("Latest Year Rankings")
    if not df.empty:
        latest = df[df["reference_year"] == df["reference_year"].max()].copy()
        col_a, col_b = st.columns(2)
        with col_a:
            if "gdp_beur" in latest.columns:
                fig_gdp_rank = bar_ranking(
                    latest.dropna(subset=["gdp_beur"]),
                    x="gdp_beur", y="country_name",
                    color_val="gdp_beur",
                    title="GDP Size (Billion EUR)",
                    xaxis_title="Billion EUR",
                    colorscale="Blues",
                )
                st.plotly_chart(fig_gdp_rank, use_container_width=True)
        with col_b:
            if "gdp_yoy_growth_pct" in latest.columns:
                fig_growth_rank = bar_ranking(
                    latest.dropna(subset=["gdp_yoy_growth_pct"]),
                    x="gdp_yoy_growth_pct", y="country_name",
                    color_val="gdp_yoy_growth_pct",
                    title="GDP Growth Rate (%)",
                    xaxis_title="% YoY",
                    colorscale="RdYlGn",
                )
                st.plotly_chart(fig_growth_rank, use_container_width=True)

with tab3:
    section_header("Year-on-Year GDP Growth Heatmap")
    if not df.empty and "gdp_yoy_growth_pct" in df.columns:
        fig_heat = heatmap_country_year(
            df, value_col="gdp_yoy_growth_pct",
            title="GDP YoY Growth (%) by Country and Year",
            colorscale="RdYlGn",
        )
        st.plotly_chart(fig_heat, use_container_width=True)

        # Highlight notable events
        with st.expander("📌 Notable Events"):
            st.markdown("""
            - **2009** — Global Financial Crisis (sharp GDP contraction across EU)
            - **2010–2011** — Eurozone sovereign debt crisis (severe impact on EL, PT, IE, ES)
            - **2020** — COVID-19 pandemic (record GDP collapse across all EU members)
            - **2021** — Strong rebound as economies reopened
            - **2022–2023** — Energy crisis + high inflation dampened growth
            """)
    else:
        st.info("Heatmap data unavailable.")

with tab4:
    section_header("Full Dataset")
    if not df.empty:
        display_cols = [c for c in ["country_name", "reference_year", "gdp_beur", "gdp_yoy_growth_pct"]
                        if c in df.columns]
        fmt_df = df[display_cols].copy()
        fmt_df.columns = [c.replace("_"," ").title() for c in fmt_df.columns]
        st.dataframe(fmt_df, use_container_width=True, height=480)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download CSV", csv, "eu_gdp_data.csv", "text/csv")
    else:
        st.info("No data loaded.")
