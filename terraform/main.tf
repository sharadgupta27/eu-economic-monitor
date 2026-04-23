# ============================================================
# EU Economic Monitor — Terraform Main Configuration
# Provisions: GCS, BigQuery (partitioned tables), Service
# Account, GCE instance for Redpanda, Dataproc for Spark.
# ============================================================

# -----------------------------------------------------------
# Service Account
# -----------------------------------------------------------
resource "google_service_account" "pipeline_sa" {
  account_id   = "eurostat-pipeline-sa"
  display_name = "Eurostat Pipeline Service Account"
  description  = "Used by dlt, Spark, and dbt to access GCS and BigQuery"
}

resource "google_project_iam_member" "sa_bigquery_admin" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.pipeline_sa.email}"
}

resource "google_project_iam_member" "sa_bigquery_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.pipeline_sa.email}"
}

resource "google_project_iam_member" "sa_gcs_admin" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.pipeline_sa.email}"
}

# Grant Dataproc Worker role for Dataproc cluster usage
resource "google_project_iam_member" "sa_dataproc_worker" {
  project = var.project_id
  role    = "roles/dataproc.worker"
  member  = "serviceAccount:${google_service_account.pipeline_sa.email}"
}

# Allow the Terraform executor to act as the pipeline service account (optional)
# Only needed if Terraform runs as a service account without Owner/Editor roles
resource "google_service_account_iam_member" "terraform_sa_user" {
  count = var.terraform_executor_email != null ? 1 : 0

  service_account_id = google_service_account.pipeline_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${var.terraform_executor_email}"
}

resource "google_service_account_key" "pipeline_sa_key" {
  service_account_id = google_service_account.pipeline_sa.name
  public_key_type    = "TYPE_X509_PEM_FILE"
}

resource "local_file" "sa_key_file" {
  content  = base64decode(google_service_account_key.pipeline_sa_key.private_key)
  filename = "../credentials/pipeline-sa-key.json"
}

# -----------------------------------------------------------
# GCS Data Lake Bucket
# -----------------------------------------------------------
resource "google_storage_bucket" "data_lake" {
  name          = var.gcs_bucket_name
  location      = var.bq_location
  force_destroy = false

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
    condition {
      age = 30
    }
  }

  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
    condition {
      age = 90
    }
  }

  uniform_bucket_level_access = true

  labels = {
    project     = "eurostat-monitor"
    environment = "production"
  }
}

# -----------------------------------------------------------
# BigQuery — Raw Dataset
# -----------------------------------------------------------
resource "google_bigquery_dataset" "raw" {
  dataset_id    = var.bq_raw_dataset
  friendly_name = "Eurostat Raw Data"
  description   = "Raw data ingested by dlt from the Eurostat API"
  location      = var.bq_location

  labels = {
    layer = "raw"
  }
}

# GDP — Partitioned by loaded_at (daily ingestion date)
resource "google_bigquery_table" "gdp_annual" {
  dataset_id          = google_bigquery_dataset.raw.dataset_id
  table_id            = "gdp_annual"
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "loaded_at"
  }

  clustering = ["country_code", "year"]

  schema = jsonencode([
    { name = "country_code", type = "STRING",  mode = "REQUIRED", description = "ISO 3166-1 alpha-2 country code (Eurostat)" },
    { name = "country_name", type = "STRING",  mode = "NULLABLE", description = "Full country name" },
    { name = "year",         type = "INTEGER", mode = "REQUIRED", description = "Reference year" },
    { name = "unit",         type = "STRING",  mode = "NULLABLE", description = "Unit of measurement (e.g. CP_MEUR)" },
    { name = "indicator",    type = "STRING",  mode = "NULLABLE", description = "National accounts indicator code" },
    { name = "value",        type = "FLOAT64", mode = "NULLABLE", description = "GDP value in millions EUR" },
    { name = "loaded_at",    type = "DATE",    mode = "REQUIRED", description = "Date the record was ingested" }
  ])
}

# Unemployment — Partitioned by loaded_at
resource "google_bigquery_table" "unemployment_annual" {
  dataset_id          = google_bigquery_dataset.raw.dataset_id
  table_id            = "unemployment_annual"
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "loaded_at"
  }

  clustering = ["country_code", "year"]

  schema = jsonencode([
    { name = "country_code", type = "STRING",  mode = "REQUIRED" },
    { name = "country_name", type = "STRING",  mode = "NULLABLE" },
    { name = "year",         type = "INTEGER", mode = "REQUIRED" },
    { name = "unit",         type = "STRING",  mode = "NULLABLE" },
    { name = "age_group",    type = "STRING",  mode = "NULLABLE", description = "TOTAL, Y15-24, Y25-74" },
    { name = "sex",          type = "STRING",  mode = "NULLABLE", description = "T (total), M, F" },
    { name = "value",        type = "FLOAT64", mode = "NULLABLE", description = "Unemployment rate (%)" },
    { name = "loaded_at",    type = "DATE",    mode = "REQUIRED" }
  ])
}

# Energy Intensity — Partitioned by loaded_at
resource "google_bigquery_table" "energy_intensity" {
  dataset_id          = google_bigquery_dataset.raw.dataset_id
  table_id            = "energy_intensity"
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "loaded_at"
  }

  clustering = ["country_code", "year"]

  schema = jsonencode([
    { name = "country_code", type = "STRING",  mode = "REQUIRED" },
    { name = "country_name", type = "STRING",  mode = "NULLABLE" },
    { name = "year",         type = "INTEGER", mode = "REQUIRED" },
    { name = "unit",         type = "STRING",  mode = "NULLABLE", description = "KGOE_TEUR = kg oil equivalent per 1000 EUR GDP" },
    { name = "value",        type = "FLOAT64", mode = "NULLABLE" },
    { name = "loaded_at",    type = "DATE",    mode = "REQUIRED" }
  ])
}

