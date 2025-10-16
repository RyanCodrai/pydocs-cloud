variable "project_id" {
  description = "Google Cloud project ID (defaults to gcloud config if not set)"
  type        = string
  default     = null
}

variable "region" {
  description = "Region for Cloud Tasks queue"
  type        = string
  default     = "europe-west2"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}
