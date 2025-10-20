# Artifact Registry for Docker images

resource "google_artifact_registry_repository" "docker_images" {
  repository_id = "pydocs-images"
  location      = var.region
  format        = "DOCKER"
  description   = "Docker images for PyDocs API services"

  labels = {
    managed_by  = "terraform"
    environment = var.environment
  }
}

# Grant Cloud Build permission to push images
resource "google_artifact_registry_repository_iam_member" "cloudbuild_writer" {
  repository = google_artifact_registry_repository.docker_images.name
  location   = google_artifact_registry_repository.docker_images.location
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${data.google_project.project.number}@cloudbuild.gserviceaccount.com"
}

# Grant Cloud Run service accounts permission to pull images
resource "google_artifact_registry_repository_iam_member" "releases_api_reader" {
  repository = google_artifact_registry_repository.docker_images.name
  location   = google_artifact_registry_repository.docker_images.location
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.releases_api.email}"
}
