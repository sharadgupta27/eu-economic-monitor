"""
utils/bigquery_client.py
==========================
Thin wrapper around google-cloud-bigquery that returns
pandas DataFrames ready for Plotly/Streamlit.

Set USE_MOCK_DATA=true in the environment to get synthetic
data without a live GCP connection (useful for local demo).
"""

from __future__ import annotations

import logging
import os

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

USE_MOCK   = os.getenv("USE_MOCK_DATA", "false").lower() == "true"
PROJECT    = os.getenv("GCP_PROJECT_ID", "")
DATASET    = os.getenv("BQ_PROCESSED_DATASET", "eurostat_processed")

# ---------------------------------------------------------------------------
# Country metadata
# ---------------------------------------------------------------------------
EU_COUNTRIES = {
    "AT": "Austria",     "BE": "Belgium",     "CZ": "Czechia",
    "DE": "Germany",     "DK": "Denmark",     "EL": "Greece",
    "ES": "Spain",       "FI": "Finland",     "FR": "France",
    "HU": "Hungary",     "IE": "Ireland",     "IT": "Italy",
    "NL": "Netherlands", "PL": "Poland",      "PT": "Portugal",
    "RO": "Romania",     "SE": "Sweden",      "SK": "Slovakia",
}

# Eurostat → ISO 3166-1 alpha-2 mapping for Plotly choropleth
EUROSTAT_TO_ISO2 = {
    "EL": "GR",
}


def to_iso2(code: str) -> str:
    return EUROSTAT_TO_ISO2.get(code, code)


# ---------------------------------------------------------------------------
# BigQuery helpers
# ---------------------------------------------------------------------------
def _bq_client():
    from google.cloud import bigquery
    return bigquery.Client(project=PROJECT)


def _query(sql: str) -> pd.DataFrame:
    client = _bq_client()
    return client.query(sql).to_dataframe()


# ---------------------------------------------------------------------------
# Mock data generator
# ---------------------------------------------------------------------------
def _mock_gdp_trends() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    rows = []
    for code, name in EU_COUNTRIES.items():
        base = rng.uniform(100, 4000)
        growth = rng.uniform(-0.02, 0.05)
        for yr in range(2000, 2024):
            rows.append({
                "country_code": code,
                "country_name": name,
                "reference_year": yr,
                "reference_date": pd.Timestamp(f"{yr}-01-01"),
                "gdp_beur": round(base, 2),
                "gdp_yoy_growth_pct": round(float(growth * 100 + rng.normal(0, 1)), 2),
            })
            base *= (1 + growth + rng.normal(0, 0.01))
    return pd.DataFrame(rows)


def _mock_unemployment() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    rows = []
    for code, name in EU_COUNTRIES.items():
        base = rng.uniform(3, 18)
        for yr in range(2000, 2024):
            rate = max(1.0, base + rng.normal(0, 0.5))
            rows.append({
                "country_code": code,
                "country_name": name,
                "reference_year": yr,
                "reference_date": pd.Timestamp(f"{yr}-01-01"),
                "unemployment_rate": round(rate, 2),
                "unemp_yoy_change": round(float(rng.normal(0, 0.5)), 2),
            })
            base = rate
    return pd.DataFrame(rows)


def _mock_energy() -> pd.DataFrame:
    rng = np.random.default_rng(13)
    rows = []
    for code, name in EU_COUNTRIES.items():
        base = rng.uniform(0.08, 0.35)
        for yr in range(2000, 2024):
            ei = max(0.04, base * (1 - 0.015 + rng.normal(0, 0.005)))
            rows.append({
                "country_code": code,
                "country_name": name,
                "reference_year": yr,
                "reference_date": pd.Timestamp(f"{yr}-01-01"),
                "energy_intensity": round(ei, 4),
                "energy_yoy_improvement_pct": round(float(rng.normal(1.5, 0.8)), 2),
            })
            base = ei
    return pd.DataFrame(rows)


def _mock_composite() -> pd.DataFrame:
    rng = np.random.default_rng(99)
    rows = []
    for code, name in EU_COUNTRIES.items():
        for yr in range(2000, 2024):
            gdp_s  = round(float(rng.uniform(20, 95)), 1)
            unem_s = round(float(rng.uniform(20, 95)), 1)
            ener_s = round(float(rng.uniform(20, 95)), 1)
            comp   = round((gdp_s + unem_s + ener_s) / 3, 1)
            rows.append({
                "country_code": code,
                "country_name": name,
                "reference_year": yr,
                "reference_date": pd.Timestamp(f"{yr}-01-01"),
                "gdp_score": gdp_s,
                "unemployment_score": unem_s,
                "energy_score": ener_s,
                "composite_score": comp,
            })
    return pd.DataFrame(rows)


def _mock_country_latest() -> pd.DataFrame:
    gdp  = _mock_gdp_trends().query("reference_year == 2023")
    unem = _mock_unemployment().query("reference_year == 2023")
    ener = _mock_energy().query("reference_year == 2023")
    comp = _mock_composite().query("reference_year == 2023")

    df = (
        gdp[["country_code", "country_name", "reference_year", "gdp_beur", "gdp_yoy_growth_pct"]]
        .merge(unem[["country_code", "unemployment_rate", "unemp_yoy_change"]], on="country_code")
        .merge(ener[["country_code", "energy_intensity"]], on="country_code")
        .merge(comp[["country_code", "composite_score", "gdp_score", "unemployment_score", "energy_score"]], on="country_code")
    )
    df = df.rename(columns={"reference_year": "latest_year"})
    return df


