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
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

# Provider configuration with workspace-specific project
provider "google" {
  project = local.project_id
}

# Derive environment from workspace
# Fail fast if someone tries to use the default workspace
locals {
  environment = terraform.workspace == "default" ? error("Please create and select a workspace (staging, prod). Do not use the default workspace.") : terraform.workspace

  # Map workspace to GCP project ID
  project_id = {
    prod    = "pydocs-prod"
    staging = "pydocs-staging"
  }[local.environment]

  # Required GCP APIs for the project
  required_apis = [
    "compute.googleapis.com",
    "cloudfunctions.googleapis.com",
    "cloudbuild.googleapis.com",
    "eventarc.googleapis.com",
    "run.googleapis.com",
    "bigquerydatatransfer.googleapis.com",
    "cloudtasks.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "servicenetworking.googleapis.com",
  ]
}

# Enable required APIs for the project
resource "google_project_service" "required_apis" {
  for_each = toset(local.required_apis)

  service            = each.key
  disable_on_destroy = false
}

# Storage Module - GCS buckets for data lake
module "storage" {
  source = "./storage"

  depends_on = [google_project_service.required_apis]
}

# BigQuery Module - Dataset and scheduled queries
module "bigquery" {
  source = "./bigquery"

  project_id  = local.project_id
  environment = local.environment

  depends_on = [google_project_service.required_apis]
}

# Cloud Tasks Module - Task queues for async processing
module "cloud_tasks" {
  source = "./cloud_tasks"

  depends_on = [google_project_service.required_apis]
}

# Cloud SQL Module - PostgreSQL database
module "cloud_sql" {
  source = "./cloud_sql"

  project_id  = local.project_id
  environment = local.environment

  depends_on = [google_project_service.required_apis]
}

# Cloud Functions Module - Event-driven functions
module "cloud_functions" {
  source                 = "./cloud_functions"
  project_id             = local.project_id
  data_bucket_name       = module.storage.bucket_name
  cloud_tasks_queue_path = module.cloud_tasks.package_releases_queue_path

  depends_on = [google_project_service.required_apis, module.storage, module.cloud_tasks]
}

# Secrets Module - Secret Manager for application config
module "secrets" {
  source = "./secrets"

  environment = local.environment

  # Cloud Run uses default compute service account by default
  # Update this if you create a dedicated service account
  cloud_run_service_account = data.google_compute_default_service_account.default.email

  # Database connection details from cloud_sql module
  postgres_db       = module.cloud_sql.database_name
  postgres_user     = module.cloud_sql.database_user
  postgres_password = module.cloud_sql.database_password
  postgres_host     = module.cloud_sql.private_ip_address
  postgres_port     = module.cloud_sql.database_port

  depends_on = [google_project_service.required_apis, module.cloud_sql]
}

# Data source for default compute service account
data "google_compute_default_service_account" "default" {
  depends_on = [google_project_service.required_apis]
}
