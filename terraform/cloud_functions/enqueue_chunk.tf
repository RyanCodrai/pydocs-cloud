# Enqueue Chunk Function
# Creates Cloud Tasks for each split file uploaded to releases-split/

# Archive the Cloud Function source code
data "archive_file" "enqueue_chunk_source" {
  type        = "zip"
  source_dir  = "${path.module}/../../functions/enqueue-chunk"
  output_path = "${path.module}/../../.terraform/tmp/enqueue_chunk_function.zip"
  excludes    = ["Makefile", "__pycache__", "*.pyc"]
}

# Upload the source code to GCS
resource "google_storage_bucket_object" "enqueue_chunk_source" {
  name   = "enqueue_chunk_function_${data.archive_file.enqueue_chunk_source.output_md5}.zip"
  bucket = google_storage_bucket.function_source.name
  source = data.archive_file.enqueue_chunk_source.output_path
}

# Cloud Function (Gen 2) for enqueueing chunks
resource "google_cloudfunctions2_function" "enqueue_chunk" {
  name     = "enqueue-chunk"
  location = var.region

  build_config {
    runtime     = "python312"
    entry_point = "enqueue_chunk"
    source {
      storage_source {
        bucket = google_storage_bucket.function_source.name
        object = google_storage_bucket_object.enqueue_chunk_source.name
      }
    }
  }

  service_config {
    max_instance_count    = 750
    available_memory      = "512Mi"
    timeout_seconds       = 600
    service_account_email = google_service_account.enqueue_chunk_sa.email

    environment_variables = {
      QUEUE_PATH         = var.cloud_tasks_queue_path
      PYPI_PROCESSOR_URL = var.pypi_processor_url
    }
  }

  event_trigger {
    trigger_region        = var.region
    event_type            = "google.cloud.storage.object.v1.finalized"
    retry_policy          = "RETRY_POLICY_RETRY"
    service_account_email = google_service_account.enqueue_chunk_sa.email

    event_filters {
      attribute = "bucket"
      value     = var.data_bucket_name
    }
  }

  labels = {
    purpose    = "enqueue-chunk"
    managed_by = "terraform"
  }

  depends_on = [
    google_project_iam_member.enqueue_chunk_eventarc_receiver,
    google_project_iam_member.enqueue_chunk_run_invoker,
    google_project_iam_member.enqueue_chunk_cloudtasks_enqueuer,
    google_storage_bucket_iam_member.enqueue_chunk_bucket_access,
    google_project_iam_member.cloudbuild_sa,
    google_project_iam_member.cloudbuild_artifact_registry,
    google_project_iam_member.gcs_pubsub_publishing
  ]
}

# Service account for the enqueue chunk function
resource "google_service_account" "enqueue_chunk_sa" {
  account_id   = "enqueue-chunk-sa"
  display_name = "Service Account for Enqueue Chunk Function"
}

# Grant the service account access to read and delete from the data bucket
resource "google_storage_bucket_iam_member" "enqueue_chunk_bucket_access" {
  bucket = var.data_bucket_name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.enqueue_chunk_sa.email}"
}

# Grant Eventarc event receiver role
resource "google_project_iam_member" "enqueue_chunk_eventarc_receiver" {
  project = var.project_id
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${google_service_account.enqueue_chunk_sa.email}"
}

# Grant Cloud Run invoker role
resource "google_project_iam_member" "enqueue_chunk_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.enqueue_chunk_sa.email}"
}

# Grant Cloud Tasks enqueuer role
resource "google_project_iam_member" "enqueue_chunk_cloudtasks_enqueuer" {
  project = var.project_id
  role    = "roles/cloudtasks.enqueuer"
  member  = "serviceAccount:${google_service_account.enqueue_chunk_sa.email}"
}