def _mock_anomalies() -> pd.DataFrame:
    from datetime import datetime, timedelta
    rng = np.random.default_rng(55)
    rows = []
    codes = list(EU_COUNTRIES.keys())
    datasets = ["gdp_annual", "unemployment_annual", "energy_intensity", "inflation_annual"]
    for i in range(20):
        rows.append({
            "dataset":      datasets[i % len(datasets)],
            "country_code": codes[i % len(codes)],
            "year":         int(rng.integers(2005, 2023)),
            "z_score":      round(float(rng.uniform(2.1, 4.5) * rng.choice([-1, 1])), 2),
            "severity":     rng.choice(["LOW", "MEDIUM", "HIGH"]),
            "detected_at":  (datetime.utcnow() - timedelta(hours=int(i * 3))).isoformat(),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def get_gdp_trends(countries: list[str] | None = None, start_year: int = 2000, end_year: int = 2023) -> pd.DataFrame:
    if USE_MOCK:
        df = _mock_gdp_trends()
    else:
        sql = f"""
            SELECT country_code, country_name, reference_year, reference_date,
                   gdp_beur, gdp_yoy_growth_pct
            FROM `{PROJECT}.{DATASET}.mart_gdp_trends`
            WHERE reference_year BETWEEN {start_year} AND {end_year}
            ORDER BY country_code, reference_year
        """
        df = _query(sql)
    if countries:
        df = df[df["country_code"].isin(countries)]
    if not df.empty:
        df = df[(df["reference_year"] >= start_year) & (df["reference_year"] <= end_year)]
    df["iso2"] = df["country_code"].apply(to_iso2)
    return df


def get_unemployment(countries: list[str] | None = None, start_year: int = 2000, end_year: int = 2023) -> pd.DataFrame:
    if USE_MOCK:
        df = _mock_unemployment()
    else:
        sql = f"""
            SELECT country_code, country_name, reference_year, reference_date,
                   unemployment_rate, unem_yoy_change
            FROM `{PROJECT}.{DATASET}.mart_unemployment_comparison`
            WHERE reference_year BETWEEN {start_year} AND {end_year}
            ORDER BY country_code, reference_year
        """
        df = _query(sql)
    if not df.empty and "unem_yoy_change" in df.columns:
        df = df.rename(columns={"unem_yoy_change": "unemp_yoy_change"})
    if countries:
        df = df[df["country_code"].isin(countries)]
    if not df.empty:
        df = df[(df["reference_year"] >= start_year) & (df["reference_year"] <= end_year)]
    df["iso2"] = df["country_code"].apply(to_iso2)
    return df


def get_energy_intensity(countries: list[str] | None = None, start_year: int = 2000, end_year: int = 2023) -> pd.DataFrame:
    if USE_MOCK:
        df = _mock_energy()
    else:
        sql = f"""
            SELECT country_code, country_name, reference_year, reference_date,
                   energy_intensity, energy_yoy_improvement_pct AS energy_yoy_improvement
            FROM `{PROJECT}.{DATASET}.mart_energy_intensity`
            WHERE reference_year BETWEEN {start_year} AND {end_year}
            ORDER BY country_code, reference_year
        """
        df = _query(sql)
    if not df.empty and "energy_yoy_improvement_pct" in df.columns:
        df = df.rename(columns={"energy_yoy_improvement_pct": "energy_yoy_improvement"})
    if countries:
        df = df[df["country_code"].isin(countries)]
    if not df.empty:
        df = df[(df["reference_year"] >= start_year) & (df["reference_year"] <= end_year)]
    df["iso2"] = df["country_code"].apply(to_iso2)
    return df


def get_composite_index(countries: list[str] | None = None, start_year: int = 2000, end_year: int = 2023) -> pd.DataFrame:
    if USE_MOCK:
        df = _mock_composite()
    else:
        sql = f"""
            SELECT country_code, country_name, reference_year, reference_date,
                   gdp_score, unemployment_score, energy_score, composite_score
            FROM `{PROJECT}.{DATASET}.mart_composite_economic_index`
            WHERE reference_year BETWEEN {start_year} AND {end_year}
            ORDER BY reference_year DESC, composite_score DESC
        """
        df = _query(sql)
    if countries:
        df = df[df["country_code"].isin(countries)]
    if not df.empty:
        df = df[(df["reference_year"] >= start_year) & (df["reference_year"] <= end_year)]
    df["iso2"] = df["country_code"].apply(to_iso2)
    return df


def get_country_latest(countries: list[str] | None = None) -> pd.DataFrame:
    if USE_MOCK:
        df = _mock_country_latest()
    else:
        sql = f"""
            SELECT *
            FROM `{PROJECT}.{DATASET}.mart_country_latest`
            ORDER BY composite_score DESC
        """
        df = _query(sql)
    if not df.empty and "unem_yoy_change" in df.columns:
        df = df.rename(columns={"unem_yoy_change": "unemp_yoy_change"})
    if countries:
        df = df[df["country_code"].isin(countries)]
    df["iso2"] = df["country_code"].apply(to_iso2)
    return df


def get_anomaly_alerts(limit: int = 50) -> pd.DataFrame:
    if USE_MOCK:
        return _mock_anomalies().head(limit)
    sql = f"""
        SELECT dataset, country_code, year, z_score, severity, detected_at
        FROM `{PROJECT}.eurostat_raw.anomaly_alerts`
        ORDER BY detected_at DESC
        LIMIT {limit}
    """
    return _query(sql)
