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

  # Default region for all resources
  region = "europe-west2"

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
    "artifactregistry.googleapis.com",
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

  depends_on = [
    google_project_service.required_apis["compute.googleapis.com"]
  ]
}

# BigQuery Module - Dataset and scheduled queries
module "bigquery" {
  source = "./bigquery"

  project_id  = local.project_id
  environment = local.environment

  depends_on = [
    google_project_service.required_apis["bigquerydatatransfer.googleapis.com"]
  ]
}

# Cloud Tasks Module - Task queues for async processing
module "cloud_tasks" {
  source = "./cloud_tasks"

  depends_on = [
    google_project_service.required_apis["cloudtasks.googleapis.com"]
  ]
}

# Cloud SQL Module - PostgreSQL database
module "cloud_sql" {
  source = "./cloud_sql"

  project_id  = local.project_id
  environment = local.environment

  depends_on = [
    google_project_service.required_apis["compute.googleapis.com"],
    google_project_service.required_apis["sqladmin.googleapis.com"],
    google_project_service.required_apis["secretmanager.googleapis.com"],
    google_project_service.required_apis["servicenetworking.googleapis.com"]
  ]
}

# Cloud Functions Module - Event-driven functions
module "cloud_functions" {
  source                 = "./cloud_functions"
  project_id             = local.project_id
  data_bucket_name       = module.storage.bucket_name
  cloud_tasks_queue_path = module.cloud_tasks.package_releases_queue_path
  pypi_processor_url     = "${module.cloud_run.releases_api_url}/api/v1/webhooks/releases"

  depends_on = [
    google_project_service.required_apis["cloudfunctions.googleapis.com"],
    google_project_service.required_apis["cloudbuild.googleapis.com"],
    google_project_service.required_apis["eventarc.googleapis.com"],
    google_project_service.required_apis["run.googleapis.com"],
    module.storage,
    module.cloud_tasks,
    module.cloud_run
  ]
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

  depends_on = [
    google_project_service.required_apis["secretmanager.googleapis.com"],
    module.cloud_sql
  ]
}

# Data source to get the latest image digest from Artifact Registry
data "google_artifact_registry_docker_image" "api_image" {
  location      = local.region
  repository_id = "pydocs-images"
  image_name    = "pydocs-api:latest"
}


# Cloud Run Module - API services
module "cloud_run" {
  source = "./cloud_run"

  project_id                       = local.project_id
  region                           = local.region
  environment                      = local.environment
  docker_image                     = data.google_artifact_registry_docker_image.api_image.self_link
  cloud_sql_connection_name        = module.cloud_sql.instance_connection_name
  data_bucket_name                 = module.storage.bucket_name

  depends_on = [
    google_project_service.required_apis["run.googleapis.com"],
    google_project_service.required_apis["artifactregistry.googleapis.com"],
    module.cloud_sql,
    module.secrets,
    module.cloud_tasks
  ]
}

# Compute Module - Gateway instance for debugging
module "compute" {
  source = "./compute"

  project_id  = local.project_id
  region      = local.region
  environment = local.environment

  depends_on = [
    google_project_service.required_apis["compute.googleapis.com"]
  ]
}

# Data source for default compute service account
data "google_compute_default_service_account" "default" {
  depends_on = [
    google_project_service.required_apis["compute.googleapis.com"]
  ]
}
