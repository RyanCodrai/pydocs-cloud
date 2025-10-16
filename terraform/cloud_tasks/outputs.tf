output "queue_id" {
  description = "The ID of the Cloud Tasks queue"
  value       = google_cloud_tasks_queue.release_updates.id
}

output "queue_name" {
  description = "The name of the Cloud Tasks queue"
  value       = google_cloud_tasks_queue.release_updates.name
}

output "queue_location" {
  description = "The location of the Cloud Tasks queue"
  value       = google_cloud_tasks_queue.release_updates.location
}
