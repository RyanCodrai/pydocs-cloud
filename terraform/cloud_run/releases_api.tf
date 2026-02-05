# PyDocs Releases API - Cloud Run Service
# This service processes package releases and MUST never miss an event

# Reference the default VPC network
data "google_compute_network" "default" {
  name = "default"
}

# Get the subnet for the region
data "google_compute_subnetwork" "default" {
  name   = "default"
  region = var.region
}

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
    "github-token",
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

# Grant Vertex AI User role for embeddings
resource "google_project_iam_member" "releases_api_vertex_ai" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.releases_api.email}"
}

# Grant Storage Object Admin role for reading and deleting split files
resource "google_storage_bucket_iam_member" "releases_api_bucket_access" {
  bucket = var.data_bucket_name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.releases_api.email}"
}


# Cloud Run service for releases API
resource "google_cloud_run_v2_service" "releases_api" {
  name     = "pydocs-releases-api"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"  # Only internal access (for Cloud Tasks)

  # NOTE: After deployment, manually click "Allow public access" in the Cloud Run console
  # to disable the IAM invoker check. This is required due to organization policy restrictions
  # that prevent setting this via Terraform.

  template {
    service_account = google_service_account.releases_api.email
    timeout         = "300s"  # 5 minute timeout for processing batches

    # Disable IAM invoker check to allow unauthenticated access
    annotations = {
      "run.googleapis.com/invoker-iam-disabled" = "true"
    }

    # Scale from 0 to 100 instances (handles high throughput from Cloud Tasks)
    scaling {
      min_instance_count = 0
      max_instance_count = 100
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
        value = "releases"
      }

      # Vertex AI configuration for embeddings
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }

      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.region
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
          memory = "1Gi"
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

    max_instance_request_concurrency = 10
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



# Get project number for Cloud Tasks service account
data "google_project" "project" {
  project_id = var.project_id
}
