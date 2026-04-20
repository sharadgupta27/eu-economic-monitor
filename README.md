# 🇪🇺 EU Economic Monitor
### Data Engineering Zoomcamp — Final Project

A **production-grade data engineering pipeline** that ingests European economic statistics from Eurostat, processes them through a multi-layer transformation stack, detects anomalies via a Kafka-compatible stream, and visualises everything in a Streamlit dashboard.

> **Reproduction time:** ~30 min for GCP setup + ~20 min for first pipeline run.  
> Everything runs in Docker — no local Python environments needed beyond Docker Desktop and Terraform.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Prerequisites](#prerequisites)
3. [Step 1 — Clone the repository](#step-1--clone-the-repository)
4. [Step 2 — Create a GCP project](#step-2--create-a-gcp-project)
5. [Step 3 — Enable GCP APIs](#step-3--enable-gcp-apis)
6. [Step 4 — Create the bootstrap service account](#step-4--create-the-bootstrap-service-account)
7. [Step 5 — Configure environment variables](#step-5--configure-environment-variables)
8. [Step 6 — Provision GCP infrastructure with Terraform](#step-6--provision-gcp-infrastructure-with-terraform)
9. [Step 7 — Build Docker images](#step-7--build-docker-images)
10. [Step 8 — Start long-running services](#step-8--start-long-running-services)
11. [Step 9 — Create Redpanda topics](#step-9--create-redpanda-topics)
12. [Step 10 — Run the data pipeline](#step-10--run-the-data-pipeline)
13. [Step 11 — Open the dashboard](#step-11--open-the-dashboard)
14. [Optional — PyFlink streaming job](#optional--pyflink-streaming-job)
15. [Tear-down](#tear-down)
16. [Windows — one-click batch scripts](#windows--one-click-batch-scripts)
17. [Repository structure](#repository-structure)
18. [Data sources](#data-sources)
19. [BigQuery schema](#bigquery-schema)
20. [Composite index methodology](#composite-index-methodology)
21. [Makefile reference](#makefile-reference)
22. [Troubleshooting](#troubleshooting)

---

## Architecture

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

### Technology stack

| Layer | Technology | Version |
|---|---|---|
| Cloud platform | GCP (BigQuery EU, GCS) | — |
| Infrastructure-as-Code | Terraform | ≥ 1.5 |
| Batch ingestion | dlt + eurostat library | 0.4.x |
| Stream broker | Redpanda (Kafka-compatible) | v23.3 |
| Batch processing | Apache Spark | 3.5.x |
| Stream processing | Apache Flink (PyFlink) | 1.17.x |
| Transformations | dbt-bigquery | 1.7.x |
| Dashboard | Streamlit + Plotly | 1.33 / 5.22 |
| Containerisation | Docker + Docker Compose v2 | — |

---

## Prerequisites

Install the following on your local machine before you begin:

| Tool | Minimum version | Install guide |
|---|---|---|
| **Docker Desktop** | Latest stable | https://docs.docker.com/get-docker/ |
| **Docker Compose** | v2 (bundled with Docker Desktop) | included with Docker Desktop |
| **Terraform** | ≥ 1.5 | https://developer.hashicorp.com/terraform/downloads |
| **Git** | Any | https://git-scm.com/downloads |
| **make** | Any | Windows: install via [Chocolatey](https://chocolatey.org/) — `choco install make`; macOS: included; Linux: `apt install make` |
| **GCP account** | With billing enabled | https://console.cloud.google.com |

> On **Windows**, run all `make` commands from Git Bash or WSL, not PowerShell.

Verify your tools:
```bash
docker --version           # Docker version 24+ expected
docker compose version     # Docker Compose version v2.x expected
terraform --version        # Terraform v1.5+ expected
make --version
```

---

## Step 1 — Clone the repository

```bash
git clone <repo-url>
cd final_project
```

---

## Step 2 — Create a GCP project

1. Go to https://console.cloud.google.com/projectcreate
2. Create a new project (e.g. `eu-monitor-demo`). Note the **Project ID** exactly — it is used throughout.
3. Make sure **billing is enabled** on the project: https://console.cloud.google.com/billing

> The Project ID is lowercase, may contain hyphens, and is distinct from the display name.

---

## Step 3 — Enable GCP APIs

Open **Cloud Shell** (the `>_` terminal button in the top-right of the GCP Console) and run:

```bash
gcloud config set project YOUR_PROJECT_ID

gcloud services enable \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  cloudresourcemanager.googleapis.com \
  storage.googleapis.com \
  bigquery.googleapis.com
```

Wait ~60 seconds for the APIs to propagate before continuing.

> Replace `YOUR_PROJECT_ID` with your actual project ID in every command below.

---

## Step 4 — Create the bootstrap service account

Terraform needs a **bootstrap service account** with sufficient permissions to create GCP resources on your behalf. Run all commands in **Cloud Shell**.

### 4a — Create the service account

```bash
gcloud iam service-accounts create eu-monitor-bootstrap \
  --display-name="EU Monitor Bootstrap SA" \
  --project=YOUR_PROJECT_ID
```

### 4b — Grant IAM roles

```bash
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
|---|---|
| `iam.serviceAccountAdmin` | Create the pipeline runtime SA (`eurostat-pipeline-sa`) |
| `iam.serviceAccountKeyAdmin` | Generate and download the pipeline SA JSON key |
| `storage.admin` | Create and configure the GCS data lake bucket |
| `bigquery.admin` | Create datasets and partitioned tables |
| `resourcemanager.projectIamAdmin` | Bind IAM roles to the pipeline SA after creation |

### 4c — Download the key file

```bash
# Run this in Cloud Shell — it downloads the key as JSON
gcloud iam service-accounts keys create eu-monitor-bootstrap-key.json \
  --iam-account="eu-monitor-bootstrap@YOUR_PROJECT_ID.iam.gserviceaccount.com"
```

Download `eu-monitor-bootstrap-key.json` from Cloud Shell (click the three-dot menu → Download) and save it to:

```
final_project/credentials/service-account.json
```

> The `credentials/` directory is gitignored — this file is **never committed**.  
> If the directory does not exist yet, create it: `mkdir credentials` (in the project root).

---

## Step 5 — Configure environment variables

### 5a — Create .env

```bash
# From the project root
make setup
```

This copies `.env.example` to `.env` and creates the `credentials/` directory if absent.

### 5b — Edit .env

Open `.env` in any text editor and fill in these values:

```bash
# ── Required — replace with your actual values ──────────────
GCP_PROJECT_ID=your-project-id          # e.g. eu-monitor-demo
GCS_BUCKET_NAME=eurostat-data-lake-your-project-id  # must be globally unique

# ── Optional — defaults work for most setups ─────────────────
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

### 5c — Configure Terraform variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform/terraform.tfvars`:

```hcl
project_id      = "your-project-id"             # same as GCP_PROJECT_ID above
region          = "europe-west1"
zone            = "europe-west1-b"
gcs_bucket_name = "eurostat-data-lake-your-project-id"   # same as GCS_BUCKET_NAME above
```

Return to the project root:
```bash
cd ..
```

---

## Step 6 — Provision GCP infrastructure with Terraform

```bash
make terraform-init    # download provider plugins
make terraform-plan    # preview what will be created (safe, no changes)
make terraform-apply   # create GCP resources
```

When prompted by `terraform apply`, type **`yes`** and press Enter.

Terraform creates:
- GCS bucket (`eurostat-data-lake-<project-id>`) in EU multi-region
- BigQuery dataset `eurostat_raw` (EU location)
- BigQuery dataset `eurostat_processed` (EU location)
- Service account `eurostat-pipeline-sa` with roles: `bigquery.dataEditor`, `bigquery.jobUser`, `storage.objectAdmin`

> The pipeline containers use `credentials/service-account.json` (your bootstrap key) via a Docker volume mount — no additional key files are needed.

---

## Step 7 — Build Docker images

```bash
make build
```

This builds all service images (ingestion, spark, flink, dbt, dashboard). The first build takes 5–10 minutes; subsequent builds use the layer cache and are faster.

To force a clean rebuild from scratch (e.g. after changing a Dockerfile):

```bash
make build-clean
```

---

## Step 8 — Start long-running services

```bash
make up
```

This starts the following services in the background:

| Service | Description | Port |
|---|---|---|
| `redpanda` | Kafka-compatible stream broker | 19092 (ext), 9092 (int) |
| `redpanda-console` | Web UI for inspecting topics/messages | http://localhost:8080 |
| `redpanda-consumer` | Reads ingestion events, detects anomalies | — |
| `flink-jobmanager` | Flink cluster job manager | http://localhost:8081 |
| `flink-taskmanager` | Flink cluster task manager | — |
| `dashboard` | Streamlit analytics dashboard | http://localhost:8501 |

Wait for all services to become healthy before proceeding. You can monitor them:

```bash
make logs           # tail all service logs
docker ps           # check container status (should show "Up" or "(healthy)")
```

Wait until you see `redpanda` report `kafka is ready` in the logs (usually 15–30 seconds).

---

## Step 9 — Create Redpanda topics

```bash
make create-topics
```

This creates two Kafka topics inside the running Redpanda broker:

| Topic | Purpose |
|---|---|
| `eurostat.ingestion.completed` | Ingestion pipeline notifies on completion |
| `eurostat.anomalies` | Consumer publishes anomaly alerts |

You can verify the topics were created at http://localhost:8080 (Redpanda Console → Topics).

---

## Step 10 — Run the data pipeline

```bash
make pipeline
```

This runs three steps in sequence:

```
Step 1/3 — dlt Ingestion
  Downloads GDP, Unemployment, Energy Intensity, Inflation data from
  the Eurostat REST API for 18 EU countries (2000–2023).
  Writes to BigQuery: eurostat_raw.gdp_annual, unemployment_annual,
                      energy_intensity, inflation_annual
  Duration: ~5–10 min (first run, network dependent)

Step 2/3 — Spark Batch Processing
  Reads eurostat_raw → computes year-on-year deltas and z-scores.
  Writes enriched tables to BigQuery: eurostat_processed.
  Duration: ~3–5 min

Step 3/3 — dbt Transformations
  Runs dbt deps → dbt run → dbt test.
  Materialises 11 models (staging views → intermediate tables → mart tables).
  All 31 tests must pass.
  Duration: ~2–4 min
```

You can also run each step individually:

```bash
make ingest         # dlt ingestion only
make spark-batch    # Spark batch only
make dbt-run        # dbt transformations + tests only
```

---

## Step 11 — Open the dashboard

```bash
make open-dashboard
# Opens http://localhost:8501
```

Or navigate directly to http://localhost:8501.

The dashboard has five pages:

| Page | Description |
|---|---|
| **Home** | EU choropleth map, country KPI cards, anomaly alerts |
| **GDP Analysis** | GDP trends, year-on-year growth, country comparison |
| **Unemployment** | Unemployment rates over time, EU average benchmark |
| **Energy Intensity** | Energy efficiency trends by country |
| **Composite Index** | Combined economic score (0–100) ranking all 18 EU countries |

---

## Optional — PyFlink streaming job

After `make up` and `make create-topics`, you can submit the PyFlink streaming job to continuously process anomaly messages from Redpanda into BigQuery:

```bash
make flink-streaming
```

This submits `flink/streaming_job.py` to the running Flink cluster. The job:
1. Reads JSON anomaly messages from the `eurostat.anomalies` topic
2. Enriches each message with a `processed_at` timestamp
3. Writes records to BigQuery `eurostat_raw.anomaly_stream_summaries` via the Streaming Insert API

Monitor the job at http://localhost:8081 (Flink Web UI).

> The Flink job is **optional** — the main dashboard does not depend on it. It provides real-time streaming analytics as an additional data flow.

---

## Tear-down

Stop all containers:

```bash
make down
```

Destroy GCP infrastructure (incurs no further costs after this):

```bash
make terraform-destroy
```

> `terraform destroy` will delete the GCS bucket, BigQuery datasets, and service account. All ingested data will be lost. Confirm with `yes` when prompted.

---

## Windows — one-click batch scripts

If you are on Windows and do not have `make` installed, two `.bat` scripts cover the full workflow as a double-click alternative.

### `run_pipeline.bat` — full pipeline runner

Double-click (or run from a Command Prompt in the project root):

```cmd
run_pipeline.bat
```

What it does, in order:

| Step | Action |
|---|---|
| Pre-flight | Verifies Docker, Docker Compose v2, `.env`, `credentials/service-account.json`, `terraform.tfvars` |
| 1/7 | `terraform init` + `terraform apply` — provisions GCP (skipped automatically if Terraform is not installed) |
| 2/7 | `docker compose build` — builds all project images |
| 3/7 | `docker compose up -d` — starts Redpanda, Flink cluster, anomaly consumer, dashboard |
| 4/7 | Creates the two Redpanda Kafka topics |
| 5/7 | Runs the dlt ingestion container (Eurostat → BigQuery raw) |
| 6/7 | Runs the Spark batch container (raw → processed) |
| 7/7 | Runs the dbt container (staging → intermediate → marts) |
| Done | Opens `http://localhost:8501` in your default browser |

Each step exits with an error message if it fails — no silent failures.

### `clean_project.bat` — teardown and cleanup

```cmd
clean_project.bat
```

Interactive menu with three levels:

| Level | What is removed |
|---|---|
| **1 — Soft clean** | Stops containers, removes volumes and orphaned networks. Docker images and GCP resources are kept. |
| **2 — Hard clean** | Everything in soft clean, plus all project Docker images and the Docker build cache are deleted. Next `run_pipeline.bat` will rebuild from scratch. |
| **3 — Full reset** | Everything in hard clean, plus `terraform destroy` — **deletes all BigQuery datasets and GCS bucket**. Requires `YES` confirmation. |

> **Tip:** After a soft clean you can immediately re-run `run_pipeline.bat` without rebuilding images. After a hard clean, images are rebuilt automatically on the next run.

---

## Repository structure

```
final_project/
├── .env.example                  # Environment variable template — copy to .env
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
├── credentials/                  # !! gitignored — place service-account.json here
│   └── service-account.json      # Bootstrap SA key (downloaded in Step 4c)
│
├── ingestion/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── eurostat_pipeline.py      # dlt pipeline — fetches 4 Eurostat datasets → BQ raw
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
│   ├── dbt_project.yml           # Project config — model paths, materialisation
│   ├── profiles.yml              # BigQuery connection profile
│   ├── packages.yml              # dbt-utils dependency
│   └── models/
│       ├── sources.yml           # Declares eurostat_raw source tables
│       ├── staging/              # stg_* views — cast and clean raw tables
│       ├── intermediate/         # int_* tables — joins and window functions
│       └── marts/                # mart_* partitioned tables — analytics-ready
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

---

## Data sources

| Dataset | Eurostat code | Description |
|---|---|---|
| GDP | `nama_10_gdp` | GDP and main aggregates — annual, current prices |
| Unemployment | `une_rt_a` | Unemployment rate by sex and age — annual |
| Energy Intensity | `nrg_ind_ei` | Energy intensity of the economy (kgoe per 1000 EUR GDP) |
| Inflation (HICP) | `prc_hicp_aind` | Harmonised Index of Consumer Prices — annual |

**Countries (18):** AT, BE, CZ, DE, DK, EL, ES, FI, FR, HU, IE, IT, NL, PL, PT, RO, SE, SK  
**Time range:** 2000 – 2023

Data is fetched via the [Eurostat REST API](https://ec.europa.eu/eurostat/web/json-and-unicode-web-services/) (no API key required).

---

## BigQuery schema

### `eurostat_raw` dataset — raw ingestion layer

All raw tables are:
- Partitioned by `loaded_at DATE` (ingestion date)
- Clustered by `[country_code, year]`

| Table | Key columns |
|---|---|
| `gdp_annual` | `country_code`, `year`, `gdp_value`, `unit`, `loaded_at` |
| `unemployment_annual` | `country_code`, `year`, `unemployment_rate`, `sex`, `age`, `loaded_at` |
| `energy_intensity` | `country_code`, `year`, `energy_intensity_value`, `unit`, `loaded_at` |
| `inflation_annual` | `country_code`, `year`, `hicp_value`, `unit`, `loaded_at` |
| `anomaly_stream_summaries` | `country_code`, `dataset`, `anomaly_score`, `processed_at` |

### `eurostat_processed` dataset — dbt marts

| Table | Partition | Cluster | Description |
|---|---|---|---|
| `mart_gdp_trends` | `reference_date` (year) | `country_code` | GDP values + YoY growth % |
| `mart_unemployment_comparison` | `reference_date` (year) | `country_code` | Unemployment rates + EU average |
| `mart_energy_intensity` | `reference_date` (year) | `country_code` | Energy intensity + YoY delta |
| `mart_composite_economic_index` | `reference_date` (year) | `country_code` | Composite score (0–100) |
| `mart_country_latest` | — | `country_code` | Latest-year snapshot per country |

### dbt lineage

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

---

## Composite index methodology

The composite score (0–100) combines three normalised sub-scores, calculated **within each calendar year** across all 18 EU countries in scope:

$$\text{score}(x) = \frac{x - x_{\min}}{x_{\max} - x_{\min}} \times 100$$

| Sub-score | Source | Direction |
|---|---|---|
| GDP Growth Score | YoY GDP growth % | Higher = better |
| Unemployment Score | Unemployment rate | **Inverted** — lower rate = better |
| Energy Score | Energy intensity (kgoe/1k€) | **Inverted** — lower intensity = better |

$$\text{Composite} = \frac{\text{GDP Score} + \text{Unemp. Score} + \text{Energy Score}}{3}$$

A score of 100 means the country ranks best on all three metrics in that year relative to peers.

---

## Makefile reference

```bash
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

---

## Troubleshooting

### `make up` fails — port already in use

```
Error: bind: address already in use
```

Another process is using one of the ports (8080, 8081, 8501, 19092). Stop the conflicting process or change the host port in `docker-compose.yml`.

---

### Terraform error: `Permission denied` or `403`

Your bootstrap service account is missing a required IAM role. Re-run the role binding commands from Step 4b, then retry `make terraform-apply`.

---

### dlt ingestion fails with `404` or `No data`

The Eurostat API occasionally returns no data for certain country-year combinations. This is normal. The pipeline will still succeed and load whatever data is available.

---

### dbt fails: `Table not found: eurostat_raw.*`

The Spark batch job must complete successfully before dbt can run. Run `make spark-batch` first, or use `make pipeline` which enforces the correct order.

---

### BigQuery dataset location error

```
Not found: Dataset was not found in location EU
```

Ensure `GCP_PROJECT_ID` in `.env` and `project_id` in `terraform.tfvars` are identical and match your actual GCP project. Terraform creates datasets in `EU` location — do not change this.

---

### Dashboard shows no data

1. Confirm `GCP_PROJECT_ID` and `BQ_PROCESSED_DATASET` are set correctly in `.env`.
2. Confirm `credentials/service-account.json` exists and is valid.
3. Confirm `make pipeline` completed without errors — check `docker logs eurostat-dbt`.
4. To test without BigQuery, set `USE_MOCK_DATA=true` in `.env` and restart the dashboard:
   ```bash
   docker compose restart dashboard
   ```

---

### Flink job fails to start

Ensure `make up` has been running for at least 30 seconds so that `flink-taskmanager` is registered with `flink-jobmanager`. Check the Flink Web UI at http://localhost:8081 — you should see `1 TaskManager` registered before submitting the job.

---

### On Windows: `make` command not found

You have three options:

1. **Use the provided batch scripts** (no extra tools needed):
   - `run_pipeline.bat` — runs the full pipeline end-to-end
   - `clean_project.bat` — interactive teardown

2. Install `make` via Chocolatey:
   ```cmd
   choco install make
   ```

3. Run all `make` commands from **Git Bash** or **WSL** where `make` is natively available.

---

## License

MIT
