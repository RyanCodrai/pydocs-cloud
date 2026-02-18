# Global External Application Load Balancer for User API
# Routes api.sourced.dev to the Cloud Run user API service

# Static global IP address — point your A record here
resource "google_compute_global_address" "user_api" {
  name = "pydocs-user-api-ip"
}

# Serverless NEG pointing to the Cloud Run service
resource "google_compute_region_network_endpoint_group" "user_api" {
  name                  = "pydocs-user-api-neg"
  region                = var.region
  network_endpoint_type = "SERVERLESS"

  cloud_run {
    service = google_cloud_run_v2_service.user_api.name
  }
}

# Backend service wrapping the serverless NEG
resource "google_compute_backend_service" "user_api" {
  name                  = "pydocs-user-api-backend"
  load_balancing_scheme = "EXTERNAL"
  protocol              = "HTTPS"

  backend {
    group = google_compute_region_network_endpoint_group.user_api.id
  }

  log_config {
    enable = true
  }
}

# URL map — routes all traffic to the backend
resource "google_compute_url_map" "user_api" {
  name            = "pydocs-user-api-url-map"
  default_service = google_compute_backend_service.user_api.id
}

# Google-managed SSL certificate for api.sourced.dev
resource "google_compute_managed_ssl_certificate" "user_api" {
  name = "pydocs-user-api-cert"

  managed {
    domains = [var.user_api_domain]
  }
}

# HTTPS target proxy
resource "google_compute_target_https_proxy" "user_api" {
  name             = "pydocs-user-api-https-proxy"
  url_map          = google_compute_url_map.user_api.id
  ssl_certificates = [google_compute_managed_ssl_certificate.user_api.id]
}

# HTTPS forwarding rule (port 443)
resource "google_compute_global_forwarding_rule" "user_api_https" {
  name                  = "pydocs-user-api-https-rule"
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL"
  port_range            = "443"
  target                = google_compute_target_https_proxy.user_api.id
  ip_address            = google_compute_global_address.user_api.id
}

# --- HTTP → HTTPS redirect ---

resource "google_compute_url_map" "user_api_http_redirect" {
  name = "pydocs-user-api-http-redirect"

  default_url_redirect {
    https_redirect         = true
    strip_query            = false
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
  }
}

resource "google_compute_target_http_proxy" "user_api" {
  name    = "pydocs-user-api-http-proxy"
  url_map = google_compute_url_map.user_api_http_redirect.id
}

resource "google_compute_global_forwarding_rule" "user_api_http" {
  name                  = "pydocs-user-api-http-rule"
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL"
  port_range            = "80"
  target                = google_compute_target_http_proxy.user_api.id
  ip_address            = google_compute_global_address.user_api.id
}
