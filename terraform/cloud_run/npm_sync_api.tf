# npm Sync Service - Cloud Run
# A continuously-running service that polls the npm registry _changes feed
# and upserts package/release data directly into the database.
# Deployed with SERVICE_TYPE=npm_sync — only exposes /health.

# Service account for npm sync API
resource "google_service_account" "npm_sync_api" {
  account_id   = "pydocs-npm-sync-api"
  display_name = "Service Account for PyDocs npm Sync API"
}

# Grant Secret Manager access to npm sync service account
resource "google_secret_manager_secret_iam_member" "npm_sync_api_secrets" {
  for_each = toset([
    "logging-level",
    "app-environment",
    "postgres-db",
    "postgres-user",
    "postgres-password",
    "postgres-host",
    "postgres-port",
  ])

  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.npm_sync_api.email}"
}

# Grant Cloud SQL Client role for database access
resource "google_project_iam_member" "npm_sync_api_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.npm_sync_api.email}"
}

# Cloud Run service for npm sync
resource "google_cloud_run_v2_service" "npm_sync_api" {
  name     = "pydocs-npm-sync-api"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    service_account = google_service_account.npm_sync_api.email
    timeout         = "300s"

    annotations = {
      "run.googleapis.com/invoker-iam-disabled" = "true"
    }

    # Always keep exactly 1 instance running
    scaling {
      min_instance_count = 1
      max_instance_count = 1
    }

    # VPC access with ALL_TRAFFIC egress — needs both VPC (for Cloud SQL)
    # and public internet (for npm registry APIs)
    vpc_access {
      network_interfaces {
        network    = data.google_compute_network.default.id
        subnetwork = data.google_compute_subnetwork.default.id
      }
      egress = "ALL_TRAFFIC"
    }

    containers {
      image = var.docker_image

      ports {
        container_port = 8080
      }

      # Service type: npm_sync — only loads /health, starts polling loop
      env {
        name  = "SERVICE_TYPE"
        value = "npm_sync"
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
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

      # npm sync tuning (override defaults via env vars)
      env {
        name  = "NPM_SYNC_POLL_INTERVAL"
        value = "30"
      }

      env {
        name  = "NPM_SYNC_CHANGES_BATCH_SIZE"
        value = "500"
      }

      env {
        name  = "NPM_SYNC_MAX_PACKAGES_PER_RUN"
        value = "200"
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
        # CPU always allocated — this service runs a background polling loop
        cpu_idle = false
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 10
        timeout_seconds       = 1
        period_seconds        = 5
        failure_threshold     = 6
      }

      liveness_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        period_seconds    = 30
        failure_threshold = 3
      }
    }

    max_instance_request_concurrency = 1
  }

  labels = {
    service_type = "npm-sync"
    managed_by   = "terraform"
    environment  = var.environment
  }

  depends_on = [
    google_secret_manager_secret_iam_member.npm_sync_api_secrets,
    google_project_iam_member.npm_sync_api_cloudsql,
  ]
}
