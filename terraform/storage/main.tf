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
    zone       = "bronze-silver-gold"
  }
}

# Create folder structure (using objects as placeholders)
resource "google_storage_bucket_object" "bronze_folder" {
  name    = "bronze/"
  content = " "
  bucket  = google_storage_bucket.pydocs_datalake.name
}

resource "google_storage_bucket_object" "silver_folder" {
  name    = "silver/"
  content = " "
  bucket  = google_storage_bucket.pydocs_datalake.name
}

resource "google_storage_bucket_object" "gold_folder" {
  name    = "gold/"
  content = " "
  bucket  = google_storage_bucket.pydocs_datalake.name
}
