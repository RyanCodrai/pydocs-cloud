output "instance_name" {
  description = "The name of the Cloud SQL instance"
  value       = google_sql_database_instance.pydocs.name
}

output "instance_connection_name" {
  description = "The connection name of the instance (used for Cloud SQL Proxy)"
  value       = google_sql_database_instance.pydocs.connection_name
}

output "database_name" {
  description = "The name of the database"
  value       = "postgres"
}

output "public_ip_address" {
  description = "The public IP address of the instance"
  value       = google_sql_database_instance.pydocs.public_ip_address
}

output "private_ip_address" {
  description = "The private IP address of the instance"
  value       = google_sql_database_instance.pydocs.private_ip_address
}

output "postgres_password_secret" {
  description = "The Secret Manager secret ID containing the postgres password"
  value       = google_secret_manager_secret.postgres_password.secret_id
}
