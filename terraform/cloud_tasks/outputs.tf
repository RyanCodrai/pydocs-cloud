output "package_releases_queue_path" {
  description = "The full path of the package releases Cloud Tasks queue (projects/PROJECT/locations/LOCATION/queues/QUEUE)"
  value       = google_cloud_tasks_queue.package_releases.id
}

output "package_releases_queue_name" {
  description = "The name of the package releases Cloud Tasks queue"
  value       = google_cloud_tasks_queue.package_releases.name
}

output "package_releases_queue_location" {
  description = "The location of the package releases Cloud Tasks queue"
  value       = google_cloud_tasks_queue.package_releases.location
}
