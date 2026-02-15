variable "github_token" {
  description = "GitHub API token for fetching READMEs"
  type        = string
  sensitive   = true
}

variable "github_app_client_id" {
  description = "GitHub App OAuth client ID"
  type        = string
}

variable "github_app_client_secret" {
  description = "GitHub App OAuth client secret"
  type        = string
  sensitive   = true
}
