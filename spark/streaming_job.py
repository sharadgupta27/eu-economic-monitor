"""
streaming_job.py
================
Spark Structured Streaming job that:
  1. Reads anomaly alert JSON messages from the `eurostat.anomalies`
     Redpanda topic.
  2. Applies a 10-minute tumbling window to aggregate alert counts
     per country and dataset.
  3. Writes windowed summaries back to BigQuery in micro-batch mode.

Execution (local Docker):
    spark-submit \
      --packages com.google.cloud.spark:spark-bigquery-with-dependencies_2.12:0.34.0,\
                 org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
      --conf spark.hadoop.google.cloud.auth.service.account.enable=true \
      --conf spark.hadoop.google.cloud.auth.service.account.json.keyfile=/credentials/service-account.json \
      /app/streaming_job.py
"""

from __future__ import annotations

import logging
import os

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
GCP_PROJECT      = os.getenv("GCP_PROJECT_ID", "")
RAW_DATASET      = os.getenv("BQ_RAW_DATASET", "eurostat_raw")
GCS_BUCKET       = os.getenv("GCS_BUCKET_NAME", "")
REDPANDA_BROKERS = os.getenv("REDPANDA_BROKERS", "localhost:9092")
KAFKA_TOPIC      = os.getenv("KAFKA_TOPIC_ANOMALIES", "eurostat.anomalies")

ALERT_SCHEMA = StructType([
    StructField("dataset",      StringType(),    True),
    StructField("country_code", StringType(),    True),
    StructField("year",         IntegerType(),   True),
    StructField("value",        DoubleType(),    True),
    StructField("z_score",      DoubleType(),    True),
    StructField("severity",     StringType(),    True),
    StructField("detected_at",  TimestampType(), True),
])


def build_spark() -> SparkSession:
    return (
        SparkSession.builder
        .appName("EurostatAnomalyStream")
        .config("spark.sql.streaming.checkpointLocation", f"/tmp/spark-checkpoint")
        .config("temporaryGcsBucket", GCS_BUCKET)
        .getOrCreate()
    )


def write_to_bq(batch_df, batch_id: int) -> None:
    """Micro-batch writer for BigQuery (foreachBatch sink)."""
    if batch_df.isEmpty():
        return
    logger.info("Writing batch %d (%d rows) to BigQuery …", batch_id, batch_df.count())
    (
        batch_df.write
        .format("bigquery")
        .option("project", GCP_PROJECT)
        .option("dataset", RAW_DATASET)
        .option("table", "anomaly_stream_summaries")
        .option("temporaryGcsBucket", GCS_BUCKET)
        .mode("append")
        .save()
    )


def main() -> None:
    logger.info("Starting Spark Structured Streaming job …")
    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")

    # -------------------------------------------------------------------------
    # Read from Redpanda (Kafka protocol)
    # -------------------------------------------------------------------------
    raw_stream = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", REDPANDA_BROKERS)
        .option("subscribe", KAFKA_TOPIC)
        .option("startingOffsets", "latest")
        .option("kafka.group.id", "spark-anomaly-consumer")
        .load()
    )

    # -------------------------------------------------------------------------
    # Parse JSON payload
    # -------------------------------------------------------------------------
    parsed = (
        raw_stream
        .select(
            F.from_json(
                F.col("value").cast("string"),
                ALERT_SCHEMA,
            ).alias("data")
        )
        .select("data.*")
        .withColumn("event_time",
                    F.coalesce(F.col("detected_at"), F.current_timestamp()))
        .withWatermark("event_time", "5 minutes")
    )

    # -------------------------------------------------------------------------
    # Window aggregation: alert counts per country / dataset in 10-min windows
    # -------------------------------------------------------------------------
    windowed = (
        parsed
        .groupBy(
            F.window("event_time", "10 minutes"),
            F.col("country_code"),
            F.col("dataset"),
            F.col("severity"),
        )
        .agg(
            F.count("*").alias("alert_count"),
            F.avg("z_score").alias("avg_z_score"),
            F.max(F.abs(F.col("z_score"))).alias("max_abs_z"),
        )
        .withColumn("window_start", F.col("window.start"))
        .withColumn("window_end",   F.col("window.end"))
        .drop("window")
    )

    # -------------------------------------------------------------------------
    # Write to BigQuery via foreachBatch
    # -------------------------------------------------------------------------
    query = (
        windowed.writeStream
        .outputMode("update")
        .foreachBatch(write_to_bq)
        .trigger(processingTime="60 seconds")
        .start()
    )

    logger.info("Streaming query started. Awaiting termination …")
    query.awaitTermination()


if __name__ == "__main__":
    main()
