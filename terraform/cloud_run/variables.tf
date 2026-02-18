# Variables for Cloud Run services

variable "project_id" {
  description = "Google Cloud project ID"
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run services"
  type        = string
  default     = "europe-west2"
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

variable "mcp_api_domain" {
  description = "Custom domain for the MCP API (e.g., mcp.sourced.dev)"
  type        = string
  default     = "mcp.sourced.dev"
}

variable "landing_domain" {
  description = "Custom domain for the landing page (e.g., sourced.dev)"
  type        = string
  default     = "sourced.dev"
}

variable "landing_docker_image" {
  description = "Docker image URL for the landing page"
  type        = string
}

