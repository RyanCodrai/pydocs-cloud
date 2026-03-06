# Cloud Build trigger for automatic deployment on push to main
#
# PREREQUISITE: You must create a GitHub connection manually first:
#   1. Go to https://console.cloud.google.com/cloud-build/repositories
#   2. Click "Create Host Connection" and select GitHub
#   3. Authenticate and install the Cloud Build GitHub app
#   4. Name the connection "github"
#   5. Link the repository "RyanCodrai/pydocs-cloud"
#
# Then run `terraform apply` to create the trigger.

# Cloud Build v2 repository link (requires manual GitHub connection above)
resource "google_cloudbuildv2_repository" "sourced" {
  name              = "sourced"
  location          = var.region
  parent_connection = "projects/${var.project_id}/locations/${var.region}/connections/github"
  remote_uri        = "https://github.com/RyanCodrai/pydocs-cloud.git"
}

# Trigger: build and deploy API on push to main
resource "google_cloudbuild_trigger" "deploy_api" {
  name     = "deploy-api-on-push"
  location = var.region

  repository_event_config {
    repository = google_cloudbuildv2_repository.sourced.id
    push {
      branch = "^main$"
    }
  }

  included_files = ["api/**"]

  filename = "api/cloudbuild.yaml"
}

# Grant Cloud Build permission to deploy to Cloud Run
resource "google_project_iam_member" "cloudbuild_run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${data.google_project.project.number}@cloudbuild.gserviceaccount.com"
}

# Cloud Build needs to act as Cloud Run service accounts to deploy
resource "google_service_account_iam_member" "cloudbuild_act_as_mcp" {
  service_account_id = google_service_account.mcp_api.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${data.google_project.project.number}@cloudbuild.gserviceaccount.com"
}

resource "google_service_account_iam_member" "cloudbuild_act_as_user" {
  service_account_id = google_service_account.user_api.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${data.google_project.project.number}@cloudbuild.gserviceaccount.com"
}

resource "google_service_account_iam_member" "cloudbuild_act_as_releases" {
  service_account_id = google_service_account.releases_api.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${data.google_project.project.number}@cloudbuild.gserviceaccount.com"
}

resource "google_service_account_iam_member" "cloudbuild_act_as_npm_sync" {
  service_account_id = google_service_account.npm_sync_api.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${data.google_project.project.number}@cloudbuild.gserviceaccount.com"
}
