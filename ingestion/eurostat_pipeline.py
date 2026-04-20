"""
eurostat_pipeline.py
=====================
dlt pipeline that ingests four Eurostat indicator datasets into
BigQuery (raw layer) and publishes an ingestion-complete event
to a Redpanda topic after each successful load.

Datasets ingested:
  - GDP annual              (nama_10_gdp)
  - Unemployment rate       (une_rt_a)
  - Energy intensity        (nrg_ind_ei)
  - HICP inflation          (prc_hicp_aind)
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime
from typing import Iterator

import dlt
import eurostat
import pandas as pd
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
COUNTRIES: list[str] = os.getenv(
    "EUROSTAT_COUNTRIES",
    "DE,FR,IT,ES,PL,NL,BE,SE,AT,PT,FI,IE,CZ,RO,HU,DK,EL,SK",
).split(",")
START_YEAR: int = int(os.getenv("EUROSTAT_START_YEAR", "2000"))
END_YEAR: int = int(os.getenv("EUROSTAT_END_YEAR", "2023"))
REDPANDA_BROKERS: str = os.getenv("REDPANDA_BROKERS", "localhost:19092")
KAFKA_TOPIC: str = os.getenv("KAFKA_TOPIC_INGESTION", "eurostat.ingestion.completed")
BQ_RAW_DATASET: str = os.getenv("BQ_RAW_DATASET", "eurostat_raw")
GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "")

COUNTRY_NAMES: dict[str, str] = {
    "AT": "Austria",     "BE": "Belgium",     "BG": "Bulgaria",
    "CY": "Cyprus",      "CZ": "Czechia",     "DE": "Germany",
    "DK": "Denmark",     "EE": "Estonia",     "EL": "Greece",
    "ES": "Spain",       "FI": "Finland",     "FR": "France",
    "HR": "Croatia",     "HU": "Hungary",     "IE": "Ireland",
    "IT": "Italy",       "LT": "Lithuania",   "LU": "Luxembourg",
    "LV": "Latvia",      "MT": "Malta",       "NL": "Netherlands",
    "PL": "Poland",      "PT": "Portugal",    "RO": "Romania",
    "SE": "Sweden",      "SI": "Slovenia",    "SK": "Slovakia",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _get_producer() -> KafkaProducer | None:
    """Create a Redpanda/Kafka producer; returns None on failure."""
    try:
        producer = KafkaProducer(
            bootstrap_servers=REDPANDA_BROKERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            request_timeout_ms=5000,
        )
        logger.info("Connected to Redpanda at %s", REDPANDA_BROKERS)
        return producer
    except NoBrokersAvailable:
        logger.warning("Redpanda unavailable — events will not be published.")
        return None


def _publish_event(producer: KafkaProducer | None, dataset: str, record_count: int) -> None:
    if producer is None:
        return
    event = {
        "dataset": dataset,
        "record_count": record_count,
        "countries": COUNTRIES,
        "year_range": {"start": START_YEAR, "end": END_YEAR},
        "timestamp": datetime.utcnow().isoformat(),
        "status": "completed",
    }
    producer.send(KAFKA_TOPIC, value=event)
    producer.flush()
    logger.info("Published ingestion event for dataset=%s", dataset)


def _fetch_to_long(dataset_code: str, filter_pars: dict) -> pd.DataFrame:
    """
    Pull data from the Eurostat API and reshape to long format.

    The eurostat library returns a wide DataFrame where the last dimension
    column is 'geo\\TIME_PERIOD' and the remaining columns are year strings.
    """
    logger.info("Fetching %s (filter=%s)", dataset_code, filter_pars)
    try:
        df = eurostat.get_data_df(dataset_code, filter_pars=filter_pars)
    except Exception as exc:
        logger.error("Failed to fetch %s: %s", dataset_code, exc)
        return pd.DataFrame()

    if df is None or df.empty:
        logger.warning("No data returned for %s", dataset_code)
        return pd.DataFrame()

    # Identify year columns (4-digit strings for years in range)
    year_cols = [
        c for c in df.columns
        if str(c).isdigit() and START_YEAR <= int(c) <= END_YEAR
    ]
    dim_cols = [c for c in df.columns if c not in year_cols]

    df_long = df.melt(
        id_vars=dim_cols,
        value_vars=year_cols,
        var_name="year",
        value_name="value",
    )
    df_long["year"] = pd.to_numeric(df_long["year"], errors="coerce").astype("Int64")
    df_long["value"] = pd.to_numeric(df_long["value"], errors="coerce")
    df_long = df_long.dropna(subset=["year", "value"])
    df_long["loaded_at"] = date.today().isoformat()

    logger.info("Reshaped %s → %d rows", dataset_code, len(df_long))
    return df_long


def _geo_col(df: pd.DataFrame) -> str:
    """Return the name of the geo/country column."""
    for col in df.columns:
        if "geo" in col.lower():
            return col
    return "geo"


# ---------------------------------------------------------------------------
# dlt Resources
# ---------------------------------------------------------------------------
@dlt.resource(name="gdp_annual", write_disposition="replace")
def gdp_resource() -> Iterator[dict]:
    """GDP annual data (nama_10_gdp, CP_MEUR, B1GQ)."""
    df = _fetch_to_long(
        "nama_10_gdp",
        {"geo": COUNTRIES, "unit": ["CP_MEUR"], "na_item": ["B1GQ"]},
    )
    geo = _geo_col(df)
    count = 0
    for _, row in df.iterrows():
        cc = str(row[geo]).strip()
        if cc not in COUNTRY_NAMES:
            continue
        yield {
            "country_code": cc,
            "country_name": COUNTRY_NAMES[cc],
            "year": int(row["year"]),
            "unit": str(row.get("unit", "CP_MEUR")),
            "indicator": "B1GQ",
            "value": float(row["value"]),
            "loaded_at": row["loaded_at"],
        }
        count += 1
    logger.info("gdp_resource yielded %d records", count)


@dlt.resource(name="unemployment_annual", write_disposition="replace")
def unemployment_resource() -> Iterator[dict]:
    """Unemployment rate annual (une_rt_a, PC_ACT, Y15-74, T)."""
    df = _fetch_to_long(
        "une_rt_a",
        {"geo": COUNTRIES, "age": ["Y15-74"], "sex": ["T"], "unit": ["PC_ACT"]},
    )
    geo = _geo_col(df)
    count = 0
    for _, row in df.iterrows():
        cc = str(row[geo]).strip()
        if cc not in COUNTRY_NAMES:
            continue
        yield {
            "country_code": cc,
            "country_name": COUNTRY_NAMES[cc],
            "year": int(row["year"]),
            "unit": "PC_ACT",
            "age_group": str(row.get("age", "TOTAL")),
            "sex": str(row.get("sex", "T")),
            "value": float(row["value"]),
            "loaded_at": row["loaded_at"],
        }
        count += 1
    logger.info("unemployment_resource yielded %d records", count)


@dlt.resource(name="energy_intensity", write_disposition="replace")
def energy_resource() -> Iterator[dict]:
    """Energy intensity of the economy (nrg_ind_ei, KGOE_TEUR)."""
    df = _fetch_to_long(
        "nrg_ind_ei",
        {"geo": COUNTRIES, "unit": ["KGOE_TEUR"]},
    )
    geo = _geo_col(df)
    count = 0
    for _, row in df.iterrows():
        cc = str(row[geo]).strip()
        if cc not in COUNTRY_NAMES:
            continue
        yield {
            "country_code": cc,
            "country_name": COUNTRY_NAMES[cc],
            "year": int(row["year"]),
            "unit": "KGOE_TEUR",
            "value": float(row["value"]),
            "loaded_at": row["loaded_at"],
        }
        count += 1
    logger.info("energy_resource yielded %d records", count)


@dlt.resource(name="inflation_annual", write_disposition="replace")
def inflation_resource() -> Iterator[dict]:
    """HICP inflation annual average rate of change (prc_hicp_aind)."""
    df = _fetch_to_long(
        "prc_hicp_aind",
        {"geo": COUNTRIES, "unit": ["RCH_A_AVG"], "coicop": ["CP00"]},
    )
    geo = _geo_col(df)
    count = 0
    for _, row in df.iterrows():
        cc = str(row[geo]).strip()
        if cc not in COUNTRY_NAMES:
            continue
        yield {
            "country_code": cc,
            "country_name": COUNTRY_NAMES[cc],
            "year": int(row["year"]),
            "unit": "RCH_A_AVG",
            "value": float(row["value"]),
            "loaded_at": row["loaded_at"],
        }
        count += 1
    logger.info("inflation_resource yielded %d records", count)


@dlt.source
def eurostat_source():
    return [
        gdp_resource(),
        unemployment_resource(),
        energy_resource(),
        inflation_resource(),
    ]


# ---------------------------------------------------------------------------
# BigQuery helpers
# ---------------------------------------------------------------------------
def _drop_bq_raw_tables() -> None:
    """Drop raw data tables so dlt recreates them with the current schema.

    Required when the existing tables were written by an older dlt version
    whose schema uses NULLABLE system fields (e.g. _dlt_load_id) that the
    current version now marks as REQUIRED — BigQuery forbids adding REQUIRED
    columns to an existing table via ALTER TABLE.
    """
    try:
        from google.cloud import bigquery  # type: ignore
    except ImportError:
        logger.warning("google-cloud-bigquery not importable — skipping table drop.")
        return

    try:
        client = bigquery.Client(project=GCP_PROJECT_ID or None)
        drop_tables = [
            "gdp_annual",
            "unemployment_annual",
            "energy_intensity",
            "inflation_annual",
            "_dlt_loads",
            "_dlt_pipeline_state",
            "_dlt_version",
        ]
        for tbl in drop_tables:
            ref = f"{client.project}.{BQ_RAW_DATASET}.{tbl}"
            client.delete_table(ref, not_found_ok=True)
            logger.info("Dropped BQ table %s (if existed)", ref)
    except Exception as exc:
        logger.warning("Could not drop BQ tables (non-fatal): %s", exc)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
def main() -> None:
    logger.info("=" * 60)
    logger.info("EU Economic Monitor — dlt Ingestion Pipeline")
    logger.info("Countries : %s", COUNTRIES)
    logger.info("Years     : %d – %d", START_YEAR, END_YEAR)
    logger.info("Destination: BigQuery / %s", BQ_RAW_DATASET)
    logger.info("=" * 60)

    # Drop existing raw tables so dlt can recreate them with the current
    # schema (avoids 'Cannot add required fields' errors on re-runs).
    _drop_bq_raw_tables()

    producer = _get_producer()

    pipeline = dlt.pipeline(
        pipeline_name="eurostat_economic_monitor",
        destination="bigquery",
        dataset_name=BQ_RAW_DATASET,
    )

    load_info = pipeline.run(eurostat_source())
    logger.info("Load info: %s", load_info)

    # Publish completion events for each loaded table
    for pkg in load_info.load_packages:
        for job in pkg.jobs.get("completed_jobs", []):
            _publish_event(producer, str(job.file_path), 0)

    _publish_event(producer, "eurostat_full_pipeline", 0)
    logger.info("✅  dlt pipeline complete.")


if __name__ == "__main__":
    main()
