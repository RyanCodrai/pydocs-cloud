# Cloud SQL PostgreSQL instance for pydocs
# Private IP only (no public IP)

# Enable required APIs
resource "google_project_service" "secretmanager" {
  service            = "secretmanager.googleapis.com"
  disable_on_destroy = false
}

# Reference the default VPC network
data "google_compute_network" "default" {
  name = "default"
}

resource "google_sql_database_instance" "pydocs" {
  name             = "pydocs-db"
  database_version = "POSTGRES_17"
  region           = var.region

  settings {
    tier              = "db-custom-2-7680"
    availability_type = "ZONAL"
    disk_type         = "PD_SSD"
    disk_size         = 20

    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 7
      }
    }

    ip_configuration {
      ipv4_enabled                                  = false
      private_network                               = data.google_compute_network.default.id
      enable_private_path_for_google_cloud_services = true
    }

    maintenance_window {
      day          = 7 # Sunday
      hour         = 3 # 3 AM
      update_track = "stable"
    }

    insights_config {
      query_insights_enabled  = true
      query_plans_per_minute  = 5
      query_string_length     = 1024
      record_application_tags = true
    }
  }

  deletion_protection = true

  lifecycle {
    prevent_destroy = true
  }
}

# Use the default 'postgres' database (no need to create a custom database)

# Create a random password for the postgres user
resource "random_password" "postgres_password" {
  length  = 32
  special = true
}

# Create postgres user with password
resource "google_sql_user" "postgres" {
  name     = "postgres"
  instance = google_sql_database_instance.pydocs.name
  password = random_password.postgres_password.result
}

# Store the password in Secret Manager
resource "google_secret_manager_secret" "postgres_password" {
  secret_id = "postgres-password"

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
    category    = "database"
  }

  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret_version" "postgres_password" {
  secret      = google_secret_manager_secret.postgres_password.id
  secret_data = random_password.postgres_password.result
}
