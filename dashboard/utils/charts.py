"""
utils/charts.py
===============
Reusable Plotly chart builders with a consistent EU-branded theme.
"""

from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# ---------------------------------------------------------------------------
# Palette — refined dark theme
# ---------------------------------------------------------------------------
EU_BLUE    = "#1F6FEB"
EU_GOLD    = "#58A6FF"
EU_LIGHT   = "#79C0FF"
CARD_BG    = "#161B22"
TEXT_COLOR = "#E6EDF3"
TEXT_MUTED = "#8B949E"
GRID_COLOR = "#21262D"
BG_COLOR   = "#0D1117"

COUNTRY_COLOR_SEQ = [
    "#1F6FEB", "#58A6FF", "#3FB950", "#D29922", "#F85149",
    "#A371F7", "#0D9488", "#E3B341", "#79C0FF", "#56D364",
    "#FF7B72", "#D2A8FF", "#2EA043", "#F0883E", "#388BFD",
]

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=TEXT_MUTED, family="Inter, sans-serif", size=12),
    xaxis=dict(gridcolor=GRID_COLOR, showgrid=True, zeroline=False,
               tickfont=dict(color=TEXT_MUTED, size=11), linecolor=GRID_COLOR),
    yaxis=dict(gridcolor=GRID_COLOR, showgrid=True, zeroline=False,
               tickfont=dict(color=TEXT_MUTED, size=11), linecolor=GRID_COLOR),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=GRID_COLOR, borderwidth=1,
                font=dict(color=TEXT_MUTED, size=11)),
    margin=dict(l=40, r=20, t=45, b=40),
    hoverlabel=dict(bgcolor=CARD_BG, bordercolor=GRID_COLOR, font_color=TEXT_COLOR),
)


def _apply_theme(fig: go.Figure) -> go.Figure:
    fig.update_layout(**CHART_LAYOUT)
    return fig


# ---------------------------------------------------------------------------
# iso-2 → iso-3 lookup for choropleth
_ISO2_TO_ISO3: dict[str, str] = {
    "AT": "AUT", "BE": "BEL", "CZ": "CZE", "DE": "DEU", "DK": "DNK",
    "EL": "GRC", "ES": "ESP", "FI": "FIN", "FR": "FRA", "HU": "HUN",
    "IE": "IRL", "IT": "ITA", "NL": "NLD", "PL": "POL", "PT": "PRT",
    "RO": "ROU", "SE": "SWE", "SK": "SVK",
}

# Choropleth — EU map
# ---------------------------------------------------------------------------
def eu_choropleth(df: pd.DataFrame, value_col: str, title: str,
                  colorscale: str = "RdYlGn", range_color: tuple | None = None) -> go.Figure:
    """Filled choropleth restricted to Europe."""
    df = df.copy()
    df["iso3"] = df["iso2"].map(_ISO2_TO_ISO3)
    fig = px.choropleth(
        df,
        locations="iso3",
        locationmode="ISO-3",
        color=value_col,
        hover_name="country_name",
        hover_data={value_col: ":.2f", "iso3": False},
        color_continuous_scale=colorscale,
        range_color=range_color,
        scope="europe",
        title=title,
        labels={value_col: value_col.replace("_", " ").title()},
    )
    fig.update_geos(
        showcoastlines=True, coastlinecolor="#21262D",
        showland=True, landcolor="#161B22",
        showocean=True, oceancolor="#0D1117",
        showlakes=True, lakecolor="#0D1117",
        showframe=False,
        projection_type="natural earth",
        lataxis_range=[34, 72],
        lonaxis_range=[-25, 45],
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        geo_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT_COLOR, family="Inter, sans-serif"),
        coloraxis_colorbar=dict(
            bgcolor=CARD_BG,
            tickfont=dict(color=TEXT_MUTED),
            title=dict(font=dict(color=TEXT_MUTED)),
            thickness=14,
            len=0.8,
        ),
        margin=dict(l=0, r=0, t=40, b=0),
        height=440,
    )
    return fig


# ---------------------------------------------------------------------------
# Line chart — trends over time
# ---------------------------------------------------------------------------
def line_trend(df: pd.DataFrame, x: str, y: str, color: str,
               title: str, yaxis_title: str = "") -> go.Figure:
    fig = px.line(
        df, x=x, y=y, color=color,
        title=title,
        labels={y: yaxis_title or y, x: "Year", color: "Country"},
        color_discrete_sequence=COUNTRY_COLOR_SEQ,
        markers=True,
    )
    fig.update_traces(line=dict(width=2), marker=dict(size=5))
    _apply_theme(fig)
    fig.update_layout(yaxis_title=yaxis_title, xaxis_title="Year", height=420)
    return fig


