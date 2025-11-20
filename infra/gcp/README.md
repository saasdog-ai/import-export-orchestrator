# GCP Infrastructure

This directory will contain Terraform configuration for deploying the import-export-orchestrator to Google Cloud Platform.

## Planned Components

- Cloud Run or Google Kubernetes Engine (GKE)
- Cloud SQL for PostgreSQL
- Virtual Private Cloud (VPC)
- Cloud Load Balancing
- Secret Manager for secrets management

## Implementation Notes

The infrastructure will follow the same clean architecture principles as the AWS deployment:

1. **Authentication**: Use Google Cloud Service Accounts (never store credentials)
2. **Secrets Management**: Use Google Secret Manager for database passwords and other secrets
3. **Container Registry**: Use Google Container Registry (GCR) or Artifact Registry for storing Docker images
4. **Monitoring**: Use Cloud Monitoring and Cloud Logging

## Future Implementation

When implementing, ensure:
- All secrets are stored in Google Secret Manager
- Service Accounts are used for service authentication
- VPC firewall rules properly restrict access
- Backups are configured for Cloud SQL
- Monitoring and alerting are set up with Cloud Monitoring

The configuration will use environment variables for GCP credentials:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account-key.json"
# Or use gcloud auth application-default login
export GOOGLE_PROJECT="your-project-id"
export GOOGLE_REGION="us-central1"
```

