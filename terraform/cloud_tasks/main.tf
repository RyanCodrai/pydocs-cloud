# Cloud Tasks Queue for Package Releases (all ecosystems)
resource "google_cloud_tasks_queue" "package_releases" {
  name     = "package-releases"
  location = var.region

  rate_limits {
    max_dispatches_per_second = 150
    max_concurrent_dispatches = 100
  }

  retry_config {
    max_attempts       = 100
    max_retry_duration = "604800s"  # 1 week (7 days * 24 hours * 60 minutes * 60 seconds)
    max_backoff        = "3600s"     # 1 hour max backoff
    min_backoff        = "1s"
    max_doublings      = 5
  }

  stackdriver_logging_config {
    sampling_ratio = 1.0
  }
}

# Cloud Tasks Queue for GitHub URL Candidate Extraction
resource "google_cloud_tasks_queue" "package_candidate_extraction" {
  name     = "package-candidate-extraction"
  location = var.region

  rate_limits {
    max_dispatches_per_second = 150
    max_concurrent_dispatches = 100
  }

  retry_config {
    max_attempts       = 100
    max_retry_duration = "604800s"  # 1 week (7 days * 24 hours * 60 minutes * 60 seconds)
    max_backoff        = "3600s"     # 1 hour max backoff
    min_backoff        = "1s"
    max_doublings      = 5
  }

  stackdriver_logging_config {
    sampling_ratio = 1.0
  }
}
