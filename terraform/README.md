# Terraform Infrastructure

This directory contains Terraform configuration for deploying pydocs infrastructure to GCP.

## Workspaces and GCP Projects

This configuration uses Terraform workspaces to manage different environments, with each workspace deploying to a separate GCP project:

| Workspace | GCP Project     | Environment |
|-----------|-----------------|-------------|
| prod      | pydocs-prod     | Production  |
| staging   | pydocs-staging  | Staging     |

## Prerequisites

1. **Create GCP Projects** (one-time setup):
   ```bash
   gcloud projects create pydocs-prod
   gcloud projects create pydocs-staging
   ```

2. **Enable billing** for each project in the GCP Console

3. **Set up authentication**:
   ```bash
   gcloud auth application-default login
   ```

## Deploying to an Environment

### First Time Setup

1. **Create workspace** (one-time per environment):
   ```bash
   cd terraform
   terraform workspace new prod
   ```

2. **Initialize Terraform**:
   ```bash
   terraform init
   ```

3. **Deploy infrastructure**:
   ```bash
   terraform apply
   ```

### Subsequent Deployments

1. **Select workspace**:
   ```bash
   terraform workspace select prod
   ```

2. **Apply changes**:
   ```bash
   terraform apply
   ```

## Switching Between Environments

```bash
# List available workspaces
terraform workspace list

# Switch to a different environment
terraform workspace select staging
terraform apply
```

## Auto-Populated Secrets

The following secrets are automatically populated by Terraform:

- `logging-level` → "INFO" (configurable via variable)
- `app-environment` → "PROD" / "STAGING" (from workspace)
- `postgres-db` → "postgres"
- `postgres-user` → "postgres"
- `postgres-password` → auto-generated password
- `postgres-host` → Cloud SQL private IP
- `postgres-port` → "5432"

## Manual Secrets

The following Auth0 secrets must be manually set after infrastructure is created:

```bash
# Set Auth0 secrets for the current workspace/project
echo -n "auth.pydocs.ai" | gcloud secrets versions add auth0-domain --data-file=-
echo -n "https://auth.pydocs.ai/" | gcloud secrets versions add auth0-issuer --data-file=-
echo -n "your-client-id" | gcloud secrets versions add auth0-client-id --data-file=-
echo -n "RS256" | gcloud secrets versions add auth0-algorithms --data-file=-
```

## Modules

- `storage` - GCS buckets for data lake
- `bigquery` - BigQuery datasets and scheduled queries
- `cloud_tasks` - Task queues for async processing
- `cloud_sql` - PostgreSQL database (private IP only)
- `cloud_functions` - Event-driven functions
- `secrets` - Secret Manager for application config
