variable "environment" {
  description = "Environment name (e.g., prod, staging)"
  type        = string
  default     = "prod"
}

variable "cloud_run_service_account" {
  description = "Service account email for Cloud Run service"
  type        = string
}
