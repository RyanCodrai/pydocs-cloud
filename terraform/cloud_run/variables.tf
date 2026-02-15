# Variables for Cloud Run services

variable "project_id" {
  description = "Google Cloud project ID"
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run services"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment (prod, staging)"
  type        = string
}

variable "docker_image" {
  description = "Docker image URL for the API (e.g., gcr.io/project/image:tag)"
  type        = string
}


variable "cloud_sql_connection_name" {
  description = "Cloud SQL connection name for VPC access"
  type        = string
}

variable "data_bucket_name" {
  description = "GCS bucket name for data storage"
  type        = string
}

variable "user_api_domain" {
  description = "Custom domain for the user API (e.g., api.sourced.dev)"
  type        = string
  default     = "api.sourced.dev"
}

