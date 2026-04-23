variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "europe-west1"
}

variable "zone" {
  description = "GCP Zone"
  type        = string
  default     = "europe-west1-b"
}

variable "credentials_file" {
  description = "Path to the GCP service account JSON key file"
  type        = string
  default     = "../credentials/service-account.json"
}

variable "gcs_bucket_name" {
  description = "Name of the GCS data lake bucket"
  type        = string
}

variable "bq_raw_dataset" {
  description = "BigQuery dataset for raw Eurostat data"
  type        = string
  default     = "eurostat_raw"
}

variable "bq_processed_dataset" {
  description = "BigQuery dataset for dbt-processed data"
  type        = string
  default     = "eurostat_processed"
}

variable "bq_location" {
  description = "BigQuery dataset location"
  type        = string
  default     = "EU"
}

variable "redpanda_machine_type" {
  description = "GCE machine type for Redpanda broker"
  type        = string
  default     = "e2-standard-2"
}

variable "terraform_executor_email" {
  description = "Email of the service account running Terraform (optional). Only needed if Terraform runs as a service account that needs to impersonate the pipeline SA. Format: 'your-sa@your-project.iam.gserviceaccount.com'"
  type        = string
  default     = null
}
