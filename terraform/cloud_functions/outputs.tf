output "function_name" {
  description = "Name of the deployed Cloud Function"
  value       = google_cloudfunctions2_function.split_csv.name
}

output "function_url" {
  description = "URL of the Cloud Function"
  value       = google_cloudfunctions2_function.split_csv.service_config[0].uri
}

output "function_region" {
  description = "Region where the function is deployed"
  value       = google_cloudfunctions2_function.split_csv.location
}

output "service_account_email" {
  description = "Service account email for the function"
  value       = google_service_account.function_sa.email
}
