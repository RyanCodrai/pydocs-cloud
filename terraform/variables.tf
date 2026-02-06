variable "github_token" {
  description = "GitHub API token for fetching READMEs"
  type        = string
  sensitive   = true
}

variable "npm_token" {
  description = "Read-only npm access token for higher registry API rate limits"
  type        = string
  sensitive   = true
  default     = ""
}
