# Main data lake bucket
resource "google_storage_bucket" "pydocs_datalake" {
  name                        = "pydocs-datalake"
  location                    = "europe-west2"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  labels = {
    purpose    = "data-lake"
    managed_by = "terraform"
  }
}

# Create folder structure (using objects as placeholders)
# exports/: Raw BigQuery exports (source of truth, kept permanently)
resource "google_storage_bucket_object" "exports_folder" {
  name    = "exports/"
  content = " "
  bucket  = google_storage_bucket.pydocs_datalake.name
}
