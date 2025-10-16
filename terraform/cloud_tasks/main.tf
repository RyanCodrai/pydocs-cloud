# Cloud Tasks Queue for Package Releases (all ecosystems)
resource "google_cloud_tasks_queue" "package_releases" {
  name     = "package-releases"
  location = var.region

  rate_limits {
    max_dispatches_per_second = 500
    max_concurrent_dispatches = 1000
  }

  retry_config {
    max_attempts       = 100
    max_retry_duration = "4s"
    max_backoff        = "3s"
    min_backoff        = "0.1s"
    max_doublings      = 3
  }

  stackdriver_logging_config {
    sampling_ratio = 1.0
  }
}
