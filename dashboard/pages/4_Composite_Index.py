"""
pages/4_Composite_Index.py
==========================
Composite economic index — radar charts, score breakdowns and rankings.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.bigquery_client import get_composite_index
from utils.charts import radar_composite, stacked_scores, bar_ranking, line_trend, CHART_LAYOUT, EU_BLUE, EU_GOLD
from utils.style import (
    inject_css, page_header, section_header, sidebar_logo, sb_divider, sb_label,
    FLAG_MAP, ALL_COUNTRIES,
)

st.set_page_config(page_title="Composite Index · EU Monitor", page_icon="📊", layout="wide")
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
    radar_country = st.selectbox(
        "Radar chart country",
        options=sel_countries if sel_countries else list(ALL.keys()),
        format_func=lambda c: f"{c} — {ALL.get(c, c)}",
    )
    sb_divider()
    sb_label("Methodology")
    st.caption(
        "The **Composite Economic Index** combines three normalised (0–100) sub-scores:"
        "\n- **GDP Growth Score** — higher growth = better"
        "\n- **Unemployment Score** — lower rate = better (inverted)"
        "\n- **Energy Score** — lower intensity = better (inverted)"
        "\nAll three are min-max normalised *within each year* across the EU, then averaged."
    )

@st.cache_data(ttl=300)
def load_composite(countries, y0, y1):
    return get_composite_index(countries=countries, start_year=y0, end_year=y1)

try:
    with st.spinner("Loading composite index data…"):
        df = load_composite(sel_countries, year_range[0], year_range[1])
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
    icon="📊",
    title="Composite Economic Index",
    subtitle="Min-max normalised score (0–100) combining GDP growth, unemployment, and energy efficiency · Higher = better",
)

# ── KPIs ───────────────────────────────────────────────────────────────────
if not df.empty:
    latest = df[df["reference_year"] == df["reference_year"].max()].drop_duplicates(subset=["country_name"])
    if not latest.empty and "composite_score" in latest.columns:
        avg_score  = latest["composite_score"].dropna().mean()
        top_row    = latest.dropna(subset=["composite_score"]).nlargest(1, "composite_score").iloc[0]
        bottom_row = latest.dropna(subset=["composite_score"]).nsmallest(1, "composite_score").iloc[0]
        med_score  = latest["composite_score"].dropna().median()

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("EU Average Score", f"{avg_score:.0f}/100")
        with c2:
            st.metric("Top Performer", top_row["country_name"], f"{top_row['composite_score']:.0f}/100")
        with c3:
            st.metric("Needs Improvement", bottom_row["country_name"], f"{bottom_row['composite_score']:.0f}/100")
        with c4:
            st.metric("Median Score", f"{med_score:.0f}/100")

# ── Tabs ───────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["🏆 Rankings", "📈 Trends", "🎯 Radar", "📦 Score Breakdown", "📋 Data"]
)

with tab1:
    section_header("Country Rankings — Latest Year")
    if not df.empty and "composite_score" in df.columns:
        latest = df[df["reference_year"] == df["reference_year"].max()].drop_duplicates(subset=["country_name"]).copy()

        col_tbl, col_bar = st.columns([1, 2], gap="large")
        with col_tbl:
            rank_df = (
                latest[["country_name", "composite_score", "gdp_score", "unemployment_score", "energy_score"]]
                .dropna(subset=["composite_score"])
                .sort_values("composite_score", ascending=False)
                .reset_index(drop=True)
            )
            rank_df.index += 1

            def _score_color(v):
                if v >= 70:
                    return f'<span class="score-pill" style="background:rgba(39,174,96,.25);color:#27AE60">{v:.0f}</span>'
                elif v >= 40:
                    return f'<span class="score-pill" style="background:rgba(243,156,18,.25);color:#F39C12">{v:.0f}</span>'
                else:
                    return f'<span class="score-pill" style="background:rgba(231,76,60,.25);color:#E74C3C">{v:.0f}</span>'

            html_rows = []
            for _, r in rank_df.iterrows():
                html_rows.append(
                    f"<tr>"
                    f"<td style='padding:.5rem .8rem;color:#9EA7BE'>{_}</td>"
                    f"<td style='padding:.5rem .8rem'>{r['country_name']}</td>"
                    f"<td style='padding:.5rem .8rem;text-align:center'>{_score_color(r['composite_score'])}</td>"
                    f"<td style='padding:.5rem .8rem;color:#9EA7BE;text-align:center'>{r.get('gdp_score', 0):.0f}</td>"
                    f"<td style='padding:.5rem .8rem;color:#9EA7BE;text-align:center'>{r.get('unemployment_score', 0):.0f}</td>"
                    f"<td style='padding:.5rem .8rem;color:#9EA7BE;text-align:center'>{r.get('energy_score', 0):.0f}</td>"
                    f"</tr>"
                )
            html_table = (
                "<table style='width:100%;border-collapse:collapse;font-family:Inter'>"
                "<thead><tr style='border-bottom:2px solid #2E3250'>"
                "<th style='padding:.5rem .8rem;color:#FFCC00'>#</th>"
                "<th style='padding:.5rem .8rem;color:#FFCC00;text-align:left'>Country</th>"
                "<th style='padding:.5rem .8rem;color:#FFCC00'>Composite</th>"
                "<th style='padding:.5rem .8rem;color:#9EA7BE'>GDP</th>"
                "<th style='padding:.5rem .8rem;color:#9EA7BE'>Unemp.</th>"
                "<th style='padding:.5rem .8rem;color:#9EA7BE'>Energy</th>"
                "</tr></thead><tbody>"
                + "".join(html_rows)
                + "</tbody></table>"
            )
            st.markdown(html_table, unsafe_allow_html=True)

        with col_bar:
            fig_rank = bar_ranking(
                latest.dropna(subset=["composite_score"]),
                x="composite_score", y="country_name",
                color_val="composite_score",
                title="Composite Score (0–100)",
                xaxis_title="Score",
                colorscale="RdYlGn",
            )
            fig_rank.update_layout(height=500)
            st.plotly_chart(fig_rank, use_container_width=True)
    else:
        st.info("No data available.")

with tab2:
    section_header("Composite Score Trends Over Time")
    if not df.empty and "composite_score" in df.columns:
        fig = line_trend(
            df, x="reference_year", y="composite_score", color="country_name",
            title="Composite Economic Index Over Time",
            yaxis_title="Composite Score (0–100)",
        )
        fig.update_layout(height=500)
        # Draw 50-point reference line
        fig.add_hline(
            y=50, line_dash="dot", line_color="rgba(255,204,0,0.4)",
            annotation_text="EU median", annotation_position="top left",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No trend data available.")

with tab3:
    section_header(f"Score Breakdown — {ALL.get(radar_country, radar_country)}")
    if not df.empty and radar_country:
        latest = df[df["reference_year"] == df["reference_year"].max()]
        country_data = latest[latest["country_code"] == radar_country]

        if not country_data.empty:
            row = country_data.iloc[0]
            col_r, col_m = st.columns([1, 1])
            with col_r:
                fig_radar = radar_composite(row, ALL.get(radar_country, radar_country))
                st.plotly_chart(fig_radar, use_container_width=True)
            with col_m:
                st.markdown(f"### {ALL.get(radar_country, radar_country)} Scores")
                scores = {
                    "Composite Score": row.get("composite_score", 0),
                    "GDP Growth Score": row.get("gdp_score", 0),
                    "Unemployment Score": row.get("unemployment_score", 0),
                    "Energy Efficiency Score": row.get("energy_score", 0),
                }
                for label, val in scores.items():
                    if val > 70:
                        color, bg = "#27AE60", "rgba(39,174,96,.15)"
                        tier = "🟢 Strong"
                    elif val > 40:
                        color, bg = "#F39C12", "rgba(243,156,18,.15)"
                        tier = "🟡 Moderate"
                    else:
                        color, bg = "#E74C3C", "rgba(231,76,60,.15)"
                        tier = "🔴 Weak"

                    st.markdown(
                        f"""<div style="background:{bg};border:1px solid {color};border-radius:8px;
                        padding:.6rem 1rem;margin:.4rem 0">
                        <div style="color:#9EA7BE;font-size:.8rem">{label}</div>
                        <div style="color:{color};font-size:1.4rem;font-weight:700">{val:.0f}/100</div>
                        <div style="color:#9EA7BE;font-size:.8rem">{tier}</div>
                        </div>""",
                        unsafe_allow_html=True,
                    )
        else:
            st.info(f"No data found for {radar_country} in the latest year.")
    else:
        st.info("Select a country in the sidebar.")

with tab4:
    section_header("Score Components Over Time")
    if not df.empty and radar_country and "gdp_score" in df.columns:
        c_df = df[df["country_code"] == radar_country].sort_values("reference_year")
        if not c_df.empty:
            fig_stack = go.Figure()
            components = [
                ("gdp_score", "GDP Score", EU_BLUE),
                ("unemployment_score", "Unemployment Score", EU_GOLD),
                ("energy_score", "Energy Score", "#27AE60"),
            ]
            for col, label, color in components:
                if col in c_df.columns:
                    fig_stack.add_trace(go.Bar(
                        x=c_df["reference_year"],
                        y=c_df[col] / 3,
                        name=label,
                        marker_color=color,
                    ))
            fig_stack.add_trace(go.Scatter(
                x=c_df["reference_year"],
                y=c_df["composite_score"],
                name="Composite Score",
                mode="lines+markers",
                line=dict(color="#FFFFFF", width=2),
                marker=dict(size=6),
                yaxis="y2",
            ))
            fig_stack.update_layout(
                **CHART_LAYOUT,
                barmode="stack",
                title=f"Score Component Breakdown — {ALL.get(radar_country, radar_country)}",
                xaxis_title="Year",
                yaxis_title="Component Contribution",
                yaxis2=dict(
                    title="Composite Score",
                    overlaying="y",
                    side="right",
                    gridcolor="rgba(0,0,0,0)",
                    range=[0, 100],
                    tickfont=dict(color="#FFFFFF"),
                ),
                height=480,
            )
            fig_stack.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02))
            st.plotly_chart(fig_stack, use_container_width=True)
        else:
            st.info(f"No data for {radar_country}.")

with tab5:
    section_header("Full Dataset")
    if not df.empty:
        disp_cols = [c for c in
                     ["country_name", "reference_year", "composite_score",
                      "gdp_score", "unemployment_score", "energy_score"]
                     if c in df.columns]
        disp = df[disp_cols].copy()
        disp.columns = [c.replace("_", " ").title() for c in disp.columns]
        st.dataframe(disp, use_container_width=True, height=500)
        st.download_button(
            "⬇️ Download CSV",
            df.to_csv(index=False).encode("utf-8"),
            "eu_composite_index.csv", "text/csv",
        )
    else:
        st.info("No data loaded.")
