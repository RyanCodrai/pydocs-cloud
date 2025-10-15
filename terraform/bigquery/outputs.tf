output "dataset_id" {
  description = "The ID of the BigQuery dataset"
  value       = google_bigquery_dataset.exports_dataset.dataset_id
}

output "dataset_location" {
  description = "The location of the BigQuery dataset"
  value       = google_bigquery_dataset.exports_dataset.location
}

output "exports_table_id" {
  description = "The full table ID (project.dataset.table)"
  value       = "${var.project_id}.${google_bigquery_dataset.exports_dataset.dataset_id}.${google_bigquery_table.exports.table_id}"
}

output "exports_table_url" {
  description = "URL to view the table in BigQuery console"
  value       = "https://console.cloud.google.com/bigquery?project=${var.project_id}&p=${var.project_id}&d=${google_bigquery_dataset.exports_dataset.dataset_id}&t=${google_bigquery_table.exports.table_id}&page=table"
}
