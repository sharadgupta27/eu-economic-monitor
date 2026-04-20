"""
pages/3_Energy_Intensity.py
===========================
Energy intensity trends, GDP vs energy scatter, and efficiency rankings.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.bigquery_client import get_energy_intensity, get_gdp_trends
from utils.charts import line_trend, bar_ranking, heatmap_country_year, scatter_gdp_energy, CHART_LAYOUT
from utils.style import (
    inject_css, page_header, section_header, sidebar_logo, sb_divider, sb_label,
    FLAG_MAP, ALL_COUNTRIES,
)

st.set_page_config(page_title="Energy Intensity · EU Monitor", page_icon="⚡", layout="wide")
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
    year_range = st.slider("Year range", 2000, 2023, (2000, 2023))
    scatter_year = st.slider("Scatter plot year", 2000, 2023, 2022)

@st.cache_data(ttl=300)
def load_energy(countries, y0, y1):
    return get_energy_intensity(countries=countries, start_year=y0, end_year=y1)

@st.cache_data(ttl=300)
def load_gdp(countries, y0, y1):
    return get_gdp_trends(countries=countries, start_year=y0, end_year=y1)

try:
    with st.spinner("Fetching energy data…"):
        df_energy = load_energy(sel_countries, year_range[0], year_range[1])
        df_gdp    = load_gdp(sel_countries, year_range[0], year_range[1])
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
    icon="⚡",
    title="Energy Intensity Analysis",
    subtitle="Source: Eurostat — nrg_ind_ei · kgoe per 1,000 EUR GDP (2015 prices) · Lower = more efficient",
)

# KPIs
if not df_energy.empty:
    latest = df_energy[df_energy["reference_year"] == df_energy["reference_year"].max()]
    avg_ei = latest["energy_intensity"].dropna().mean()
    most_eff = latest.dropna(subset=["energy_intensity"]).nsmallest(1, "energy_intensity")
    least_eff = latest.dropna(subset=["energy_intensity"]).nlargest(1, "energy_intensity")

    # Overall improvement: compare first and last year of selection
    if "energy_intensity" in df_energy.columns and df_energy["reference_year"].nunique() > 1:
        y_first = df_energy["reference_year"].min()
        y_last  = df_energy["reference_year"].max()
        avg_first = df_energy[df_energy["reference_year"] == y_first]["energy_intensity"].dropna().mean()
        avg_last  = df_energy[df_energy["reference_year"] == y_last]["energy_intensity"].dropna().mean()
        improvement = (avg_first - avg_last) / avg_first * 100 if avg_first else 0.0
    else:
        improvement = 0.0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("EU Average (latest)", f"{avg_ei:.1f} kgoe/1k€")
    with c2:
        if not most_eff.empty:
            r = most_eff.iloc[0]
            st.metric("Most Efficient", r["country_name"], f"{r['energy_intensity']:.1f} kgoe/1k€")
    with c3:
        if not least_eff.empty:
            r = least_eff.iloc[0]
            st.metric("Least Efficient", r["country_name"], f"{r['energy_intensity']:.1f} kgoe/1k€")
    with c4:
        sign = "▼" if improvement > 0 else "▲"
        st.metric(
            "Overall Improvement",
            f"{improvement:.1f}%",
            f"{sign} since {df_energy['reference_year'].min()}",
        )

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📉 Trends", "🔥 Heatmap", "🔴 GDP vs Energy", "🏆 Rankings", "📋 Data"]
)

with tab1:
    section_header("Energy Intensity Over Time")
    if not df_energy.empty:
        fig = line_trend(
            df_energy, x="reference_year", y="energy_intensity", color="country_name",
            title="Energy Intensity (kgoe / 1 000 EUR GDP)",
            yaxis_title="kgoe per 1 000 EUR",
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("📌 Efficiency Drivers"):
            st.markdown("""
            Energy intensity has declined across the EU due to:
            - **Fuel switching** — shifting from coal/oil to gas + renewables
            - **Energy efficiency policies** — EU Energy Efficiency Directive (EED)
            - **Industrial de-carbonisation** — heavy industry moving to cleaner processes
            - **Service sector growth** — less energy-heavy than manufacturing
            - **2022 energy crisis** — accelerated efficiency investments
            """)
    else:
        st.info("No energy data available for the selected filters.")

with tab2:
    section_header("Heatmap — Country × Year")
    if not df_energy.empty:
        fig_heat = heatmap_country_year(
            df_energy, value_col="energy_intensity",
            title="Energy Intensity by Country and Year (kgoe/1k€)",
            colorscale="YlOrRd_r",
        )
        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("No heatmap data.")

with tab3:
    section_header(f"GDP vs Energy Intensity ({scatter_year})")
    if not df_energy.empty and not df_gdp.empty:
        merged = pd.merge(
            df_energy[df_energy["reference_year"] == scatter_year][["country_code", "country_name", "energy_intensity", "reference_year"]],
            df_gdp[df_gdp["reference_year"] == scatter_year][["country_code", "gdp_beur"]],
            on="country_code", how="inner",
        )
        if not merged.empty:
            merged["gdp_beur"] = merged["gdp_beur"].fillna(0)
            fig_scatter = px.scatter(
                merged,
                x="gdp_beur",
                y="energy_intensity",
                text="country_code",
                size="gdp_beur",
                size_max=40,
                color="energy_intensity",
                color_continuous_scale="RdYlGn_r",
                hover_name="country_name",
                labels={
                    "gdp_beur": "GDP (Billion EUR)",
                    "energy_intensity": "Energy Intensity (kgoe/1k€)",
                },
                title=f"GDP Size vs Energy Intensity — {scatter_year}",
            )
            fig_scatter.update_traces(textposition="top center", marker=dict(opacity=0.85))
            fig_scatter.update_layout(
                **CHART_LAYOUT,
                height=480,
                coloraxis_colorbar=dict(bgcolor="#1E2130", tickfont=dict(color="#FAFAFA")),
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
            st.caption(
                "💡 Larger bubble = bigger economy. "
                "Lower on the Y-axis = more energy efficient per unit of GDP."
            )
        else:
            st.info("No matched data for the selected year.")
    else:
        st.info("Need both energy and GDP data to render this chart.")

with tab4:
    section_header("Efficiency Rankings — Latest Year")
    if not df_energy.empty:
        col_a, col_b = st.columns(2)
        latest = df_energy[df_energy["reference_year"] == df_energy["reference_year"].max()].copy()

        with col_a:
            fig_rank = bar_ranking(
                latest.dropna(subset=["energy_intensity"]),
                x="energy_intensity", y="country_name",
                color_val="energy_intensity",
                title="Energy Intensity Ranking (lower = better)",
                xaxis_title="kgoe / 1 000 EUR",
                colorscale="RdYlGn_r",
            )
            st.plotly_chart(fig_rank, use_container_width=True)

        with col_b:
            if "energy_yoy_improvement" in latest.columns:
                fig_imp = bar_ranking(
                    latest.dropna(subset=["energy_yoy_improvement"]),
                    x="energy_yoy_improvement", y="country_name",
                    color_val="energy_yoy_improvement",
                    title="YoY Efficiency Improvement (%)",
                    xaxis_title="%",
                    colorscale="RdYlGn",
                )
                st.plotly_chart(fig_imp, use_container_width=True)

with tab5:
    section_header("Full Dataset")
    if not df_energy.empty:
        disp = df_energy[[c for c in
                           ["country_name", "reference_year", "energy_intensity", "energy_yoy_improvement"]
                           if c in df_energy.columns]].copy()
        disp.columns = [c.replace("_"," ").title() for c in disp.columns]
        st.dataframe(disp, use_container_width=True, height=480)
        st.download_button(
            "⬇️ Download CSV",
            df_energy.to_csv(index=False).encode("utf-8"),
            "eu_energy_intensity.csv", "text/csv",
        )
    else:
        st.info("No data loaded.")
