# Outputs for Cloud Run module

output "releases_api_url" {
  description = "URL of the releases API Cloud Run service"
  value       = google_cloud_run_v2_service.releases_api.uri
}

output "releases_api_service_account" {
  description = "Service account email for releases API"
  value       = google_service_account.releases_api.email
}


output "artifact_registry_url" {
  description = "URL for the Artifact Registry repository"
  value       = "${google_artifact_registry_repository.docker_images.location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker_images.repository_id}"
}
