output "bucket_name" {
  description = "Name of the pydocs-datalake bucket"
  value       = google_storage_bucket.pydocs_datalake.name
}

output "bucket_url" {
  description = "GCS URL of the bucket"
  value       = "gs://${google_storage_bucket.pydocs_datalake.name}"
}

output "bucket_console_url" {
  description = "URL to view the bucket in GCP console"
  value       = "https://console.cloud.google.com/storage/browser/${google_storage_bucket.pydocs_datalake.name}"
}

output "exports_path" {
  description = "Path to exports zone (raw BigQuery exports)"
  value       = "gs://${google_storage_bucket.pydocs_datalake.name}/exports/"
}

output "pending_path" {
  description = "Path to pending zone (chunks waiting to be processed)"
  value       = "gs://${google_storage_bucket.pydocs_datalake.name}/pending/"
}
