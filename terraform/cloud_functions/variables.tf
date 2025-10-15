variable "project_id" {
  description = "Google Cloud project ID (defaults to gcloud config if not set)"
  type        = string
  default     = null
}

variable "region" {
  description = "Region for Cloud Functions"
  type        = string
  default     = "europe-west2"
}

variable "data_bucket_name" {
  description = "Name of the data lake bucket to trigger on"
  type        = string
  default     = "pydocs-datalake"
}
