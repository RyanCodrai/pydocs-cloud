# PyDocs Embed Service - Cloud Run Service
# Provides text embedding generation using Qwen 0.6B INT8 model

# Service account for embed service
resource "google_service_account" "embed_service" {
  account_id   = "pydocs-embed-service"
  display_name = "Service Account for PyDocs Embed Service"
}

# Cloud Run service for embed API
resource "google_cloud_run_v2_service" "embed_service" {
  name     = "pydocs-embed-service"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"  # Public access for embedding requests

  # NOTE: After deployment, manually click "Allow public access" in the Cloud Run console
  # to disable the IAM invoker check. This is required due to organization policy restrictions
  # that prevent setting this via Terraform.

  template {
    service_account = google_service_account.embed_service.email
    timeout         = "300s"  # 5 minute timeout for large batch processing

    # Disable IAM invoker check to allow unauthenticated access
    annotations = {
      "run.googleapis.com/invoker-iam-disabled" = "true"
    }

    # Execution environment Gen2 for improved performance
    execution_environment = "EXECUTION_ENVIRONMENT_GEN2"

    # Scale from 0 to 256 instances to handle varying load
    scaling {
      min_instance_count = 0
      max_instance_count = 256
    }

    containers {
      image = var.embed_docker_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "8Gi"
        }
        cpu_idle = true  # Request-based billing: CPU only allocated during request processing
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 60  # Model loading takes time
        timeout_seconds       = 3
        period_seconds        = 10
        failure_threshold     = 3
      }
    }

    # Process one request at a time (CPU-bound inference)
    max_instance_request_concurrency = 1
  }

  labels = {
    service_type = "embed"
    managed_by   = "terraform"
    environment  = var.environment
  }
}
