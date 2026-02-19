# PyDocs MCP API - Cloud Run Service
# MCP server for coding agents (mcp.sourced.dev)

# Service account for MCP API
resource "google_service_account" "mcp_api" {
  account_id   = "pydocs-mcp-api"
  display_name = "Service Account for PyDocs MCP API"
}

# Grant Secret Manager access to MCP API service account
resource "google_secret_manager_secret_iam_member" "mcp_api_secrets" {
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
  member    = "serviceAccount:${google_service_account.mcp_api.email}"
}

# Grant Vertex AI User role for embeddings (lookup)
resource "google_project_iam_member" "mcp_api_vertex_ai" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.mcp_api.email}"
}

# Grant Storage Object Admin role for GCS bucket access (lookup caching)
resource "google_storage_bucket_iam_member" "mcp_api_bucket_access" {
  bucket = var.data_bucket_name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.mcp_api.email}"
}

# Grant Storage Object Admin role for repo cache bucket (write-through cache)
resource "google_storage_bucket_iam_member" "mcp_api_repo_cache_access" {
  bucket = var.repo_cache_bucket_name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.mcp_api.email}"
}

# Grant Cloud SQL Client role for database access
resource "google_project_iam_member" "mcp_api_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.mcp_api.email}"
}

# Cloud Run service for MCP API
resource "google_cloud_run_v2_service" "mcp_api" {
  name                 = "pydocs-mcp-api"
  location             = var.region
  ingress              = "INGRESS_TRAFFIC_ALL"
  invoker_iam_disabled = true

  template {
    service_account       = google_service_account.mcp_api.email
    execution_environment = "EXECUTION_ENVIRONMENT_GEN2"
    timeout               = "300s"

    scaling {
      min_instance_count = 1
      max_instance_count = 10
    }

    # VPC connector for Cloud SQL and NFS access
    vpc_access {
      network_interfaces {
        network    = data.google_compute_network.default.id
        subnetwork = data.google_compute_subnetwork.default.id
      }
      egress = "PRIVATE_RANGES_ONLY"
    }

    volumes {
      name = "nfs-cache"
      nfs {
        server    = var.nfs_cache_ip
        path      = "/mnt/nfs-cache"
        read_only = true
      }
    }

    containers {
      image = var.docker_image

      volume_mounts {
        name       = "nfs-cache"
        mount_path = "/mnt/nfs-cache"
      }

      ports {
        container_port = 8080
      }

      # Service type determines which app is loaded
      env {
        name  = "SERVICE_TYPE"
        value = "mcp"
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

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle = true
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
    service_type = "mcp"
    managed_by   = "terraform"
    environment  = var.environment
  }

  depends_on = [
    google_secret_manager_secret_iam_member.mcp_api_secrets,
    google_project_iam_member.mcp_api_cloudsql,
  ]
}

# --- Load Balancer for mcp.sourced.dev ---

# Static global IP address — point your A record here
resource "google_compute_global_address" "mcp_api" {
  name = "pydocs-mcp-api-ip"
}

# Serverless NEG pointing to the Cloud Run service
resource "google_compute_region_network_endpoint_group" "mcp_api" {
  name                  = "pydocs-mcp-api-neg"
  region                = var.region
  network_endpoint_type = "SERVERLESS"

  cloud_run {
    service = google_cloud_run_v2_service.mcp_api.name
  }
}

# Backend service wrapping the serverless NEG
resource "google_compute_backend_service" "mcp_api" {
  name                  = "pydocs-mcp-api-backend"
  load_balancing_scheme = "EXTERNAL"
  protocol              = "HTTPS"

  backend {
    group = google_compute_region_network_endpoint_group.mcp_api.id
  }

  log_config {
    enable = true
  }
}

# URL map — routes all traffic to the backend
resource "google_compute_url_map" "mcp_api" {
  name            = "pydocs-mcp-api-url-map"
  default_service = google_compute_backend_service.mcp_api.id
}

# Google-managed SSL certificate for mcp.sourced.dev
resource "google_compute_managed_ssl_certificate" "mcp_api" {
  name = "pydocs-mcp-api-cert"

  managed {
    domains = [var.mcp_api_domain]
  }
}

# HTTPS target proxy
resource "google_compute_target_https_proxy" "mcp_api" {
  name             = "pydocs-mcp-api-https-proxy"
  url_map          = google_compute_url_map.mcp_api.id
  ssl_certificates = [google_compute_managed_ssl_certificate.mcp_api.id]
}

# HTTPS forwarding rule (port 443)
resource "google_compute_global_forwarding_rule" "mcp_api_https" {
  name                  = "pydocs-mcp-api-https-rule"
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL"
  port_range            = "443"
  target                = google_compute_target_https_proxy.mcp_api.id
  ip_address            = google_compute_global_address.mcp_api.id
}

# --- HTTP → HTTPS redirect ---

resource "google_compute_url_map" "mcp_api_http_redirect" {
  name = "pydocs-mcp-api-http-redirect"

  default_url_redirect {
    https_redirect         = true
    strip_query            = false
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
  }
}

resource "google_compute_target_http_proxy" "mcp_api" {
  name    = "pydocs-mcp-api-http-proxy"
  url_map = google_compute_url_map.mcp_api_http_redirect.id
}

resource "google_compute_global_forwarding_rule" "mcp_api_http" {
  name                  = "pydocs-mcp-api-http-rule"
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL"
  port_range            = "80"
  target                = google_compute_target_http_proxy.mcp_api.id
  ip_address            = google_compute_global_address.mcp_api.id
}
