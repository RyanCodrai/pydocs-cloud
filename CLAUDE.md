## Tech Stack

This is primarily a Python project. When implementing features, follow existing patterns in the codebase for API endpoints, service organization, and dependency injection.

## Code Organization

When modifying existing functionality, keep changes within existing file structures unless explicitly asked to create new files. Prefer extending current modules over creating new service layers.

## Infrastructure

For infrastructure changes (GCS buckets, databases, cloud resources), always ask before creating new resources. Prefer using existing infrastructure (e.g., 'datalake' bucket) over provisioning new ones via Terraform.

## Communication

When the user asks a question, answer it. Don't infer that a question is a request to take action (e.g. delete, refactor, change something). Wait for explicit instructions before modifying code.
