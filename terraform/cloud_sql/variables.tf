variable "project_id" {
  description = "Google Cloud project ID"
  type        = string
}

variable "region" {
  description = "Region for Cloud SQL instance"
  type        = string
  default     = "europe-west2"
}

variable "environment" {
  description = "Environment name (derived from terraform workspace)"
  type        = string
}
