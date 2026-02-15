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
    "auth0-domain",
    "auth0-issuer",
    "auth0-client-id",
    "auth0-algorithms",
    "github-token",
  ])

  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.user_api.email}"
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

    # Scale from 0 to 10 instances (user traffic is lighter)
    scaling {
      min_instance_count = 0
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

      # Auth0 configuration
      env {
        name = "AUTH0_DOMAIN"
        value_source {
          secret_key_ref {
            secret  = "auth0-domain"
            version = "latest"
          }
        }
      }

      env {
        name = "AUTH0_ISSUER"
        value_source {
          secret_key_ref {
            secret  = "auth0-issuer"
            version = "latest"
          }
        }
      }

      env {
        name = "AUTH0_CLIENT_ID"
        value_source {
          secret_key_ref {
            secret  = "auth0-client-id"
            version = "latest"
          }
        }
      }

      env {
        name = "AUTH0_ALGORITHMS"
        value_source {
          secret_key_ref {
            secret  = "auth0-algorithms"
            version = "latest"
          }
        }
      }

      # External API keys
      env {
        name = "GITHUB_TOKEN"
        value_source {
          secret_key_ref {
            secret  = "github-token"
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
