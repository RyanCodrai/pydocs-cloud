# npm Sync Function
# Walks the npm registry _changes feed to discover new/updated packages,
# fetches packuments, and writes release CSVs to GCS.
# Triggered by Cloud Scheduler on a cron schedule.

# Archive the Cloud Function source code
data "archive_file" "npm_sync_source" {
  type        = "zip"
  source_dir  = "${path.module}/../../functions/npm-sync"
  output_path = "${path.module}/../../.terraform/tmp/npm_sync_function.zip"
  excludes    = ["Makefile", "__pycache__", "*.pyc"]
}

# Upload the source code to GCS
resource "google_storage_bucket_object" "npm_sync_source" {
  name   = "npm_sync_function_${data.archive_file.npm_sync_source.output_md5}.zip"
  bucket = google_storage_bucket.function_source.name
  source = data.archive_file.npm_sync_source.output_path
}

# Cloud Function (Gen 2) for npm registry sync
resource "google_cloudfunctions2_function" "npm_sync" {
  name     = "npm-sync"
  location = var.region

  build_config {
    runtime     = "python312"
    entry_point = "npm_sync"
    source {
      storage_source {
        bucket = google_storage_bucket.function_source.name
        object = google_storage_bucket_object.npm_sync_source.name
      }
    }
  }

  service_config {
    max_instance_count    = 1 # Only one instance should run at a time
    available_memory      = "1Gi"
    available_cpu         = "1"
    timeout_seconds       = 540
    service_account_email = google_service_account.npm_sync_sa.email

    environment_variables = {
      DATA_BUCKET          = var.data_bucket_name
      STATE_PREFIX         = "npm-sync-state"
      CHANGES_BATCH_SIZE   = "500"
      MAX_PACKAGES_PER_RUN = "200"
      PACKUMENT_WORKERS    = "10"
    }
  }

  labels = {
    purpose    = "npm-sync"
    managed_by = "terraform"
  }

  depends_on = [
    google_project_iam_member.npm_sync_run_invoker,
    google_storage_bucket_iam_member.npm_sync_bucket_access,
    google_project_iam_member.cloudbuild_sa,
    google_project_iam_member.cloudbuild_artifact_registry,
  ]
}

# Service account for the npm sync function
resource "google_service_account" "npm_sync_sa" {
  account_id   = "npm-sync-sa"
  display_name = "Service Account for npm Sync Function"
}

# Grant the service account access to read/write to the data bucket
resource "google_storage_bucket_iam_member" "npm_sync_bucket_access" {
  bucket = var.data_bucket_name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.npm_sync_sa.email}"
}

# Grant Cloud Run invoker role (required for Gen 2 functions)
resource "google_project_iam_member" "npm_sync_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.npm_sync_sa.email}"
}

# Cloud Scheduler job to trigger npm sync every 5 minutes
resource "google_cloud_scheduler_job" "npm_sync_trigger" {
  name             = "npm-sync-trigger"
  description      = "Triggers npm registry sync every 5 minutes"
  schedule         = "*/5 * * * *"
  time_zone        = "UTC"
  attempt_deadline = "600s"
  region           = var.region

  http_target {
    http_method = "POST"
    uri         = google_cloudfunctions2_function.npm_sync.service_config[0].uri

    oidc_token {
      service_account_email = google_service_account.npm_sync_scheduler_sa.email
    }
  }
}

# Separate service account for Cloud Scheduler to invoke the function
resource "google_service_account" "npm_sync_scheduler_sa" {
  account_id   = "npm-sync-scheduler-sa"
  display_name = "Service Account for npm Sync Scheduler"
}

# Allow the scheduler service account to invoke the npm sync function
resource "google_cloud_run_service_iam_member" "npm_sync_scheduler_invoker" {
  location = google_cloudfunctions2_function.npm_sync.location
  service  = google_cloudfunctions2_function.npm_sync.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.npm_sync_scheduler_sa.email}"
}
