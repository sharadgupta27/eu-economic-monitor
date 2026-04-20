output "service_account_email" {
  description = "Pipeline service account email"
  value       = google_service_account.pipeline_sa.email
}

output "gcs_bucket_name" {
  description = "GCS data lake bucket name"
  value       = google_storage_bucket.data_lake.name
}

output "bq_raw_dataset" {
  description = "BigQuery raw dataset ID"
  value       = google_bigquery_dataset.raw.dataset_id
}

output "bq_processed_dataset" {
  description = "BigQuery processed dataset ID"
  value       = google_bigquery_dataset.processed.dataset_id
}

output "redpanda_external_ip" {
  description = "External IP of the GCE Redpanda broker"
  value       = google_compute_instance.redpanda_broker.network_interface[0].access_config[0].nat_ip
}

output "dataproc_cluster_name" {
  description = "Dataproc Spark cluster name"
  value       = google_dataproc_cluster.spark_cluster.name
}

output "credentials_file_path" {
  description = "Path to the generated service account key"
  value       = local_file.sa_key_file.filename
  sensitive   = true
}
