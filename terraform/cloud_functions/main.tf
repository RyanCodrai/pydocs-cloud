terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

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

# Archive the Cloud Function source code
data "archive_file" "split_csv_source" {
  type        = "zip"
  source_dir  = "${path.module}/../../cloud_run/pydocs-auto-split-csv"
  output_path = "${path.module}/../../.terraform/tmp/split_csv_function.zip"
  excludes    = ["Makefile", "__pycache__", "*.pyc"]
}

# Upload the source code to GCS
resource "google_storage_bucket_object" "split_csv_source" {
  name   = "split_csv_function_${data.archive_file.split_csv_source.output_md5}.zip"
  bucket = google_storage_bucket.function_source.name
  source = data.archive_file.split_csv_source.output_path
}

# Cloud Function (Gen 2) for CSV splitting
resource "google_cloudfunctions2_function" "split_csv" {
  name     = "pydocs-split-csv"
  location = var.region

  build_config {
    runtime     = "python312"
    entry_point = "split_csv_file"
    source {
      storage_source {
        bucket = google_storage_bucket.function_source.name
        object = google_storage_bucket_object.split_csv_source.name
      }
    }
  }

  service_config {
    max_instance_count = 10
    available_memory   = "512Mi"
    timeout_seconds    = 540
  }

  event_trigger {
    trigger_region        = var.region
    event_type            = "google.cloud.storage.object.v1.finalized"
    retry_policy          = "RETRY_POLICY_RETRY"
    service_account_email = google_service_account.function_sa.email

    event_filters {
      attribute = "bucket"
      value     = var.data_bucket_name
    }
  }

  labels = {
    purpose    = "csv-splitting"
    managed_by = "terraform"
  }
}

# Service account for the Cloud Function
resource "google_service_account" "function_sa" {
  account_id   = "pydocs-split-csv-sa"
  display_name = "Service Account for PyDocs CSV Splitting Function"
}

# Grant the service account access to read/write to the data bucket
resource "google_storage_bucket_iam_member" "function_bucket_access" {
  bucket = var.data_bucket_name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.function_sa.email}"
}

# Grant Eventarc event receiver role to the service account
resource "google_project_iam_member" "eventarc_receiver" {
  project = var.project_id
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${google_service_account.function_sa.email}"
}

# Grant Cloud Run invoker role to the service account (required for Gen 2 functions)
resource "google_project_iam_member" "run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.function_sa.email}"
}

# Get project data to retrieve project number
data "google_project" "project" {
  project_id = var.project_id
}

# Grant Eventarc service agent the ability to manage events
resource "google_project_iam_member" "eventarc_service_agent" {
  project = var.project_id
  role    = "roles/eventarc.serviceAgent"
  member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-eventarc.iam.gserviceaccount.com"
}
