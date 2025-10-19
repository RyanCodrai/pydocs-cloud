# Shared resources for all Cloud Functions

# Create a bucket to store Cloud Function source code
resource "google_storage_bucket" "function_source" {
  name                        = "pydocs-function-source"
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true

  labels = {
    purpose    = "cloud-function-source"
    managed_by = "terraform"
  }
}

# Note: Eventarc service agent is automatically created and granted permissions
# by Google when you first create an Eventarc trigger. No manual IAM binding needed.

# Get project number for Cloud Build service account
data "google_project" "project" {
  project_id = var.project_id
}

# Grant Cloud Build permissions to the default Compute Service Account
# Required for Cloud Functions Gen 2 in projects created after July 2024
resource "google_project_iam_member" "cloudbuild_sa" {
  project = var.project_id
  role    = "roles/cloudbuild.builds.builder"
  member  = "serviceAccount:${data.google_project.project.number}-compute@developer.gserviceaccount.com"
}

# Get GCS service account (this triggers its creation if it doesn't exist)
data "google_storage_project_service_account" "gcs_account" {
  project = var.project_id
}

# Grant Cloud Storage service account Pub/Sub Publisher role for Eventarc triggers
# Required for GCS CloudEvent triggers to publish to Pub/Sub
resource "google_project_iam_member" "gcs_pubsub_publishing" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${data.google_storage_project_service_account.gcs_account.email_address}"
}
