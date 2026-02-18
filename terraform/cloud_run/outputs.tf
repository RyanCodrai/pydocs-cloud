# Outputs for Cloud Run module

output "releases_api_url" {
  description = "URL of the releases API Cloud Run service"
  value       = google_cloud_run_v2_service.releases_api.uri
}

output "releases_api_service_account" {
  description = "Service account email for releases API"
  value       = google_service_account.releases_api.email
}


output "npm_sync_api_url" {
  description = "URL of the npm sync API Cloud Run service"
  value       = google_cloud_run_v2_service.npm_sync_api.uri
}

output "npm_sync_api_service_account" {
  description = "Service account email for npm sync API"
  value       = google_service_account.npm_sync_api.email
}

output "user_api_url" {
  description = "URL of the user API Cloud Run service"
  value       = google_cloud_run_v2_service.user_api.uri
}

output "user_api_service_account" {
  description = "Service account email for user API"
  value       = google_service_account.user_api.email
}

output "user_api_ip_address" {
  description = "Static IP address for the user API load balancer — point your A record here"
  value       = google_compute_global_address.user_api.address
}

output "mcp_api_url" {
  description = "URL of the MCP API Cloud Run service"
  value       = google_cloud_run_v2_service.mcp_api.uri
}

output "mcp_api_service_account" {
  description = "Service account email for MCP API"
  value       = google_service_account.mcp_api.email
}

output "mcp_api_ip_address" {
  description = "Static IP address for the MCP API load balancer — point your A record here"
  value       = google_compute_global_address.mcp_api.address
}

output "artifact_registry_url" {
  description = "URL for the Artifact Registry repository"
  value       = "${google_artifact_registry_repository.docker_images.location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker_images.repository_id}"
}

output "landing_ip_address" {
  description = "Static IP address for the landing page load balancer — point your A record here"
  value       = google_compute_global_address.landing.address
}
