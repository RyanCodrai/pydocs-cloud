# CSV Splitting Function
# Automatically splits large CSV files from bronze/ into 100-row chunks in silver/

# Archive the Cloud Function source code
data "archive_file" "split_csv_source" {
  type        = "zip"
  source_dir  = "${path.module}/../../functions/split-csv"
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
    max_instance_count    = 10
    available_memory      = "512Mi"
    timeout_seconds       = 540
    service_account_email = google_service_account.split_csv_sa.email
  }

  event_trigger {
    trigger_region        = var.region
    event_type            = "google.cloud.storage.object.v1.finalized"
    retry_policy          = "RETRY_POLICY_RETRY"
    service_account_email = google_service_account.split_csv_sa.email

    event_filters {
      attribute = "bucket"
      value     = var.data_bucket_name
    }
  }

  labels = {
    purpose    = "csv-splitting"
    managed_by = "terraform"
  }

  depends_on = [
    google_project_iam_member.split_csv_eventarc_receiver,
    google_project_iam_member.split_csv_run_invoker,
    google_storage_bucket_iam_member.split_csv_bucket_access
  ]
}

# Service account for the split CSV function
resource "google_service_account" "split_csv_sa" {
  account_id   = "pydocs-csv-splitter-sa"
  display_name = "Service Account for PyDocs CSV Splitting Function"
}

# Grant the service account access to read/write to the data bucket
resource "google_storage_bucket_iam_member" "split_csv_bucket_access" {
  bucket = var.data_bucket_name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.split_csv_sa.email}"
}

# Grant Eventarc event receiver role to the service account
resource "google_project_iam_member" "split_csv_eventarc_receiver" {
  project = data.google_client_config.current.project
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${google_service_account.split_csv_sa.email}"
}

# Grant Cloud Run invoker role to the service account (required for Gen 2 functions)
resource "google_project_iam_member" "split_csv_run_invoker" {
  project = data.google_client_config.current.project
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.split_csv_sa.email}"
}