# Inflation — Partitioned by loaded_at
resource "google_bigquery_table" "inflation_annual" {
  dataset_id          = google_bigquery_dataset.raw.dataset_id
  table_id            = "inflation_annual"
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "loaded_at"
  }

  clustering = ["country_code", "year"]

  schema = jsonencode([
    { name = "country_code", type = "STRING",  mode = "REQUIRED" },
    { name = "country_name", type = "STRING",  mode = "NULLABLE" },
    { name = "year",         type = "INTEGER", mode = "REQUIRED" },
    { name = "unit",         type = "STRING",  mode = "NULLABLE" },
    { name = "value",        type = "FLOAT64", mode = "NULLABLE", description = "HICP inflation rate (%)" },
    { name = "loaded_at",    type = "DATE",    mode = "REQUIRED" }
  ])
}

# Anomaly Alerts — written by Spark Streaming consumer
resource "google_bigquery_table" "anomaly_alerts" {
  dataset_id          = google_bigquery_dataset.raw.dataset_id
  table_id            = "anomaly_alerts"
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "detected_at"
  }

  schema = jsonencode([
    { name = "dataset",       type = "STRING",    mode = "REQUIRED" },
    { name = "country_code",  type = "STRING",    mode = "REQUIRED" },
    { name = "year",          type = "INTEGER",   mode = "REQUIRED" },
    { name = "value",         type = "FLOAT64",   mode = "NULLABLE" },
    { name = "z_score",       type = "FLOAT64",   mode = "NULLABLE" },
    { name = "mean",          type = "FLOAT64",   mode = "NULLABLE" },
    { name = "std_dev",       type = "FLOAT64",   mode = "NULLABLE" },
    { name = "severity",      type = "STRING",    mode = "NULLABLE", description = "LOW, MEDIUM, HIGH" },
    { name = "detected_at",   type = "TIMESTAMP", mode = "REQUIRED" }
  ])
}

# -----------------------------------------------------------
# BigQuery — Processed Dataset (dbt output)
# -----------------------------------------------------------
resource "google_bigquery_dataset" "processed" {
  dataset_id    = var.bq_processed_dataset
  friendly_name = "Eurostat Processed Data"
  description   = "Analytics-ready tables produced by dbt"
  location      = var.bq_location

  labels = {
    layer = "processed"
  }
}

# -----------------------------------------------------------
# GCE Instance — Redpanda Broker (optional cloud deployment)
# Used when running Redpanda on GCP instead of local Docker
# -----------------------------------------------------------
resource "google_compute_instance" "redpanda_broker" {
  name         = "eurostat-redpanda-broker"
  machine_type = var.redpanda_machine_type
  zone         = var.zone

  tags = ["redpanda-broker"]

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
      size  = 50
      type  = "pd-ssd"
    }
  }

  network_interface {
    network = "default"
    access_config {}
  }

  metadata_startup_script = <<-SCRIPT
    #!/bin/bash
    curl -1sLf 'https://dl.redpanda.com/nzc4ZYQK3WRGd9sy/redpanda/cfg/setup/bash.deb.sh' | bash
    apt-get install -y redpanda
    rpk redpanda config set redpanda.developer_mode true
    systemctl enable redpanda
    systemctl start redpanda
    rpk topic create eurostat.ingestion.completed --partitions 3
    rpk topic create eurostat.anomalies --partitions 3
  SCRIPT

  service_account {
    email  = google_service_account.pipeline_sa.email
    scopes = ["cloud-platform"]
  }

  labels = {
    project = "eurostat-monitor"
    role    = "streaming-broker"
  }
}

resource "google_compute_firewall" "redpanda_fw" {
  name    = "allow-redpanda-kafka"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["9092", "19092", "8081", "8082", "9644"]
  }

  target_tags   = ["redpanda-broker"]
  source_ranges = ["0.0.0.0/0"]
}

# -----------------------------------------------------------
# Wait for IAM propagation before creating Dataproc cluster
# -----------------------------------------------------------
resource "time_sleep" "wait_for_iam" {
  depends_on = [
    google_project_iam_member.sa_dataproc_worker,
    google_project_iam_member.sa_bigquery_admin,
    google_project_iam_member.sa_gcs_admin
  ]

  create_duration = "60s"
}

# -----------------------------------------------------------
# Dataproc — Spark Cluster (for cloud Spark jobs)
# -----------------------------------------------------------
resource "google_dataproc_cluster" "spark_cluster" {
  name   = "eurostat-spark-cluster"
  region = var.region

  cluster_config {
    staging_bucket = google_storage_bucket.data_lake.name

    master_config {
      num_instances = 1
      machine_type  = "n2-standard-4"

      disk_config {
        boot_disk_type    = "pd-ssd"
        boot_disk_size_gb = 100
      }
    }

    worker_config {
      num_instances = 2
      machine_type  = "n2-standard-4"

      disk_config {
        boot_disk_type    = "pd-standard"
        boot_disk_size_gb = 100
      }
    }

    software_config {
      image_version = "2.1-debian11"

      optional_components = ["JUPYTER"]

      override_properties = {
        "dataproc:dataproc.allow.zero.workers" = "true"
      }
    }

    gce_cluster_config {
      service_account        = google_service_account.pipeline_sa.email
      service_account_scopes = ["cloud-platform"]
    }
  }

  labels = {
    project = "eurostat-monitor"
  }

  # Ensure IAM roles are propagated before creating cluster
  depends_on = [
    time_sleep.wait_for_iam
  ]
}
