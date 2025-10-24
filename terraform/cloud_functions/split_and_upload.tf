# Split and Upload Function
# Splits CSV files into smaller files and uploads them to releases-split/

# Archive the Cloud Function source code
data "archive_file" "split_and_upload_source" {
  type        = "zip"
  source_dir  = "${path.module}/../../functions/split-and-upload"
  output_path = "${path.module}/../../.terraform/tmp/split_and_upload_function.zip"
  excludes    = ["Makefile", "__pycache__", "*.pyc"]
}

# Upload the source code to GCS
resource "google_storage_bucket_object" "split_and_upload_source" {
  name   = "split_and_upload_function_${data.archive_file.split_and_upload_source.output_md5}.zip"
  bucket = google_storage_bucket.function_source.name
  source = data.archive_file.split_and_upload_source.output_path
}

# Cloud Function (Gen 2) for splitting and uploading
resource "google_cloudfunctions2_function" "split_and_upload" {
  name     = "split-and-upload"
  location = var.region

  build_config {
    runtime     = "python312"
    entry_point = "split_and_upload"
    source {
      storage_source {
        bucket = google_storage_bucket.function_source.name
        object = google_storage_bucket_object.split_and_upload_source.name
      }
    }
  }

  service_config {
    max_instance_count    = 100
    available_memory      = "1Gi"
    available_cpu         = "1"
    timeout_seconds       = 600
    service_account_email = google_service_account.split_and_upload_sa.email
  }

  event_trigger {
    trigger_region        = var.region
    event_type            = "google.cloud.storage.object.v1.finalized"
    retry_policy          = "RETRY_POLICY_RETRY"
    service_account_email = google_service_account.split_and_upload_sa.email

    event_filters {
      attribute = "bucket"
      value     = var.data_bucket_name
    }
  }

  labels = {
    purpose    = "split-and-upload"
    managed_by = "terraform"
  }

  depends_on = [
    google_project_iam_member.split_and_upload_eventarc_receiver,
    google_project_iam_member.split_and_upload_run_invoker,
    google_storage_bucket_iam_member.split_and_upload_bucket_access,
    google_project_iam_member.cloudbuild_sa,
    google_project_iam_member.cloudbuild_artifact_registry,
    google_project_iam_member.gcs_pubsub_publishing
  ]
}

# Service account for the split and upload function
resource "google_service_account" "split_and_upload_sa" {
  account_id   = "split-and-upload-sa"
  display_name = "Service Account for Split and Upload Function"
}

# Grant the service account access to read/write to the data bucket
resource "google_storage_bucket_iam_member" "split_and_upload_bucket_access" {
  bucket = var.data_bucket_name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.split_and_upload_sa.email}"
}

# Grant Eventarc event receiver role
resource "google_project_iam_member" "split_and_upload_eventarc_receiver" {
  project = var.project_id
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${google_service_account.split_and_upload_sa.email}"
}

# Grant Cloud Run invoker role
resource "google_project_iam_member" "split_and_upload_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.split_and_upload_sa.email}"
}
