# sourced.dev Landing Page - Cloud Run Service + Global Load Balancer

# Cloud Run service for the landing page
resource "google_cloud_run_v2_service" "landing" {
  name                 = "sourced-landing"
  location             = var.region
  ingress              = "INGRESS_TRAFFIC_ALL"
  invoker_iam_disabled = true

  template {
    timeout = "30s"

    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }

    containers {
      image = var.landing_docker_image

      ports {
        container_port = 3000
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "256Mi"
        }
        cpu_idle = true
      }

      startup_probe {
        http_get {
          path = "/"
          port = 3000
        }
        initial_delay_seconds = 5
        timeout_seconds       = 1
        period_seconds        = 5
        failure_threshold     = 3
      }
    }

    max_instance_request_concurrency = 80
  }

  labels = {
    service_type = "landing"
    managed_by   = "terraform"
    environment  = var.environment
  }
}

# --- Global Load Balancer ---

# Static global IP address — point your A record here
resource "google_compute_global_address" "landing" {
  name = "sourced-landing-ip"
}

# Serverless NEG pointing to the Cloud Run service
resource "google_compute_region_network_endpoint_group" "landing" {
  name                  = "sourced-landing-neg"
  region                = var.region
  network_endpoint_type = "SERVERLESS"

  cloud_run {
    service = google_cloud_run_v2_service.landing.name
  }
}

# Backend service wrapping the serverless NEG
resource "google_compute_backend_service" "landing" {
  name                  = "sourced-landing-backend"
  load_balancing_scheme = "EXTERNAL"
  protocol              = "HTTPS"

  backend {
    group = google_compute_region_network_endpoint_group.landing.id
  }

  log_config {
    enable = true
  }
}

# URL map — routes all traffic to the backend
resource "google_compute_url_map" "landing" {
  name            = "sourced-landing-url-map"
  default_service = google_compute_backend_service.landing.id
}

# Google-managed SSL certificate for sourced.dev
resource "google_compute_managed_ssl_certificate" "landing" {
  name = "sourced-landing-cert"

  managed {
    domains = [var.landing_domain]
  }
}

# HTTPS target proxy
resource "google_compute_target_https_proxy" "landing" {
  name             = "sourced-landing-https-proxy"
  url_map          = google_compute_url_map.landing.id
  ssl_certificates = [google_compute_managed_ssl_certificate.landing.id]
}

# HTTPS forwarding rule (port 443)
resource "google_compute_global_forwarding_rule" "landing_https" {
  name                  = "sourced-landing-https-rule"
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL"
  port_range            = "443"
  target                = google_compute_target_https_proxy.landing.id
  ip_address            = google_compute_global_address.landing.id
}
