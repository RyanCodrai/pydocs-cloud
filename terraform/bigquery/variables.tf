variable "project_id" {
  description = "Google Cloud project ID (defaults to gcloud config if not set)"
  type        = string
  default     = null
}

variable "region" {
  description = "Default region for resources"
  type        = string
  default     = "us-central1"
}

variable "dataset_id" {
  description = "BigQuery dataset ID"
  type        = string
  default     = "pydocs_us"
}

variable "dataset_friendly_name" {
  description = "Friendly name for the BigQuery dataset"
  type        = string
  default     = "Exports Tracking"
}

variable "environment" {
  description = "Environment label (e.g., dev, staging, prod)"
  type        = string
  default     = "prod"
}
