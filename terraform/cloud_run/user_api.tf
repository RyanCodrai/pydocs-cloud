# PyDocs User API - Cloud Run Service
# Public-facing service for user auth, API keys, and external API access (api.sourced.dev)

# Service account for user API
resource "google_service_account" "user_api" {
  account_id   = "pydocs-user-api"
  display_name = "Service Account for PyDocs User API"
}

# Grant Secret Manager access to user API service account
resource "google_secret_manager_secret_iam_member" "user_api_secrets" {
  for_each = toset([
    "logging-level",
    "app-environment",
    "postgres-db",
    "postgres-user",
    "postgres-password",
    "postgres-host",
    "postgres-port",
    "github-app-client-id",
    "github-app-client-secret",
  ])

  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.user_api.email}"
}

# Grant Vertex AI User role for embeddings (lookup)
resource "google_project_iam_member" "user_api_vertex_ai" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.user_api.email}"
}

# Grant Storage Object Admin role for GCS bucket access (lookup caching)
resource "google_storage_bucket_iam_member" "user_api_bucket_access" {
  bucket = var.data_bucket_name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.user_api.email}"
}

# Grant Cloud SQL Client role for database access
resource "google_project_iam_member" "user_api_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.user_api.email}"
}

# Cloud Run service for user API
resource "google_cloud_run_v2_service" "user_api" {
  name                 = "pydocs-user-api"
  location             = var.region
  ingress              = "INGRESS_TRAFFIC_ALL"  # Public-facing, sits behind global load balancer
  invoker_iam_disabled = true

  template {
    service_account = google_service_account.user_api.email
    timeout         = "300s"

    scaling {
      min_instance_count = 1
      max_instance_count = 10
    }

    # VPC connector for Cloud SQL access
    vpc_access {
      network_interfaces {
        network    = data.google_compute_network.default.id
        subnetwork = data.google_compute_subnetwork.default.id
      }
      egress = "PRIVATE_RANGES_ONLY"
    }

    containers {
      image = var.docker_image

      ports {
        container_port = 8080
      }

      # Service type determines which routes are loaded
      env {
        name  = "SERVICE_TYPE"
        value = "user"
      }

      # Environment configuration
      env {
        name = "LOGGING_LEVEL"
        value_source {
          secret_key_ref {
            secret  = "logging-level"
            version = "latest"
          }
        }
      }

      env {
        name = "ENVIRONMENT"
        value_source {
          secret_key_ref {
            secret  = "app-environment"
            version = "latest"
          }
        }
      }

      # Database configuration
      env {
        name = "POSTGRES_DB"
        value_source {
          secret_key_ref {
            secret  = "postgres-db"
            version = "latest"
          }
        }
      }

      env {
        name = "POSTGRES_USER"
        value_source {
          secret_key_ref {
            secret  = "postgres-user"
            version = "latest"
          }
        }
      }

      env {
        name = "POSTGRES_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = "postgres-password"
            version = "latest"
          }
        }
      }

      env {
        name = "POSTGRES_HOST"
        value_source {
          secret_key_ref {
            secret  = "postgres-host"
            version = "latest"
          }
        }
      }

      env {
        name = "POSTGRES_PORT"
        value_source {
          secret_key_ref {
            secret  = "postgres-port"
            version = "latest"
          }
        }
      }

      # GitHub App OAuth
      env {
        name = "GITHUB_APP_CLIENT_ID"
        value_source {
          secret_key_ref {
            secret  = "github-app-client-id"
            version = "latest"
          }
        }
      }

      env {
        name = "GITHUB_APP_CLIENT_SECRET"
        value_source {
          secret_key_ref {
            secret  = "github-app-client-secret"
            version = "latest"
          }
        }
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle = true  # Request-based billing: CPU only allocated during request processing
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 30
        timeout_seconds       = 1
        period_seconds        = 10
        failure_threshold     = 3
      }
    }

    max_instance_request_concurrency = 80
  }

  labels = {
    service_type = "user"
    managed_by   = "terraform"
    environment  = var.environment
  }

  depends_on = [
    google_secret_manager_secret_iam_member.user_api_secrets,
    google_project_iam_member.user_api_cloudsql,
  ]
}
