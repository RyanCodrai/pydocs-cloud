variable "region" {
  description = "Region for Cloud SQL instance"
  type        = string
  default     = "europe-west2"
}

variable "environment" {
  description = "Environment name (e.g., prod, staging)"
  type        = string
  default     = "prod"
}
