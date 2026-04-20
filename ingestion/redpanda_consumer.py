"""
redpanda_consumer.py
====================
Long-running consumer that:
  1. Reads ingestion-complete events from the `eurostat.ingestion.completed`
     Redpanda topic.
  2. Queries BigQuery for the newly loaded data.
  3. Calculates z-scores to detect statistical anomalies (|z| > 2).
  4. Publishes anomaly records to the `eurostat.anomalies` topic.
  5. Writes anomaly records to BigQuery `eurostat_raw.anomaly_alerts`.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime

import numpy as np
from google.cloud import bigquery
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import NoBrokersAvailable

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
REDPANDA_BROKERS: str = os.getenv("REDPANDA_BROKERS", "localhost:19092")
TOPIC_IN: str = os.getenv("KAFKA_TOPIC_INGESTION", "eurostat.ingestion.completed")
TOPIC_ANOMALIES: str = os.getenv("KAFKA_TOPIC_ANOMALIES", "eurostat.anomalies")
BQ_RAW_DATASET: str = os.getenv("BQ_RAW_DATASET", "eurostat_raw")
GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "")
ZSCORE_THRESHOLD: float = 2.0

DATASET_TABLE_MAP: dict[str, str] = {
    "gdp_annual": "gdp_annual",
    "unemployment_annual": "unemployment_annual",
    "energy_intensity": "energy_intensity",
    "inflation_annual": "inflation_annual",
}

# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------
def _bq_client() -> bigquery.Client:
    return bigquery.Client(project=GCP_PROJECT_ID)


def _make_producer() -> KafkaProducer | None:
    try:
        return KafkaProducer(
            bootstrap_servers=REDPANDA_BROKERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
    except NoBrokersAvailable:
        logger.warning("Could not connect to Redpanda producer")
        return None


def _make_consumer() -> KafkaConsumer:
    return KafkaConsumer(
        TOPIC_IN,
        bootstrap_servers=REDPANDA_BROKERS,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        group_id="eurostat-anomaly-detector",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )


# ---------------------------------------------------------------------------
# Anomaly Detection
# ---------------------------------------------------------------------------
def _detect_anomalies(bq: bigquery.Client, table_name: str) -> list[dict]:
    """Return rows with |z-score| > threshold for the given raw table."""
    query = f"""
        WITH stats AS (
            SELECT
                country_code,
                AVG(value)    AS mean_val,
                STDDEV(value) AS std_val
            FROM `{GCP_PROJECT_ID}.{BQ_RAW_DATASET}.{table_name}`
            GROUP BY country_code
        )
        SELECT
            r.country_code,
            r.year,
            r.value,
            s.mean_val   AS mean,
            s.std_val    AS std_dev,
            SAFE_DIVIDE(r.value - s.mean_val, NULLIF(s.std_val, 0)) AS z_score
        FROM `{GCP_PROJECT_ID}.{BQ_RAW_DATASET}.{table_name}` r
        JOIN stats s USING (country_code)
        WHERE ABS(SAFE_DIVIDE(r.value - s.mean_val, NULLIF(s.std_val, 0))) > {ZSCORE_THRESHOLD}
        ORDER BY ABS(z_score) DESC
        LIMIT 200
    """
    try:
        rows = list(bq.query(query).result())
        logger.info("Found %d anomalies in %s", len(rows), table_name)
        return [dict(row) for row in rows]
    except Exception as exc:
        logger.error("BQ anomaly query failed for %s: %s", table_name, exc)
        return []


def _severity(z: float) -> str:
    az = abs(z)
    if az >= 4:
        return "HIGH"
    if az >= 3:
        return "MEDIUM"
    return "LOW"


def _write_alerts_to_bq(bq: bigquery.Client, alerts: list[dict], dataset_name: str) -> None:
    if not alerts:
        return
    table_ref = f"{GCP_PROJECT_ID}.{BQ_RAW_DATASET}.anomaly_alerts"
    rows = [
        {
            "dataset": dataset_name,
            "country_code": a["country_code"],
            "year": int(a["year"]),
            "value": float(a["value"]) if a["value"] is not None else None,
            "z_score": float(a["z_score"]) if a["z_score"] is not None else None,
            "mean": float(a["mean"]) if a["mean"] is not None else None,
            "std_dev": float(a["std_dev"]) if a["std_dev"] is not None else None,
            "severity": _severity(float(a["z_score"] or 0)),
            "detected_at": datetime.utcnow().isoformat(),
        }
        for a in alerts
    ]
    errors = bq.insert_rows_json(table_ref, rows)
    if errors:
        logger.error("BQ insert errors: %s", errors)
    else:
        logger.info("Wrote %d anomaly alerts to BigQuery", len(rows))


# ---------------------------------------------------------------------------
# Main Loop
# ---------------------------------------------------------------------------
def main() -> None:
    logger.info("Starting anomaly-detection consumer …")
    bq = _bq_client()
    producer = _make_producer()
    consumer = _make_consumer()

    for message in consumer:
        event: dict = message.value
        logger.info("Received event: %s", event)

        dataset_name = event.get("dataset", "")
        # Map full pipeline event → check all tables
        tables = (
            list(DATASET_TABLE_MAP.values())
            if "full_pipeline" in dataset_name
            else [DATASET_TABLE_MAP.get(dataset_name)]
        )

        for table in tables:
            if table is None:
                continue
            anomalies = _detect_anomalies(bq, table)
            if not anomalies:
                continue

            # Write to BigQuery
            _write_alerts_to_bq(bq, anomalies, table)

            # Publish to Redpanda
            if producer:
                for a in anomalies:
                    alert_msg = {
                        "dataset": table,
                        "country_code": a["country_code"],
                        "year": int(a["year"]),
                        "value": float(a["value"] or 0),
                        "z_score": float(a["z_score"] or 0),
                        "severity": _severity(float(a["z_score"] or 0)),
                        "detected_at": datetime.utcnow().isoformat(),
                    }
                    producer.send(TOPIC_ANOMALIES, value=alert_msg)
                producer.flush()
                logger.info(
                    "Published %d alerts to %s", len(anomalies), TOPIC_ANOMALIES
                )


if __name__ == "__main__":
    main()
