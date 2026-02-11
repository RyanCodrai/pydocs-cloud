variable "environment" {
  description = "Environment name (derived from terraform workspace)"
  type        = string
}

variable "logging_level" {
  description = "Application logging level"
  type        = string
  default     = "INFO"
}

variable "cloud_run_service_account" {
  description = "Service account email for Cloud Run service"
  type        = string
}

# Database connection values from cloud_sql module
variable "postgres_db" {
  description = "PostgreSQL database name"
  type        = string
}

variable "postgres_user" {
  description = "PostgreSQL user name"
  type        = string
}

variable "postgres_password" {
  description = "PostgreSQL password"
  type        = string
  sensitive   = true
}

variable "postgres_host" {
  description = "PostgreSQL host (private IP)"
  type        = string
}

variable "postgres_port" {
  description = "PostgreSQL port"
  type        = string
}

variable "github_token" {
  description = "GitHub API token for fetching READMEs"
  type        = string
  sensitive   = true
}
