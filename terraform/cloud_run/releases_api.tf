# PyDocs Releases API - Cloud Run Service
# This service processes package releases and MUST never miss an event

# Service account for releases API
resource "google_service_account" "releases_api" {
  account_id   = "pydocs-releases-api"
  display_name = "Service Account for PyDocs Releases API"
}

# Grant Secret Manager access to releases API service account
resource "google_secret_manager_secret_iam_member" "releases_api_secrets" {
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
  ])

  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.releases_api.email}"
}

# Grant Cloud SQL Client role for database access
resource "google_project_iam_member" "releases_api_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.releases_api.email}"
}

# Cloud Run service for releases API
resource "google_cloud_run_v2_service" "releases_api" {
  name     = "pydocs-releases-api"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"  # Only internal access (for Cloud Tasks)

  template {
    service_account = google_service_account.releases_api.email

    # Scale from 0 to 10 instances (cost-effective with request-based billing)
    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }

    # VPC connector for Cloud SQL access
    vpc_access {
      network_interfaces {
        network    = "default"
        subnetwork = "default"
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
        value = "releases"
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

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
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

    # Support 20 concurrent requests per instance
    max_instance_request_concurrency = 20
  }

  labels = {
    service_type = "releases"
    managed_by   = "terraform"
    environment  = var.environment
  }

  depends_on = [
    google_secret_manager_secret_iam_member.releases_api_secrets,
    google_project_iam_member.releases_api_cloudsql,
  ]
}

# Allow Cloud Tasks to invoke the releases API
resource "google_cloud_run_v2_service_iam_member" "releases_api_invoker" {
  name     = google_cloud_run_v2_service.releases_api.name
  location = google_cloud_run_v2_service.releases_api.location
  role     = "roles/run.invoker"
  member   = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-cloudtasks.iam.gserviceaccount.com"
}

# Get project number for Cloud Tasks service account
data "google_project" "project" {
  project_id = var.project_id
}
