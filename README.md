# EU Economic Monitor

### Data Engineering Zoomcamp - Final Project {#data-engineering-zoomcamp---final-project}

A **production-grade data engineering pipeline** that ingests European economic statistics from Eurostat, processes them through a multi-layer transformation stack, detects anomalies via a Kafka-compatible stream, and visualises everything in a Streamlit dashboard.

> **Reproduction time:** \~30 min for GCP setup + \~20 min for first pipeline run.\
> Everything runs in Docker - no local Python environments needed beyond Docker Desktop and Terraform.

> **🚀 Quick Start for Windows Users:** After completing the GCP setup (Steps 1-5), simply double-click `run_pipeline.bat` or run from command line to execute the entire pipeline automatically. See [Windows one-click batch scripts](#windows---one-click-batch-scripts) for details.

------------------------------------------------------------------------

## 📊 Project Overview

This project demonstrates a complete end-to-end data engineering solution for monitoring and analyzing EU economic indicators. It implements modern data engineering best practices including Infrastructure as Code, containerization, stream processing, dimensional modeling, and real-time anomaly detection.

**Data Scope:** - **4 Economic Indicators:** GDP (annual growth), Unemployment rates, Energy Intensity, Inflation (HICP) - **18 EU Countries:** Austria, Belgium, Czech Republic, Germany, Denmark, Greece, Spain, Finland, France, Hungary, Ireland, Italy, Netherlands, Poland, Portugal, Romania, Sweden, Slovakia - **Time Range:** 2000-2023 (24 years of historical data) - **Data Source:** Official Eurostat REST API

**Key Features:** - ☁️ **Cloud-Native Architecture:** Fully deployed on Google Cloud Platform (BigQuery, Cloud Storage, Compute Engine, Dataproc) - 🏗️ **Infrastructure as Code:** Complete Terraform configuration for reproducible infrastructure provisioning - 🐳 **Containerized Services:** 8 Docker services orchestrated via Docker Compose with health checks and dependency management - 📥 **Automated Ingestion:** dlt pipeline fetching data from Eurostat API with incremental loading - 🔄 **Dual Stream Processing:** Real-time anomaly detection using both Apache Flink and Spark Structured Streaming - 🧮 **Dimensional Modeling:** dbt transformations with staging, intermediate, and mart layers following Kimball methodology - 📈 **Interactive Dashboard:** Multi-page Streamlit app with Plotly visualizations (choropleths, trends, heatmaps, radar charts) - 🚨 **Anomaly Detection:** Statistical z-score analysis identifying economic outliers with severity classification - 📊 **Composite Economic Index:** Normalized 0-100 score combining GDP, unemployment, and energy efficiency

**Use Cases:** - Economic trend analysis and forecasting - Cross-country comparative analysis - Real-time monitoring of economic anomalies - Policy impact assessment - Academic research on EU economic integration - Learning modern data engineering patterns and tools

**What Makes This Production-Grade:** - Partitioned and clustered BigQuery tables for query performance - Event-driven architecture with Kafka topics for loose coupling - Proper IAM and service account management - Multi-layer transformation architecture (raw → staging → intermediate → marts) - Automated testing and data quality checks via dbt - Comprehensive monitoring and observability - One-click deployment scripts with pre-flight validation

------------------------------------------------------------------------

## Table of Contents {#table-of-contents}

- [EU Economic Monitor](#eu-economic-monitor)
    - [Data Engineering Zoomcamp - Final Project {#data-engineering-zoomcamp---final-project}](#data-engineering-zoomcamp---final-project-data-engineering-zoomcamp---final-project)
  - [📊 Project Overview](#-project-overview)
  - [Table of Contents {#table-of-contents}](#table-of-contents-table-of-contents)
  - [](#)
  - [Architecture {#architecture}](#architecture-architecture)
    - [Technology stack {#technology-stack}](#technology-stack-technology-stack)
    - [Workflow Orchestration {#workflow-orchestration}](#workflow-orchestration-workflow-orchestration)
  - [Prerequisites {#prerequisites}](#prerequisites-prerequisites)
  - [Step 1 - Clone the repository {#step-1---clone-the-repository}](#step-1---clone-the-repository-step-1---clone-the-repository)
  - [Step 2 - Create a GCP project {#step-2---create-a-gcp-project}](#step-2---create-a-gcp-project-step-2---create-a-gcp-project)
  - [Step 3 - Enable GCP APIs {#step-3---enable-gcp-apis}](#step-3---enable-gcp-apis-step-3---enable-gcp-apis)
  - [Step 4 - Create the bootstrap service account {#step-4---create-the-bootstrap-service-account}](#step-4---create-the-bootstrap-service-account-step-4---create-the-bootstrap-service-account)
    - [4a - Create the service account](#4a---create-the-service-account)
    - [4b - Grant IAM roles](#4b---grant-iam-roles)
    - [4c - Download the key file](#4c---download-the-key-file)
  - [Step 5 - Configure environment variables {#step-5---configure-environment-variables}](#step-5---configure-environment-variables-step-5---configure-environment-variables)
    - [5a - Create .env](#5a---create-env)
    - [5b - Edit .env](#5b---edit-env)
    - [5c - Configure Terraform variables](#5c---configure-terraform-variables)
  - [Step 6 - Provision GCP infrastructure with Terraform {#step-6---provision-gcp-infrastructure-with-terraform}](#step-6---provision-gcp-infrastructure-with-terraform-step-6---provision-gcp-infrastructure-with-terraform)
  - [Step 7 - Build Docker images {#step-7---build-docker-images}](#step-7---build-docker-images-step-7---build-docker-images)
  - [Step 8 - Start long-running services {#step-8---start-long-running-services}](#step-8---start-long-running-services-step-8---start-long-running-services)
  - [Step 9 - Create Redpanda topics {#step-9---create-redpanda-topics}](#step-9---create-redpanda-topics-step-9---create-redpanda-topics)
  - [Step 10 - Run the data pipeline {#step-10---run-the-data-pipeline}](#step-10---run-the-data-pipeline-step-10---run-the-data-pipeline)
  - [Step 11 - Open the dashboard {#step-11---open-the-dashboard}](#step-11---open-the-dashboard-step-11---open-the-dashboard)
  - [Optional - PyFlink streaming job {#optional---pyflink-streaming-job}](#optional---pyflink-streaming-job-optional---pyflink-streaming-job)
  - [Tear-down {#tear-down}](#tear-down-tear-down)
  - [Windows - one-click batch scripts {#windows---one-click-batch-scripts}](#windows---one-click-batch-scripts-windows---one-click-batch-scripts)
    - [`run_pipeline.bat` - full pipeline runner](#run_pipelinebat---full-pipeline-runner)
    - [`clean_project.bat` - teardown and cleanup](#clean_projectbat---teardown-and-cleanup)
  - [Repository structure {#repository-structure}](#repository-structure-repository-structure)
  - [Data sources {#data-sources}](#data-sources-data-sources)
  - [BigQuery schema {#bigquery-schema}](#bigquery-schema-bigquery-schema)
    - [`eurostat_raw` dataset - raw ingestion layer {#eurostat\_raw-dataset---raw-ingestion-layer}](#eurostat_raw-dataset---raw-ingestion-layer-eurostat_raw-dataset---raw-ingestion-layer)
    - [`eurostat_processed` dataset - dbt marts {#eurostat\_processed-dataset---dbt-marts}](#eurostat_processed-dataset---dbt-marts-eurostat_processed-dataset---dbt-marts)
    - [dbt lineage {#dbt-lineage}](#dbt-lineage-dbt-lineage)
  - [Composite index methodology {#composite-index-methodology}](#composite-index-methodology-composite-index-methodology)
  - [Makefile reference {#makefile-reference}](#makefile-reference-makefile-reference)
  - [Troubleshooting {#troubleshooting}](#troubleshooting-troubleshooting)
    - [`make up` fails - port already in use {#make-up-fails---port-already-in-use}](#make-up-fails---port-already-in-use-make-up-fails---port-already-in-use)
    - [Terraform error: `Permission denied` or `403` {#terraform-error-permission-denied-or-403}](#terraform-error-permission-denied-or-403-terraform-error-permission-denied-or-403)
    - [dlt ingestion fails with `404` or `No data` {#dlt-ingestion-fails-with-404-or-no-data}](#dlt-ingestion-fails-with-404-or-no-data-dlt-ingestion-fails-with-404-or-no-data)
    - [dbt fails: `Table not found: eurostat_raw.*`](#dbt-fails-table-not-found-eurostat_raw)
    - [BigQuery dataset location error {#bigquery-dataset-location-error}](#bigquery-dataset-location-error-bigquery-dataset-location-error)
    - [Dashboard shows no data {#dashboard-shows-no-data}](#dashboard-shows-no-data-dashboard-shows-no-data)
    - [Flink job fails to start {#flink-job-fails-to-start}](#flink-job-fails-to-start-flink-job-fails-to-start)
    - [On Windows: `make` command not found {#on-windows-make-command-not-found}](#on-windows-make-command-not-found-on-windows-make-command-not-found)
  - [Acknowledgements](#acknowledgements)
  - [License {#license}](#license-license)

## 

## Architecture {#architecture}

```         
┌─────────────────────────────────────────────────────────────────┐
│                       DATA SOURCES                              │
│   Eurostat REST API  (GDP · Unemployment · Energy · Inflation)   │
└────────────────────────────┬────────────────────────────────────┘
                             │  HTTP / JSON-stat
                             ▼
┌────────────────────────────────────────────────────────────────┐
│                    INGESTION LAYER  (dlt)                       │
│   ingestion/eurostat_pipeline.py                               │
│   Destination: BigQuery  eurostat_raw                          │
│   Tables: gdp_annual · unemployment_annual ·                   │
│           energy_intensity · inflation_annual                  │
│   Partitioned by DATE (loaded_at) · Clustered by country_code  │
└───────────────┬────────────────────┬───────────────────────────┘
                │ Kafka events        │ BigQuery tables
                ▼                     ▼
┌──────────────────────┐  ┌─────────────────────────────────────┐
│   REDPANDA BROKER    │  │     BATCH PROCESSING  (Spark)        │
│  (Kafka-compatible)  │  │   spark/batch_job.py                │
│  port 19092 (ext)    │  │   Reads eurostat_raw →              │
│  Topics:             │  │   Computes YoY deltas + z-scores →  │
│  · ingestion.done    │  │   Writes eurostat_processed         │
│  · anomalies         │  └─────────────────┬───────────────────┘
└──────┬───────────────┘                    │ BigQuery tables
       │                                    ▼
       ▼                   ┌──────────────────────────────────────┐
┌────────────────────┐     │   TRANSFORMATIONS  (dbt)             │
│  ANOMALY CONSUMER  │     │   Staging → Intermediate → Marts     │
│  redpanda_consumer │     │   mart_gdp_trends                    │
│  z-score detection │     │   mart_unemployment_comparison       │
│  → anomalies topic │     │   mart_energy_intensity              │
└────────────────────┘     │   mart_composite_economic_index      │
       │                   │   mart_country_latest                │
       ▼                   └──────────────────┬───────────────────┘
┌────────────────────┐                        │
│  FLINK STREAMING   │                        ▼
│  flink/            │     ┌──────────────────────────────────────┐
│  Reads anomalies   │     │     DASHBOARD  (Streamlit + Plotly)  │
│  → BQ stream table │     │   http://localhost:8501              │
└────────────────────┘     │   Home: EU choropleth + KPIs         │
                           │   1_GDP_Analysis                     │
                           │   2_Unemployment                     │
                           │   3_Energy_Intensity                 │
                           │   4_Composite_Index                  │
                           └──────────────────────────────────────┘
```

### Technology stack {#technology-stack}

| Layer                  | Technology                  | Version     |
|------------------------|-----------------------------|-------------|
| Cloud platform         | GCP (BigQuery EU, GCS)      | \-          |
| Infrastructure-as-Code | Terraform                   | ≥ 1.5       |
| Batch ingestion        | dlt + eurostat library      | 0.4.x       |
| Stream broker          | Redpanda (Kafka-compatible) | v23.3       |
| Batch processing       | Apache Spark                | 3.5.x       |
| Stream processing      | Apache Flink (PyFlink)      | 1.17.x      |
| Transformations        | dbt-bigquery                | 1.7.x       |
| Dashboard              | Streamlit + Plotly          | 1.33 / 5.22 |
| Containerisation       | Docker + Docker Compose v2  | \-          |

### Workflow Orchestration {#workflow-orchestration}

This project uses a **lightweight orchestration approach** suitable for development and small-scale production workloads, without a dedicated workflow scheduler like Airflow or Prefect.

**Orchestration mechanisms:**

1.  **Docker Compose** (Service Orchestration)
    -   Manages 8 containerized services with dependency ordering
    -   Handles health checks, networking, and service restarts
    -   Services: Redpanda (+ console), dlt-ingestion, redpanda-consumer, Spark, Flink cluster (jobmanager + taskmanager), dbt, Streamlit dashboard
2.  **Makefile** (Task Automation)
    -   Provides simple CLI commands for common operations
    -   Key targets: `make pipeline`, `make ingest`, `make spark-batch`, `make dbt-run`, `make clean`
    -   See [Makefile reference](#makefile-reference) for full list
3.  **Batch Script** (`run_pipeline.bat` for Windows)
    -   **7-step automated workflow** with pre-flight checks:
        1.  Terraform (infrastructure provisioning)
        2.  Docker build (image creation)
        3.  Service startup (Redpanda, Flink, dashboard)
        4.  Topic creation (Kafka topics)
        5.  dlt ingestion (Eurostat API → BigQuery raw)
        6.  Spark batch job (raw → processed with YoY calculations)
        7.  dbt transformations (staging → marts)
4.  **Event-Driven Coordination** (Kafka/Redpanda)
    -   Topics act as event buses for loose coupling:
        -   `eurostat.ingestion.completed`
            -   signals downstream consumers
        -   `eurostat.anomalies` - triggers real-time Flink processing
    -   Services react to events rather than scheduled intervals

------------------------------------------------------------------------

## Prerequisites {#prerequisites}

Install the following on your local machine before you begin:

| Tool | Minimum version | Install guide |
|------------------------|------------------------|------------------------|
| **Docker Desktop** | Latest stable | https://docs.docker.com/get-docker/ |
| **Docker Compose** | v2 (bundled with Docker Desktop) | included with Docker Desktop |
| **Terraform** | ≥ 1.5 | https://developer.hashicorp.com/terraform/downloads |
| **Git** | Any | https://git-scm.com/downloads |
| **make** | Any | Windows: install via [Chocolatey](https://chocolatey.org/) - `choco install make`; macOS: included; Linux: `apt install make` |
| **GCP account** | With billing enabled | https://console.cloud.google.com |

> On **Windows**, run all `make` commands from Git Bash or WSL, not PowerShell.

Verify your tools:

``` bash
docker --version           # Docker version 24+ expected
docker compose version     # Docker Compose version v2.x expected
terraform --version        # Terraform v1.5+ expected
make --version
```

> **⚡ Windows Users:** If you don't have `make` installed, you can skip installing it and use `run_pipeline.bat` instead, which provides a one-click automated workflow. See [Windows - one-click batch scripts](#windows---one-click-batch-scripts) below.

------------------------------------------------------------------------

## Step 1 - Clone the repository {#step-1---clone-the-repository}

``` bash
git clone <repo-url>
cd final_project
```

------------------------------------------------------------------------

## Step 2 - Create a GCP project {#step-2---create-a-gcp-project}

1.  Go to https://console.cloud.google.com/projectcreate
2.  Create a new project (e.g. `eu-monitor-demo`). Note the **Project ID** exactly - it is used throughout.
3.  Make sure **billing is enabled** on the project: https://console.cloud.google.com/billing

> The Project ID is lowercase, may contain hyphens, and is distinct from the display name.

------------------------------------------------------------------------

## Step 3 - Enable GCP APIs {#step-3---enable-gcp-apis}

Open **Cloud Shell** (the `>_` terminal button in the top-right of the GCP Console) and run:

``` bash
gcloud config set project YOUR_PROJECT_ID

gcloud services enable \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  cloudresourcemanager.googleapis.com \
  storage.googleapis.com \
  bigquery.googleapis.com
```

Wait \~60 seconds for the APIs to propagate before continuing.

> Replace `YOUR_PROJECT_ID` with your actual project ID in every command below.

------------------------------------------------------------------------

## Step 4 - Create the bootstrap service account {#step-4---create-the-bootstrap-service-account}

Terraform needs a **bootstrap service account** with sufficient permissions to create GCP resources on your behalf. Run all commands in **Cloud Shell**.

### 4a - Create the service account

``` bash
gcloud iam service-accounts create eu-monitor-bootstrap \
  --display-name="EU Monitor Bootstrap SA" \
  --project=YOUR_PROJECT_ID
```

### 4b - Grant IAM roles

``` bash
SA="eu-monitor-bootstrap@YOUR_PROJECT_ID.iam.gserviceaccount.com"
PROJECT="YOUR_PROJECT_ID"

for ROLE in \
  roles/iam.serviceAccountAdmin \
  roles/iam.serviceAccountKeyAdmin \
  roles/storage.admin \
  roles/bigquery.admin \
  roles/resourcemanager.projectIamAdmin; do

  gcloud projects add-iam-policy-binding "$PROJECT" \
    --member="serviceAccount:$SA" \
    --role="$ROLE"
done
```

| Role | Why it is needed |
|------------------------------------|------------------------------------|
| `iam.serviceAccountAdmin` | Create the pipeline runtime SA (`eurostat-pipeline-sa`) |
| `iam.serviceAccountKeyAdmin` | Generate and download the pipeline SA JSON key |
| `storage.admin` | Create and configure the GCS data lake bucket |
| `bigquery.admin` | Create datasets and partitioned tables |
| `resourcemanager.projectIamAdmin` | Bind IAM roles to the pipeline SA after creation |

### 4c - Download the key file

``` bash
# Run this in Cloud Shell - it downloads the key as JSON
gcloud iam service-accounts keys create eu-monitor-bootstrap-key.json \
  --iam-account="eu-monitor-bootstrap@YOUR_PROJECT_ID.iam.gserviceaccount.com"
```

Download `eu-monitor-bootstrap-key.json` from Cloud Shell (click the three-dot menu → Download) and save it to:

```         
final_project/credentials/service-account.json
```

> **🔑 CRITICAL:** This file must be placed at exactly `credentials/service-account.json` relative to the project root. The pipeline cannot run without it.

**Steps to save the key:**
1. Create the `credentials/` directory if it doesn't exist: `mkdir credentials`
2. Download the key file from Cloud Shell (three-dot menu → Download)
3. Rename it to `service-account.json`
4. Move it to `final_project/credentials/service-account.json`
5. Verify the file path: `ls credentials/service-account.json` should show the file

> The `credentials/` directory is gitignored - this file is **never committed** to version control.

------------------------------------------------------------------------

## Step 5 - Configure environment variables {#step-5---configure-environment-variables}

### 5a - Create .env

``` bash
# From the project root
make setup
```

This copies `.env.example` to `.env` and creates the `credentials/` directory if absent.

### 5b - Edit .env

Open `.env` in any text editor and fill in these values:

``` bash
# ── Required - replace with your actual values ──────────────
GCP_PROJECT_ID=your-project-id          # e.g. eu-monitor-demo
GCS_BUCKET_NAME=eurostat-data-lake-your-project-id  # must be globally unique

# ── Optional - defaults work for most setups ─────────────────
GCP_REGION=europe-west1
GCP_ZONE=europe-west1-b
BQ_RAW_DATASET=eurostat_raw
BQ_PROCESSED_DATASET=eurostat_processed
GOOGLE_APPLICATION_CREDENTIALS=/credentials/service-account.json
REDPANDA_BROKERS=redpanda:9092
KAFKA_TOPIC_INGESTION=eurostat.ingestion.completed
KAFKA_TOPIC_ANOMALIES=eurostat.anomalies
EUROSTAT_COUNTRIES=DE,FR,IT,ES,PL,NL,BE,SE,AT,PT,FI,IE,CZ,RO,HU,DK,EL,SK
EUROSTAT_START_YEAR=2000
EUROSTAT_END_YEAR=2023
USE_MOCK_DATA=false
```

> `GCS_BUCKET_NAME` must be **globally unique** across all of GCP. A safe convention: `eurostat-data-lake-<YOUR_PROJECT_ID>`.

### 5c - Configure Terraform variables

``` bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform/terraform.tfvars`:

``` hcl
project_id      = "your-project-id"             # same as GCP_PROJECT_ID above
region          = "europe-west1"
zone            = "europe-west1-b"
gcs_bucket_name = "eurostat-data-lake-your-project-id"   # same as GCS_BUCKET_NAME above
```

Return to the project root:

``` bash
cd ..
```

> **\u2705 Configuration Complete!** You've finished all the prerequisite steps. You're now ready to provision infrastructure and run the pipeline.
>
> **Windows Users:** Instead of following Steps 6-11 manually, you can simply run `run_pipeline.bat` which executes all remaining steps automatically with pre-flight validation. See [Windows - one-click batch scripts](#windows---one-click-batch-scripts) for details.

------------------------------------------------------------------------

## Step 6 - Provision GCP infrastructure with Terraform {#step-6---provision-gcp-infrastructure-with-terraform}

``` bash
make terraform-init    # download provider plugins
make terraform-plan    # preview what will be created (safe, no changes)
make terraform-apply   # create GCP resources
```

When prompted by `terraform apply`, type **`yes`** and press Enter.

Terraform creates: - GCS bucket (`eurostat-data-lake-<project-id>`) in EU multi-region - BigQuery dataset `eurostat_raw` (EU location) - BigQuery dataset `eurostat_processed` (EU location) - Service account `eurostat-pipeline-sa` with roles: `bigquery.dataEditor`, `bigquery.jobUser`, `storage.objectAdmin`

> The pipeline containers use `credentials/service-account.json` (your bootstrap key) via a Docker volume mount - no additional key files are needed.

------------------------------------------------------------------------

## Step 7 - Build Docker images {#step-7---build-docker-images}

``` bash
make build
```

This builds all service images (ingestion, spark, flink, dbt, dashboard). The first build takes 5–10 minutes; subsequent builds use the layer cache and are faster.

To force a clean rebuild from scratch (e.g. after changing a Dockerfile):

``` bash
make build-clean
```

------------------------------------------------------------------------

## Step 8 - Start long-running services {#step-8---start-long-running-services}

``` bash
make up
```

This starts the following services in the background:

| Service | Description | Port |
|------------------------|------------------------|------------------------|
| `redpanda` | Kafka-compatible stream broker | 19092 (ext), 9092 (int) |
| `redpanda-console` | Web UI for inspecting topics/messages | http://localhost:8080 |
| `redpanda-consumer` | Reads ingestion events, detects anomalies | \- |
| `flink-jobmanager` | Flink cluster job manager | http://localhost:8081 |
| `flink-taskmanager` | Flink cluster task manager | \- |
| `dashboard` | Streamlit analytics dashboard | http://localhost:8501 |

Wait for all services to become healthy before proceeding. You can monitor them:

``` bash
make logs           # tail all service logs
docker ps           # check container status (should show "Up" or "(healthy)")
```

Wait until you see `redpanda` report `kafka is ready` in the logs (usually 15–30 seconds).

------------------------------------------------------------------------

## Step 9 - Create Redpanda topics {#step-9---create-redpanda-topics}

``` bash
make create-topics
```

This creates two Kafka topics inside the running Redpanda broker:

| Topic                          | Purpose                                   |
|------------------------------------|------------------------------------|
| `eurostat.ingestion.completed` | Ingestion pipeline notifies on completion |
| `eurostat.anomalies`           | Consumer publishes anomaly alerts         |

You can verify the topics were created at http://localhost:8080 (Redpanda Console → Topics).

------------------------------------------------------------------------

## Step 10 - Run the data pipeline {#step-10---run-the-data-pipeline}

``` bash
make pipeline
```

This runs three steps in sequence:

```         
Step 1/3 - dlt Ingestion
  Downloads GDP, Unemployment, Energy Intensity, Inflation data from
  the Eurostat REST API for 18 EU countries (2000–2023).
  Writes to BigQuery: eurostat_raw.gdp_annual, unemployment_annual,
                      energy_intensity, inflation_annual
  Duration: ~5–10 min (first run, network dependent)

Step 2/3 - Spark Batch Processing
  Reads eurostat_raw → computes year-on-year deltas and z-scores.
  Writes enriched tables to BigQuery: eurostat_processed.
  Duration: ~3–5 min

Step 3/3 - dbt Transformations
  Runs dbt deps → dbt run → dbt test.
  Materialises 11 models (staging views → intermediate tables → mart tables).
  All 31 tests must pass.
  Duration: ~2–4 min
```

You can also run each step individually:

``` bash
make ingest         # dlt ingestion only
make spark-batch    # Spark batch only
make dbt-run        # dbt transformations + tests only
```

------------------------------------------------------------------------

## Step 11 - Open the dashboard {#step-11---open-the-dashboard}

``` bash
make open-dashboard
# Opens http://localhost:8501
```

Or navigate directly to http://localhost:8501.

The dashboard has five pages:

| Page | Description |
|------------------------------------|------------------------------------|
| **Home** | EU choropleth map, country KPI cards, anomaly alerts |
| **GDP Analysis** | GDP trends, year-on-year growth, country comparison |
| **Unemployment** | Unemployment rates over time, EU average benchmark |
| **Energy Intensity** | Energy efficiency trends by country |
| **Composite Index** | Combined economic score (0–100) ranking all 18 EU countries |

------------------------------------------------------------------------

## Optional - PyFlink streaming job {#optional---pyflink-streaming-job}

After `make up` and `make create-topics`, you can submit the PyFlink streaming job to continuously process anomaly messages from Redpanda into BigQuery:

``` bash
make flink-streaming
```

This submits `flink/streaming_job.py` to the running Flink cluster. The job: 1. Reads JSON anomaly messages from the `eurostat.anomalies` topic 2. Enriches each message with a `processed_at` timestamp 3. Writes records to BigQuery `eurostat_raw.anomaly_stream_summaries` via the Streaming Insert API

Monitor the job at http://localhost:8081 (Flink Web UI).

> The Flink job is **optional** - the main dashboard does not depend on it. It provides real-time streaming analytics as an additional data flow.

------------------------------------------------------------------------

## Tear-down {#tear-down}

Stop all containers:

``` bash
make down
```

Destroy GCP infrastructure (incurs no further costs after this):

``` bash
make terraform-destroy
```

> `terraform destroy` will delete the GCS bucket, BigQuery datasets, and service account. All ingested data will be lost. Confirm with `yes` when prompted.

------------------------------------------------------------------------

## Windows - one-click batch scripts {#windows---one-click-batch-scripts}

**🎯 For Windows users:** If you don't have `make` installed or prefer a simpler workflow, use these batch scripts that automate the entire pipeline.

**Prerequisites before running:**
1. ✅ Completed Steps 1-5 (GCP project setup, service account, environment variables)
2. ✅ `credentials/service-account.json` exists in the project root
3. ✅ `.env` file is configured with your GCP project ID
4. ✅ `terraform.tfvars` is configured (or Terraform is not installed)
5. ✅ Docker Desktop is running

### `run_pipeline.bat` - full pipeline runner

Double-click (or run from a Command Prompt in the project root):

``` cmd
run_pipeline.bat
```

What it does, in order:

| Step | Action |
|------------------------------------|------------------------------------|
| Pre-flight | Verifies Docker, Docker Compose v2, `.env`, `credentials/service-account.json`, `terraform.tfvars` |
| 1/7 | `terraform init` + `terraform apply` - provisions GCP (skipped automatically if Terraform is not installed) |
| 2/7 | `docker compose build` - builds all project images |
| 3/7 | `docker compose up -d` - starts Redpanda, Flink cluster, anomaly consumer, dashboard |
| 4/7 | Creates the two Redpanda Kafka topics |
| 5/7 | Runs the dlt ingestion container (Eurostat → BigQuery raw) |
| 6/7 | Runs the Spark batch container (raw → processed) |
| 7/7 | Runs the dbt container (staging → intermediate → marts) |
| Done | Opens `http://localhost:8501` in your default browser |

Each step exits with an error message if it fails - no silent failures.

> **\ud83d\udd11 Common Issue:** If the script fails at pre-flight with "credentials/service-account.json not found", make sure you completed Step 4c and saved the GCP service account key to exactly `credentials/service-account.json` in the project root.

### `clean_project.bat` - teardown and cleanup

``` cmd
clean_project.bat
```

Interactive menu with three levels:

| Level | What is removed |
|------------------------------------|------------------------------------|
| **1 - Soft clean** | Stops containers, removes volumes and orphaned networks. Docker images and GCP resources are kept. |
| **2 - Hard clean** | Everything in soft clean, plus all project Docker images and the Docker build cache are deleted. Next `run_pipeline.bat` will rebuild from scratch. |
| **3 - Full reset** | Everything in hard clean, plus `terraform destroy` - **deletes all BigQuery datasets and GCS bucket**. Requires `YES` confirmation. |

> **Tip:** After a soft clean you can immediately re-run `run_pipeline.bat` without rebuilding images. After a hard clean, images are rebuilt automatically on the next run.

------------------------------------------------------------------------

## Repository structure {#repository-structure}

```         
final_project/
├── .env.example                  # Environment variable template - copy to .env
├── .gitignore
├── docker-compose.yml            # All service definitions
├── Makefile                      # Developer commands (see Makefile Reference)
├── run_pipeline.bat              # Windows: one-click full pipeline runner
├── clean_project.bat             # Windows: interactive teardown / clean menu
│
├── terraform/
│   ├── providers.tf              # Google provider configuration
│   ├── variables.tf              # Input variables with defaults
│   ├── main.tf                   # GCS bucket · BigQuery datasets · Service Account
│   ├── outputs.tf                # Outputs: bucket name, SA email, dataset IDs
│   └── terraform.tfvars.example  # Copy to terraform.tfvars and fill in values
│
├── credentials/                  # !! gitignored - place service-account.json here
│   └── service-account.json      # Bootstrap SA key (downloaded in Step 4c)
│
├── ingestion/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── eurostat_pipeline.py      # dlt pipeline - fetches 4 Eurostat datasets → BQ raw
│   └── redpanda_consumer.py      # Reads ingestion events, detects anomalies, publishes alerts
│
├── spark/
│   ├── Dockerfile
│   └── batch_job.py              # YoY deltas + z-scores · raw → processed BQ tables
│
├── flink/
│   ├── Dockerfile.flink
│   ├── flink-config.yaml         # Flink cluster configuration
│   ├── pyproject.flink.toml      # Python dependencies for the Flink job
│   └── streaming_job.py          # PyFlink job: anomalies topic → BQ stream table
│
├── dbt_project/
│   ├── Dockerfile
│   ├── dbt_project.yml           # Project config - model paths, materialisation
│   ├── profiles.yml              # BigQuery connection profile
│   ├── packages.yml              # dbt-utils dependency
│   └── models/
│       ├── sources.yml           # Declares eurostat_raw source tables
│       ├── staging/              # stg_* views - cast and clean raw tables
│       ├── intermediate/         # int_* tables - joins and window functions
│       └── marts/                # mart_* partitioned tables - analytics-ready
│
└── dashboard/
    ├── Dockerfile
    ├── requirements.txt
    ├── app.py                    # Home page: EU map · KPI cards · anomaly alerts
    ├── .streamlit/
    │   └── config.toml           # Streamlit theme (Tableau dark)
    ├── pages/
    │   ├── 1_GDP_Analysis.py
    │   ├── 2_Unemployment.py
    │   ├── 3_Energy_Intensity.py
    │   └── 4_Composite_Index.py
    └── utils/
        ├── bigquery_client.py    # BQ data access (with mock-data fallback)
        ├── charts.py             # Plotly chart builders
        ├── style.py              # Shared CSS / dark-theme helpers
        └── __init__.py
```

------------------------------------------------------------------------

## Data sources {#data-sources}

| Dataset | Eurostat code | Description |
|------------------------|------------------------|------------------------|
| GDP | `nama_10_gdp` | GDP and main aggregates - annual, current prices |
| Unemployment | `une_rt_a` | Unemployment rate by sex and age - annual |
| Energy Intensity | `nrg_ind_ei` | Energy intensity of the economy (kgoe per 1000 EUR GDP) |
| Inflation (HICP) | `prc_hicp_aind` | Harmonised Index of Consumer Prices - annual |

**Countries (18):** AT, BE, CZ, DE, DK, EL, ES, FI, FR, HU, IE, IT, NL, PL, PT, RO, SE, SK\
**Time range:** 2000 – 2023

Data is fetched via the [Eurostat REST API](https://ec.europa.eu/eurostat/web/json-and-unicode-web-services/) (no API key required).

------------------------------------------------------------------------

## BigQuery schema {#bigquery-schema}

### `eurostat_raw` dataset - raw ingestion layer {#eurostat_raw-dataset---raw-ingestion-layer}

All raw tables are: - Partitioned by `loaded_at DATE` (ingestion date) - Clustered by `[country_code, year]`

| Table | Key columns |
|------------------------------------|------------------------------------|
| `gdp_annual` | `country_code`, `year`, `gdp_value`, `unit`, `loaded_at` |
| `unemployment_annual` | `country_code`, `year`, `unemployment_rate`, `sex`, `age`, `loaded_at` |
| `energy_intensity` | `country_code`, `year`, `energy_intensity_value`, `unit`, `loaded_at` |
| `inflation_annual` | `country_code`, `year`, `hicp_value`, `unit`, `loaded_at` |
| `anomaly_stream_summaries` | `country_code`, `dataset`, `anomaly_score`, `processed_at` |

### `eurostat_processed` dataset - dbt marts {#eurostat_processed-dataset---dbt-marts}

| Table | Partition | Cluster | Description |
|------------------|------------------|------------------|------------------|
| `mart_gdp_trends` | `reference_date` (year) | `country_code` | GDP values + YoY growth % |
| `mart_unemployment_comparison` | `reference_date` (year) | `country_code` | Unemployment rates + EU average |
| `mart_energy_intensity` | `reference_date` (year) | `country_code` | Energy intensity + YoY delta |
| `mart_composite_economic_index` | `reference_date` (year) | `country_code` | Composite score (0–100) |
| `mart_country_latest` | \- | `country_code` | Latest-year snapshot per country |

### dbt lineage {#dbt-lineage}

```         
sources (eurostat_raw)
    └── stg_gdp / stg_unemployment / stg_energy / stg_inflation   [views]
            └── int_country_indicators                               [table]
                    └── int_yoy_deltas                               [table]
                            ├── mart_gdp_trends                      [partitioned table]
                            ├── mart_unemployment_comparison         [partitioned table]
                            ├── mart_energy_intensity                [partitioned table]
                            ├── mart_composite_economic_index        [partitioned table]
                            └── mart_country_latest                  [table]
```

------------------------------------------------------------------------

## Composite index methodology {#composite-index-methodology}

The composite score (0–100) combines three normalised sub-scores, calculated **within each calendar year** across all 18 EU countries in scope:

$$\text{score}(x) = \frac{x - x_{\min}}{x_{\max} - x_{\min}} \times 100$$

| Sub-score | Source | Direction |
|------------------------|------------------------|------------------------|
| GDP Growth Score | YoY GDP growth % | Higher = better |
| Unemployment Score | Unemployment rate | **Inverted** - lower rate = better |
| Energy Score | Energy intensity (kgoe/1k€) | **Inverted** - lower intensity = better |

$$\text{Composite} = \frac{\text{GDP Score} + \text{Unemp. Score} + \text{Energy Score}}{3}$$

A score of 100 means the country ranks best on all three metrics in that year relative to peers.

------------------------------------------------------------------------

## Makefile reference {#makefile-reference}

``` bash
make setup              # Copy .env.example → .env  (run once at setup)

# Terraform
make terraform-init     # Download Terraform provider plugins
make terraform-plan     # Preview infrastructure changes (read-only)
make terraform-apply    # Create GCP resources
make terraform-destroy  # Delete all GCP resources (irreversible)

# Docker
make build              # Build all Docker images (cached)
make build-clean        # Rebuild all images from scratch (no cache)
make up                 # Start all long-running services
make down               # Stop and remove all containers
make logs               # Tail logs from all services

# Pipeline steps
make create-topics      # Create Redpanda Kafka topics
make ingest             # Run dlt ingestion (Eurostat → BQ raw)
make spark-batch        # Run Spark batch job (BQ raw → BQ processed)
make dbt-run            # Run dbt models and tests
make pipeline           # Full pipeline: ingest + spark-batch + dbt-run

# Streaming (optional)
make flink-streaming    # Submit PyFlink job to the running Flink cluster

# Shortcuts
make open-dashboard     # Open http://localhost:8501 in your browser
make open-console       # Open http://localhost:8080 (Redpanda Console)
make open-flink         # Open http://localhost:8081 (Flink Web UI)
```

------------------------------------------------------------------------

## Troubleshooting {#troubleshooting}

### `make up` fails - port already in use {#make-up-fails---port-already-in-use}

```         
Error: bind: address already in use
```

Another process is using one of the ports (8080, 8081, 8501, 19092). Stop the conflicting process or change the host port in `docker-compose.yml`.

------------------------------------------------------------------------

### Terraform error: `Permission denied` or `403` {#terraform-error-permission-denied-or-403}

Your bootstrap service account is missing a required IAM role. Re-run the role binding commands from Step 4b, then retry `make terraform-apply`.

------------------------------------------------------------------------

### dlt ingestion fails with `404` or `No data` {#dlt-ingestion-fails-with-404-or-no-data}

The Eurostat API occasionally returns no data for certain country-year combinations. This is normal. The pipeline will still succeed and load whatever data is available.

------------------------------------------------------------------------

### dbt fails: `Table not found: eurostat_raw.*`

The Spark batch job must complete successfully before dbt can run. Run `make spark-batch` first, or use `make pipeline` which enforces the correct order.

------------------------------------------------------------------------

### BigQuery dataset location error {#bigquery-dataset-location-error}

```         
Not found: Dataset was not found in location EU
```

Ensure `GCP_PROJECT_ID` in `.env` and `project_id` in `terraform.tfvars` are identical and match your actual GCP project. Terraform creates datasets in `EU` location - do not change this.

------------------------------------------------------------------------

### Dashboard shows no data {#dashboard-shows-no-data}

1.  Confirm `GCP_PROJECT_ID` and `BQ_PROCESSED_DATASET` are set correctly in `.env`.

2.  Confirm `credentials/service-account.json` exists and is valid.

3.  Confirm `make pipeline` completed without errors - check `docker logs eurostat-dbt`.

4.  To test without BigQuery, set `USE_MOCK_DATA=true` in `.env` and restart the dashboard:

    ``` bash
    docker compose restart dashboard
    ```

------------------------------------------------------------------------

### Flink job fails to start {#flink-job-fails-to-start}

Ensure `make up` has been running for at least 30 seconds so that `flink-taskmanager` is registered with `flink-jobmanager`. Check the Flink Web UI at http://localhost:8081 - you should see `1 TaskManager` registered before submitting the job.

------------------------------------------------------------------------

### On Windows: `make` command not found {#on-windows-make-command-not-found}

You have three options:

1.  **Use the provided batch scripts** (no extra tools needed):

    -   `run_pipeline.bat` - runs the full pipeline end-to-end
    -   `clean_project.bat` - interactive teardown

2.  Install `make` via Chocolatey:

    ``` cmd
    choco install make
    ```

3.  Run all `make` commands from **Git Bash** or **WSL** where `make` is natively available.

------------------------------------------------------------------------

## Acknowledgements

Thanks to the [DataTalks.Club](https://datatalks.club/) community for providing a structured learning path and covering a wide stack of data engineering tools through the [Data Engineering Zoomcamp](https://github.com/DataTalksClub/data-engineering-zoomcamp).

------------------------------------------------------------------------

## License {#license}

MIT