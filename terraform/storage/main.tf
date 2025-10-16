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

# Main data lake bucket
resource "google_storage_bucket" "pydocs_datalake" {
  name                        = "pydocs-datalake"
  location                    = "europe-west2"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  labels = {
    purpose    = "data-lake"
    managed_by = "terraform"
  }
}

# Create folder structure (using objects as placeholders)
# exports/: Raw BigQuery exports (source of truth, kept permanently)
# pending/: Split chunks waiting to be processed (deleted after processing)
resource "google_storage_bucket_object" "exports_folder" {
  name    = "exports/"
  content = " "
  bucket  = google_storage_bucket.pydocs_datalake.name
}

resource "google_storage_bucket_object" "pending_folder" {
  name    = "pending/"
  content = " "
  bucket  = google_storage_bucket.pydocs_datalake.name
}
