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

# Grant Cloud Build permission to access Cloud Storage (for build staging)
resource "google_project_iam_member" "cloudbuild_storage_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${data.google_project.project.number}@cloudbuild.gserviceaccount.com"
}

# Grant Cloud Build service account the Cloud Build Service Account role
resource "google_project_iam_member" "cloudbuild_service_account" {
  project = var.project_id
  role    = "roles/cloudbuild.builds.builder"
  member  = "serviceAccount:${data.google_project.project.number}@cloudbuild.gserviceaccount.com"
}

# Grant Compute service account storage access (for running builds from GCE instances)
resource "google_project_iam_member" "compute_storage_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${data.google_project.project.number}-compute@developer.gserviceaccount.com"
}

# Grant Compute service account logs writer permission
resource "google_project_iam_member" "compute_logs_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${data.google_project.project.number}-compute@developer.gserviceaccount.com"
}

# Grant Cloud Run service accounts permission to pull images
resource "google_artifact_registry_repository_iam_member" "releases_api_reader" {
  repository = google_artifact_registry_repository.docker_images.name
  location   = google_artifact_registry_repository.docker_images.location
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.releases_api.email}"
}

