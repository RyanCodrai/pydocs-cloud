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
  value       = "https://console.cloud.google.com/storage/browser/${google_storage_bucket.pydocs_datalake.name}?project=${var.project_id}"
}

output "bronze_path" {
  description = "Path to bronze zone"
  value       = "gs://${google_storage_bucket.pydocs_datalake.name}/bronze/"
}

output "silver_path" {
  description = "Path to silver zone"
  value       = "gs://${google_storage_bucket.pydocs_datalake.name}/silver/"
}

output "gold_path" {
  description = "Path to gold zone"
  value       = "gs://${google_storage_bucket.pydocs_datalake.name}/gold/"
}
