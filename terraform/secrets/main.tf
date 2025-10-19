# Secret Manager secrets for application configuration
# All application config is stored here for centralized management and audit trail

# Application Configuration
resource "google_secret_manager_secret" "logging_level" {
  secret_id = "logging-level"

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    category    = "config"
  }
}

resource "google_secret_manager_secret" "environment" {
  secret_id = "app-environment"

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    category    = "config"
  }
}

# Database Configuration
resource "google_secret_manager_secret" "postgres_db" {
  secret_id = "postgres-db"

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    category    = "database"
  }
}

resource "google_secret_manager_secret" "postgres_user" {
  secret_id = "postgres-user"

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    category    = "database"
  }
}

resource "google_secret_manager_secret" "postgres_password" {
  secret_id = "postgres-password"

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    category    = "database"
    sensitive   = "true"
  }
}

resource "google_secret_manager_secret" "postgres_host" {
  secret_id = "postgres-host"

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    category    = "database"
  }
}

resource "google_secret_manager_secret" "postgres_port" {
  secret_id = "postgres-port"

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    category    = "database"
  }
}

# Auth0 Configuration
resource "google_secret_manager_secret" "auth0_domain" {
  secret_id = "auth0-domain"

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    category    = "auth"
  }
}

resource "google_secret_manager_secret" "auth0_issuer" {
  secret_id = "auth0-issuer"

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    category    = "auth"
  }
}

resource "google_secret_manager_secret" "auth0_client_id" {
  secret_id = "auth0-client-id"

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    category    = "auth"
  }
}

resource "google_secret_manager_secret" "auth0_algorithms" {
  secret_id = "auth0-algorithms"

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    category    = "auth"
  }
}

# Grant Cloud Run service account access to all secrets
locals {
  secrets = {
    logging-level        = google_secret_manager_secret.logging_level.id
    app-environment      = google_secret_manager_secret.environment.id
    postgres-db          = google_secret_manager_secret.postgres_db.id
    postgres-user        = google_secret_manager_secret.postgres_user.id
    postgres-password    = google_secret_manager_secret.postgres_password.id
    postgres-host        = google_secret_manager_secret.postgres_host.id
    postgres-port        = google_secret_manager_secret.postgres_port.id
    auth0-domain         = google_secret_manager_secret.auth0_domain.id
    auth0-issuer         = google_secret_manager_secret.auth0_issuer.id
    auth0-client-id      = google_secret_manager_secret.auth0_client_id.id
    auth0-algorithms     = google_secret_manager_secret.auth0_algorithms.id
  }
}

resource "google_secret_manager_secret_iam_member" "cloud_run_access" {
  for_each = local.secrets

  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.cloud_run_service_account}"
}
