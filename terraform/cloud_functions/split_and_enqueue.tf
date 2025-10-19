# Split and Enqueue Function
# Splits CSV files into chunks and enqueues them to Cloud Tasks for processing

# Archive the Cloud Function source code
data "archive_file" "split_and_enqueue_source" {
  type        = "zip"
  source_dir  = "${path.module}/../../functions/split-and-enqueue"
  output_path = "${path.module}/../../.terraform/tmp/split_and_enqueue_function.zip"
  excludes    = ["Makefile", "__pycache__", "*.pyc"]
}

# Upload the source code to GCS
resource "google_storage_bucket_object" "split_and_enqueue_source" {
  name   = "split_and_enqueue_function_${data.archive_file.split_and_enqueue_source.output_md5}.zip"
  bucket = google_storage_bucket.function_source.name
  source = data.archive_file.split_and_enqueue_source.output_path
}

# Cloud Function (Gen 2) for splitting and enqueueing
resource "google_cloudfunctions2_function" "split_and_enqueue" {
  name     = "split-and-enqueue"
  location = var.region

  build_config {
    runtime     = "python312"
    entry_point = "split_and_enqueue"
    source {
      storage_source {
        bucket = google_storage_bucket.function_source.name
        object = google_storage_bucket_object.split_and_enqueue_source.name
      }
    }
  }

  service_config {
    max_instance_count    = 10
    available_memory      = "512Mi"
    timeout_seconds       = 540
    service_account_email = google_service_account.split_and_enqueue_sa.email

    environment_variables = {
      QUEUE_PATH         = var.cloud_tasks_queue_path
      PYPI_PROCESSOR_URL = var.pypi_processor_url
    }
  }

  event_trigger {
    trigger_region        = var.region
    event_type            = "google.cloud.storage.object.v1.finalized"
    retry_policy          = "RETRY_POLICY_RETRY"
    service_account_email = google_service_account.split_and_enqueue_sa.email

    event_filters {
      attribute = "bucket"
      value     = var.data_bucket_name
    }
  }

  labels = {
    purpose    = "split-and-enqueue"
    managed_by = "terraform"
  }

  depends_on = [
    google_project_iam_member.split_and_enqueue_eventarc_receiver,
    google_project_iam_member.split_and_enqueue_run_invoker,
    google_project_iam_member.split_and_enqueue_cloudtasks_enqueuer,
    google_storage_bucket_iam_member.split_and_enqueue_bucket_access,
    google_project_iam_member.cloudbuild_sa,
    google_project_iam_member.gcs_pubsub_publishing
  ]
}

# Service account for the split and enqueue function
resource "google_service_account" "split_and_enqueue_sa" {
  account_id   = "split-and-enqueue-sa"
  display_name = "Service Account for Split and Enqueue Function"
}

# Grant the service account access to read from the data bucket
resource "google_storage_bucket_iam_member" "split_and_enqueue_bucket_access" {
  bucket = var.data_bucket_name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.split_and_enqueue_sa.email}"
}

# Grant Eventarc event receiver role to the service account
resource "google_project_iam_member" "split_and_enqueue_eventarc_receiver" {
  project = var.project_id
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${google_service_account.split_and_enqueue_sa.email}"
}

# Grant Cloud Run invoker role to the service account (required for Gen 2 functions)
resource "google_project_iam_member" "split_and_enqueue_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.split_and_enqueue_sa.email}"
}

# Grant Cloud Tasks enqueuer role to the service account
resource "google_project_iam_member" "split_and_enqueue_cloudtasks_enqueuer" {
  project = var.project_id
  role    = "roles/cloudtasks.enqueuer"
  member  = "serviceAccount:${google_service_account.split_and_enqueue_sa.email}"
}
