terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Cloud Tasks Queue for Release Updates
resource "google_cloud_tasks_queue" "release_updates" {
  name     = "release-updates"
  location = var.region

  rate_limits {
    max_dispatches_per_second = 500
    max_concurrent_dispatches = 1000
  }

  retry_config {
    max_attempts       = 5
    max_retry_duration = "4s"
    max_backoff        = "3s"
    min_backoff        = "0.1s"
    max_doublings      = 3
  }

  stackdriver_logging_config {
    sampling_ratio = 1.0
  }
}
