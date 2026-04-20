"""
flink/streaming_job.py
======================
PyFlink streaming job for the European Statistics Economic Monitor.

Pipeline:
  1. Read anomaly alert JSON messages from the ``eurostat.anomalies``
     Redpanda / Kafka topic.
  2. Parse and enrich each message (add ``processed_at`` timestamp).
  3. Write individual records to BigQuery ``anomaly_stream_summaries``
     via a batched Python sink using the BigQuery Streaming Insert API.

Environment variables (all required unless a default is shown):
  GCP_PROJECT_ID            – GCP project that owns the BigQuery dataset.
  BQ_RAW_DATASET            – BigQuery dataset name  (default: eurostat_raw).
  REDPANDA_BROKERS          – Kafka bootstrap address (default: redpanda:9092).
  KAFKA_TOPIC_ANOMALIES     – Source topic           (default: eurostat.anomalies).
  FLINK_CONSUMER_GROUP      – Kafka consumer group   (default: flink-eurostat-streaming).
  GOOGLE_APPLICATION_CREDENTIALS – GCP service account key path (auto-set in Docker).
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

from pyflink.common import Duration, WatermarkStrategy
from pyflink.common.serialization import SimpleStringSchema
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import (
    KafkaOffsetsInitializer,
    KafkaSource,
)
from pyflink.datastream.functions import MapFunction, ProcessFunction

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
GCP_PROJECT = os.getenv("GCP_PROJECT_ID", "")
RAW_DATASET = os.getenv("BQ_RAW_DATASET", "eurostat_raw")
REDPANDA_BROKERS = os.getenv("REDPANDA_BROKERS", "redpanda:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC_ANOMALIES", "eurostat.anomalies")
CONSUMER_GROUP = os.getenv("FLINK_CONSUMER_GROUP", "flink-eurostat-streaming")


# ---------------------------------------------------------------------------
# Stream operators
# ---------------------------------------------------------------------------
class ParseAlertFn(MapFunction):
    """
    Parse a raw Kafka JSON string into a dict and add ``processed_at``.

    Malformed records are returned as an empty dict so the downstream
    filter can discard them without crashing the pipeline.
    """

    def map(self, value: str) -> dict:  # type: ignore[override]
        try:
            record: dict = json.loads(value)
            record.setdefault(
                "processed_at",
                datetime.now(timezone.utc).isoformat(),
            )
            return record
        except (json.JSONDecodeError, TypeError, ValueError):
            logger.warning("Skipping unparseable record: %.120s", value)
            return {}


class BigQuerySink(ProcessFunction):
    """
    Batched BigQuery streaming-insert sink implemented as a ProcessFunction.

    ProcessFunction is the correct base for custom Python sinks in PyFlink 2.x
    (SinkFunction is a Java wrapper and cannot be subclassed in Python).

    * Opens a ``google.cloud.bigquery.Client`` once per task-slot in ``open()``.
    * Accumulates rows in an in-memory buffer.
    * Flushes every ``BATCH_SIZE`` rows *or* when the task closes.
    """

    BATCH_SIZE: int = 100

    def __init__(self, project: str, dataset: str, table: str) -> None:
        self._project = project
        self._dataset = dataset
        self._table_id = f"{project}.{dataset}.{table}"
        self._buffer: list[dict] = []
        self._client = None  # created in open()

    # Flink lifecycle ---------------------------------------------------------

    def open(self, runtime_context) -> None:  # noqa: ANN001
        from google.cloud import bigquery  # type: ignore[import-untyped]

        self._client = bigquery.Client(project=self._project)
        logger.info("BigQuery client opened → table: %s", self._table_id)

    def process_element(self, record: dict, ctx) -> None:  # noqa: ANN001
        if not record or not record.get("country_code"):
            return
        self._buffer.append(record)
        if len(self._buffer) >= self.BATCH_SIZE:
            self._flush()

    def close(self) -> None:
        self._flush()
        if self._client is not None:
            self._client.close()
            self._client = None

    # Helpers -----------------------------------------------------------------

    def _flush(self) -> None:
        if not self._buffer or self._client is None:
            return
        errors = self._client.insert_rows_json(self._table_id, self._buffer)
        if errors:
            logger.error(
                "BigQuery insert errors for %d rows: %s",
                len(self._buffer),
                errors,
            )
        else:
            logger.info(
                "Flushed %d rows → %s",
                len(self._buffer),
                self._table_id,
            )
        self._buffer.clear()


# ---------------------------------------------------------------------------
# Job entry-point
# ---------------------------------------------------------------------------
def main() -> None:
    if not GCP_PROJECT:
        raise RuntimeError("GCP_PROJECT_ID environment variable is required.")

    env = StreamExecutionEnvironment.get_execution_environment()
    env.enable_checkpointing(60_000)  # checkpoint every 60 s
    env.set_parallelism(1)

    source = (
        KafkaSource.builder()
        .set_bootstrap_servers(REDPANDA_BROKERS)
        .set_topics(KAFKA_TOPIC)
        .set_group_id(CONSUMER_GROUP)
        .set_starting_offsets(KafkaOffsetsInitializer.earliest())
        .set_value_only_deserializer(SimpleStringSchema())
        .build()
    )

    watermark_strategy = WatermarkStrategy.for_bounded_out_of_orderness(
        Duration.of_seconds(30)
    )

    (
        env
        .from_source(
            source=source,
            watermark_strategy=watermark_strategy,
            source_name="eurostat-anomaly-topic",
        )
        .map(ParseAlertFn())
        .filter(lambda rec: bool(rec.get("country_code")))
        .process(
            BigQuerySink(
                project=GCP_PROJECT,
                dataset=RAW_DATASET,
                table="anomaly_stream_summaries",
            )
        )
    )

    env.execute("EurostatAnomalyFlink")


if __name__ == "__main__":
    main()
