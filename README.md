# 🇪🇺 EU Economic Monitor
### Data Engineering Zoomcamp — Final Project

A **production-grade data engineering pipeline** that ingests European economic statistics from Eurostat, processes them through a multi-layer transformation stack, detects anomalies via a Kafka-compatible stream, and visualises everything in a Streamlit dashboard.

> **Reproduction time:** ~30 min for GCP setup + ~20 min for first pipeline run.  
> Everything runs in Docker — no local Python environments needed beyond Docker Desktop and Terraform.

For full documentation, architecture diagrams, setup instructions, and troubleshooting, see the complete README in the repository.

## Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/sharadgupta27/eu-economic-monitor.git
cd eu-economic-monitor
make setup

# 2. Configure .env and terraform/terraform.tfvars with your GCP project

# 3. Provision infrastructure
make terraform-init
make terraform-apply

# 4. Build and run
make build
make up
make create-topics
make pipeline

# 5. Open dashboard
make open-dashboard  # http://localhost:8501
```

## Architecture

- **Ingestion**: dlt → BigQuery (raw layer)
- **Streaming**: Redpanda (Kafka-compatible)
- **Batch Processing**: Spark → BigQuery (processed layer)
- **Real-time Processing**: PyFlink → anomaly detection
- **Transformations**: dbt (staging → marts)
- **Visualization**: Streamlit + Plotly
- **Infrastructure**: Terraform + Docker Compose

## Technology Stack

- Cloud: GCP (BigQuery, GCS)
- Ingestion: dlt 0.4.x + eurostat library
- Stream: Redpanda v23.3
- Batch: Apache Spark 3.5.x
- Stream Processing: Apache Flink 1.17.x
- Transform: dbt-bigquery 1.7.x
- Dashboard: Streamlit 1.33 + Plotly 5.22
- IaC: Terraform ≥ 1.5
- Container: Docker + Docker Compose v2