terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}

# Provider will automatically use GOOGLE_PROJECT environment variable
provider "google" {
}

# Storage Module - GCS buckets for data lake
module "storage" {
  source = "./storage"
}

# BigQuery Module - Dataset and scheduled queries
module "bigquery" {
  source = "./bigquery"
}

# Cloud Functions Module - Event-driven functions
module "cloud_functions" {
  source           = "./cloud_functions"
  data_bucket_name = module.storage.bucket_name

  depends_on = [module.storage]
}

# Cloud Tasks Module - Task queues for async processing
module "cloud_tasks" {
  source = "./cloud_tasks"
}
