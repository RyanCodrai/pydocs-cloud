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

resource "google_secret_manager_secret_version" "logging_level" {
  secret      = google_secret_manager_secret.logging_level.id
  secret_data = var.logging_level
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

resource "google_secret_manager_secret_version" "environment" {
  secret      = google_secret_manager_secret.environment.id
  secret_data = upper(var.environment)
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

resource "google_secret_manager_secret_version" "postgres_db" {
  secret      = google_secret_manager_secret.postgres_db.id
  secret_data = var.postgres_db
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

resource "google_secret_manager_secret_version" "postgres_user" {
  secret      = google_secret_manager_secret.postgres_user.id
  secret_data = var.postgres_user
}

# postgres_password secret is created by cloud_sql module
# We just reference it here for IAM permissions
data "google_secret_manager_secret" "postgres_password" {
  secret_id = "postgres-password"
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

resource "google_secret_manager_secret_version" "postgres_host" {
  secret      = google_secret_manager_secret.postgres_host.id
  secret_data = var.postgres_host
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

resource "google_secret_manager_secret_version" "postgres_port" {
  secret      = google_secret_manager_secret.postgres_port.id
  secret_data = var.postgres_port
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

# External API Keys
resource "google_secret_manager_secret" "github_token" {
  secret_id = "github-token"

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    category    = "api-keys"
  }
}

resource "google_secret_manager_secret_version" "github_token" {
  secret      = google_secret_manager_secret.github_token.id
  secret_data = var.github_token
}



# Grant Cloud Run service account access to all secrets
locals {
  secrets = {
    logging-level        = google_secret_manager_secret.logging_level.id
    app-environment      = google_secret_manager_secret.environment.id
    postgres-db          = google_secret_manager_secret.postgres_db.id
    postgres-user        = google_secret_manager_secret.postgres_user.id
    postgres-password    = data.google_secret_manager_secret.postgres_password.id
    postgres-host        = google_secret_manager_secret.postgres_host.id
    postgres-port        = google_secret_manager_secret.postgres_port.id
    auth0-domain         = google_secret_manager_secret.auth0_domain.id
    auth0-issuer         = google_secret_manager_secret.auth0_issuer.id
    auth0-client-id      = google_secret_manager_secret.auth0_client_id.id
    auth0-algorithms     = google_secret_manager_secret.auth0_algorithms.id
    github-token         = google_secret_manager_secret.github_token.id
  }
}

resource "google_secret_manager_secret_iam_member" "cloud_run_access" {
  for_each = local.secrets

  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.cloud_run_service_account}"
}
