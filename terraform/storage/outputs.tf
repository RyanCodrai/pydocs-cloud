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

output "releases_path" {
  description = "Path to releases zone (raw package releases from all ecosystems)"
  value       = "gs://${google_storage_bucket.pydocs_datalake.name}/releases/"
}
