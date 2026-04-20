"""
batch_job.py
============
Spark batch job that reads raw BigQuery tables produced by dlt,
computes year-over-year metrics and z-score anomaly flags, then
writes enriched tables back to BigQuery (eurostat_processed dataset).

Execution (local Docker):
    spark-submit \
      --packages com.google.cloud.spark:spark-bigquery-with-dependencies_2.12:0.34.0 \
      --conf spark.hadoop.google.cloud.auth.service.account.enable=true \
      --conf spark.hadoop.google.cloud.auth.service.account.json.keyfile=/credentials/service-account.json \
      /app/batch_job.py
"""

from __future__ import annotations

import logging
import os

from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
GCP_PROJECT      = os.getenv("GCP_PROJECT_ID", "")
RAW_DATASET      = os.getenv("BQ_RAW_DATASET", "eurostat_raw")
PROCESSED        = os.getenv("BQ_PROCESSED_DATASET", "eurostat_processed")
GCS_BUCKET       = os.getenv("GCS_BUCKET_NAME", "")
CREDENTIALS_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/credentials/service-account.json")


def build_spark() -> SparkSession:
    return (
        SparkSession.builder
        .appName("EurostatBatchProcessor")
        .config("spark.sql.adaptive.enabled", "true")
        .config("writeMethod", "direct")
        .getOrCreate()
    )


def read_bq(spark: SparkSession, table: str, dataset: str | None = None):
    return (
        spark.read
        .format("bigquery")
        .option("project", GCP_PROJECT)
        .option("dataset", dataset or RAW_DATASET)
        .option("table", table)
        .load()
    )


def write_bq(df, table: str, mode: str = "overwrite") -> None:
    (
        df.write
        .format("bigquery")
        .option("project", GCP_PROJECT)
        .option("dataset", PROCESSED)
        .option("table", table)
        .option("writeMethod", "direct")
        .mode(mode)
        .save()
    )
    logger.info("Written: %s.%s.%s", GCP_PROJECT, PROCESSED, table)


# ---------------------------------------------------------------------------
# Transformations
# ---------------------------------------------------------------------------
def add_yoy(df, value_col: str = "value", partition_col: str = "country_code"):
    """Add year-over-year change and growth % columns."""
    w = Window.partitionBy(partition_col).orderBy("year")
    prev = F.lag(value_col).over(w)
    return (
        df
        .withColumn("prev_value", prev)
        .withColumn("yoy_change", F.col(value_col) - F.col("prev_value"))
        .withColumn(
            "yoy_growth_pct",
            F.round(
                F.when(F.col("prev_value") != 0,
                       (F.col(value_col) - F.col("prev_value")) / F.col("prev_value") * 100
                ).otherwise(F.lit(None)),
                2,
            ),
        )
        .drop("prev_value")
    )


def add_zscore(df, value_col: str = "value", partition_col: str = "country_code"):
    """Add z-score column relative to each country's historical mean."""
    w = Window.partitionBy(partition_col)
    mean_ = F.avg(value_col).over(w)
    std_  = F.stddev(value_col).over(w)
    return df.withColumn(
        "z_score",
        F.round(
            F.when(std_ != 0, (F.col(value_col) - mean_) / std_).otherwise(F.lit(0)),
            3,
        ),
    )


def add_reference_date(df):
    """Add DATE(year, 1, 1) as reference_date for BigQuery partitioning."""
    return df.withColumn(
        "reference_date",
        F.to_date(F.concat(F.col("year").cast("string"), F.lit("-01-01"))),
    )


# ---------------------------------------------------------------------------
# Per-dataset processing
# ---------------------------------------------------------------------------
def process_gdp(spark: SparkSession) -> None:
    logger.info("Processing GDP …")
    df = (
        read_bq(spark, "gdp_annual")
        .withColumnRenamed("value", "gdp_meur")
        .withColumn("gdp_beur", F.round(F.col("gdp_meur") / 1000, 3))
    )
    df = add_yoy(df, "gdp_meur")
    df = add_zscore(df, "gdp_meur")
    df = add_reference_date(df)
    df = df.filter(F.col("gdp_meur").isNotNull())
    write_bq(df, "gdp_annual_processed")


def process_unemployment(spark: SparkSession) -> None:
    logger.info("Processing Unemployment …")
    df = (
        read_bq(spark, "unemployment_annual")
        .withColumnRenamed("value", "unemployment_rate")
    )
    df = add_yoy(df, "unemployment_rate")
    df = add_zscore(df, "unemployment_rate")
    df = add_reference_date(df)
    df = df.filter(F.col("unemployment_rate").isNotNull())
    write_bq(df, "unemployment_processed")


def process_energy(spark: SparkSession) -> None:
    logger.info("Processing Energy Intensity …")
    df = (
        read_bq(spark, "energy_intensity")
        .withColumnRenamed("value", "energy_intensity")
    )
    df = add_yoy(df, "energy_intensity")
    df = add_zscore(df, "energy_intensity")
    df = add_reference_date(df)
    df = df.filter(F.col("energy_intensity").isNotNull())
    write_bq(df, "energy_intensity_processed")


def process_inflation(spark: SparkSession) -> None:
    logger.info("Processing Inflation …")
    df = (
        read_bq(spark, "inflation_annual")
        .withColumnRenamed("value", "inflation_rate")
    )
    df = add_yoy(df, "inflation_rate")
    df = add_zscore(df, "inflation_rate")
    df = add_reference_date(df)
    df = df.filter(F.col("inflation_rate").isNotNull())
    write_bq(df, "inflation_processed")


def process_combined(spark: SparkSession) -> None:
    """Join all processed indicators into a single wide fact table."""
    logger.info("Building combined indicators table …")

    gdp  = read_bq(spark, "gdp_annual_processed", PROCESSED).select(
        "country_code", "country_name", "year", "reference_date",
        F.col("gdp_beur"), F.col("yoy_growth_pct").alias("gdp_yoy_pct"),
    )
    unem = read_bq(spark, "unemployment_processed", PROCESSED).select(
        "country_code", "year",
        F.col("unemployment_rate"), F.col("yoy_growth_pct").alias("unem_yoy_pct"),
    )
    ener = read_bq(spark, "energy_intensity_processed", PROCESSED).select(
        "country_code", "year",
        F.col("energy_intensity"), F.col("yoy_growth_pct").alias("energy_yoy_pct"),
    )
    infl = read_bq(spark, "inflation_processed", PROCESSED).select(
        "country_code", "year",
        F.col("inflation_rate"),
    )

    combined = (
        gdp
        .join(unem, ["country_code", "year"], "left")
        .join(ener, ["country_code", "year"], "left")
        .join(infl, ["country_code", "year"], "left")
        .orderBy("country_code", "year")
    )
    write_bq(combined, "combined_indicators")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    logger.info("Starting Eurostat Spark Batch Job …")
    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")

    process_gdp(spark)
    process_unemployment(spark)
    process_energy(spark)
    process_inflation(spark)
    process_combined(spark)

    spark.stop()
    logger.info("✅  Spark batch job complete.")


if __name__ == "__main__":
    main()