# ---------------------------------------------------------------------------
# Horizontal bar — ranking
# ---------------------------------------------------------------------------
def bar_ranking(df: pd.DataFrame, x: str, y: str, color_val: str | None,
                title: str, xaxis_title: str = "", colorscale: str = "RdYlGn") -> go.Figure:
    df = df.sort_values(x, ascending=True)
    if color_val:
        fig = px.bar(
            df, x=x, y=y, orientation="h",
            color=color_val,
            color_continuous_scale=colorscale,
            title=title,
            labels={x: xaxis_title or x, y: ""},
        )
    else:
        fig = px.bar(
            df, x=x, y=y, orientation="h",
            title=title,
            labels={x: xaxis_title or x, y: ""},
            color_discrete_sequence=[EU_GOLD],
        )
    _apply_theme(fig)
    fig.update_layout(height=max(350, len(df) * 28), xaxis_title=xaxis_title, yaxis_title="")
    return fig


# ---------------------------------------------------------------------------
# Heatmap — countries × years
# ---------------------------------------------------------------------------
def heatmap_country_year(df: pd.DataFrame, value_col: str, title: str,
                         colorscale: str = "RdYlGn") -> go.Figure:
    pivot = df.pivot_table(index="country_name", columns="reference_year", values=value_col)
    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=[str(c) for c in pivot.columns],
            y=pivot.index.tolist(),
            colorscale=colorscale,
            hovertemplate="Country: %{y}<br>Year: %{x}<br>Value: %{z:.2f}<extra></extra>",
            colorbar=dict(bgcolor=CARD_BG, tickfont=dict(color=TEXT_MUTED)),
        )
    )
    _apply_theme(fig)
    fig.update_layout(
        title=title,
        xaxis_title="Year",
        yaxis_title="",
        height=max(350, len(pivot) * 26),
    )
    return fig


# ---------------------------------------------------------------------------
# Radar — composite score breakdown
# ---------------------------------------------------------------------------
def radar_composite(df_row: pd.Series, country: str) -> go.Figure:
    categories = ["GDP Score", "Unemployment Score", "Energy Score"]
    values = [
        float(df_row.get("gdp_score", 50)),
        float(df_row.get("unemployment_score", 50)),
        float(df_row.get("energy_score", 50)),
    ]
    values_closed = values + [values[0]]
    categories_closed = categories + [categories[0]]

    fig = go.Figure(
        go.Scatterpolar(
            r=values_closed,
            theta=categories_closed,
            fill="toself",
            fillcolor=f"rgba(0, 51, 153, 0.4)",
            line=dict(color=EU_GOLD, width=2),
            name=country,
        )
    )
    fig.update_layout(
        polar=dict(
            bgcolor=CARD_BG,
            radialaxis=dict(visible=True, range=[0, 100], gridcolor=GRID_COLOR,
                            tickfont=dict(color=TEXT_MUTED)),
            angularaxis=dict(gridcolor=GRID_COLOR, tickfont=dict(color=TEXT_MUTED, size=12)),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT_MUTED),
        showlegend=False,
        title=f"{country} — Score Breakdown",
        height=380,
    )
    return fig


# ---------------------------------------------------------------------------
# Stacked bar — score components over time
# ---------------------------------------------------------------------------
def stacked_scores(df: pd.DataFrame, country_code: str) -> go.Figure:
    c = df[df["country_code"] == country_code].sort_values("reference_year")
    fig = go.Figure()
    components = {
        "gdp_score": ("GDP Score", EU_BLUE),
        "unemployment_score": ("Unemployment Score", EU_GOLD),
        "energy_score": ("Energy Score", "#27AE60"),
    }
    for col, (label, color) in components.items():
        if col in c.columns:
            fig.add_trace(go.Bar(
                x=c["reference_year"], y=c[col] / 3,
                name=label, marker_color=color,
            ))
    fig.update_layout(
        barmode="stack",
        title=f"Composite Score Components — {country_code}",
        xaxis_title="Year",
        yaxis_title="Score Component (0-100/3)",
        **CHART_LAYOUT,
        height=380,
    )
    return fig


# ---------------------------------------------------------------------------
# Scatter — GDP vs Energy Intensity
# ---------------------------------------------------------------------------
def scatter_gdp_energy(df: pd.DataFrame, year: int) -> go.Figure:
    subset = df[df["reference_year"] == year]
    fig = px.scatter(
        subset,
        x="gdp_beur",
        y="energy_intensity",
        text="country_code",
        size_max=20,
        title=f"GDP vs Energy Intensity ({year})",
        labels={
            "gdp_beur": "GDP (Billion EUR)",
            "energy_intensity": "Energy Intensity (kgoe/1000 EUR)",
            "country_code": "Country",
        },
        color="composite_score" if "composite_score" in subset.columns else None,
        color_continuous_scale="RdYlGn",
    )
    fig.update_traces(textposition="top center", marker=dict(size=14, opacity=0.85))
    _apply_theme(fig)
    fig.update_layout(height=450)
    return fig
