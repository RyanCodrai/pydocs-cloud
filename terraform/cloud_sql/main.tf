# Cloud SQL PostgreSQL instance for pydocs

resource "google_sql_database_instance" "pydocs" {
  name             = "pydocs-postgres"
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
      ipv4_enabled = true
      # Add authorized networks as needed
      # authorized_networks {
      #   name  = "office"
      #   value = "0.0.0.0/0"
      # }
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

# Create the pydocs-db database
resource "google_sql_database" "pydocs" {
  name     = "pydocs-db"
  instance = google_sql_database_instance.pydocs.name
}

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
}

resource "google_secret_manager_secret_version" "postgres_password" {
  secret      = google_secret_manager_secret.postgres_password.id
  secret_data = random_password.postgres_password.result
}
