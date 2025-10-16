output "function_name" {
  description = "Name of the deployed Cloud Function"
  value       = google_cloudfunctions2_function.split_and_enqueue.name
}

output "function_url" {
  description = "URL of the Cloud Function"
  value       = google_cloudfunctions2_function.split_and_enqueue.service_config[0].uri
}

output "function_region" {
  description = "Region where the function is deployed"
  value       = google_cloudfunctions2_function.split_and_enqueue.location
}

output "split_and_enqueue_service_account_email" {
  description = "Service account email for the split and enqueue function"
  value       = google_service_account.split_and_enqueue_sa.email
}
