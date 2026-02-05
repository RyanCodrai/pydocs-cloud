output "enqueue_chunk_function_name" {
  description = "Name of the enqueue chunk Cloud Function"
  value       = google_cloudfunctions2_function.enqueue_chunk.name
}

output "enqueue_chunk_function_url" {
  description = "URL of the enqueue chunk Cloud Function"
  value       = google_cloudfunctions2_function.enqueue_chunk.service_config[0].uri
}

output "enqueue_chunk_function_region" {
  description = "Region where the enqueue chunk function is deployed"
  value       = google_cloudfunctions2_function.enqueue_chunk.location
}

output "split_and_upload_function_name" {
  description = "Name of the split and upload Cloud Function"
  value       = google_cloudfunctions2_function.split_and_upload.name
}

output "split_and_upload_function_url" {
  description = "URL of the split and upload Cloud Function"
  value       = google_cloudfunctions2_function.split_and_upload.service_config[0].uri
}

output "split_and_upload_function_region" {
  description = "Region where the split and upload function is deployed"
  value       = google_cloudfunctions2_function.split_and_upload.location
}

output "enqueue_chunk_service_account_email" {
  description = "Service account email for the enqueue chunk function"
  value       = google_service_account.enqueue_chunk_sa.email
}

output "split_and_upload_service_account_email" {
  description = "Service account email for the split and upload function"
  value       = google_service_account.split_and_upload_sa.email
}

output "npm_sync_function_name" {
  description = "Name of the npm sync Cloud Function"
  value       = google_cloudfunctions2_function.npm_sync.name
}

output "npm_sync_function_url" {
  description = "URL of the npm sync Cloud Function"
  value       = google_cloudfunctions2_function.npm_sync.service_config[0].uri
}

output "npm_sync_service_account_email" {
  description = "Service account email for the npm sync function"
  value       = google_service_account.npm_sync_sa.email
}