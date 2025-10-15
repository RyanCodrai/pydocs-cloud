variable "project_id" {
  description = "Google Cloud project ID (defaults to gcloud config if not set)"
  type        = string
  default     = null
}

variable "region" {
  description = "Default region for resources"
  type        = string
  default     = "europe-west2"
}
