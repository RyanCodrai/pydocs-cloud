terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# BigQuery Dataset (create if it doesn't exist)
resource "google_bigquery_dataset" "exports_dataset" {
  dataset_id    = var.dataset_id
  friendly_name = var.dataset_friendly_name
  description   = "Dataset for tracking data exports and pipeline metadata"
  location      = "US"

  labels = {
    environment = var.environment
    managed_by  = "terraform"
  }
}

# BigQuery Exports Tracking Table
resource "google_bigquery_table" "exports" {
  dataset_id = google_bigquery_dataset.exports_dataset.dataset_id
  table_id   = "exports"

  description = "Tracks BigQuery data exports to external destinations"

  labels = {
    purpose    = "export-tracking"
    managed_by = "terraform"
  }

  schema = jsonencode([
    {
      name        = "id"
      type        = "INTEGER"
      mode        = "REQUIRED"
      description = "Unique identifier for the export"
    },
    {
      name               = "timestamp"
      type               = "TIMESTAMP"
      mode               = "NULLABLE"
      description        = "When the export was created"
      defaultValueExpression = "CURRENT_TIMESTAMP()"
    },
    {
      name        = "export_name"
      type        = "STRING"
      mode        = "NULLABLE"
      description = "Name/identifier of the export job"
    },
    {
      name        = "source_table"
      type        = "STRING"
      mode        = "NULLABLE"
      description = "Source BigQuery table that was exported"
    },
    {
      name        = "destination_uri"
      type        = "STRING"
      mode        = "NULLABLE"
      description = "Destination URI where data was exported (e.g., GCS path)"
    },
    {
      name        = "record_count"
      type        = "INTEGER"
      mode        = "NULLABLE"
      description = "Number of records exported"
    }
  ])
}
