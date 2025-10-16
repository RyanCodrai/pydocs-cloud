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

# Get current project configuration from provider
data "google_client_config" "current" {
}

# Get project data to retrieve project number
data "google_project" "project" {
  project_id = data.google_client_config.current.project
}

# Grant Eventarc service agent the ability to manage events
resource "google_project_iam_member" "eventarc_service_agent" {
  project = data.google_client_config.current.project
  role    = "roles/eventarc.serviceAgent"
  member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-eventarc.iam.gserviceaccount.com"
}
