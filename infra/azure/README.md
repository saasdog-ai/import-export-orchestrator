# Azure Infrastructure

This directory will contain Terraform configuration for deploying the import-export-orchestrator to Azure.

## Planned Components

- Azure Container Instances or Azure Kubernetes Service (AKS)
- Azure Database for PostgreSQL
- Azure Virtual Network
- Azure Load Balancer
- Azure Key Vault for secrets management

## Implementation Notes

The infrastructure will follow the same clean architecture principles as the AWS deployment:

1. **Authentication**: Use Azure Service Principals or Managed Identities (never store credentials)
2. **Secrets Management**: Use Azure Key Vault for database passwords and other secrets
3. **Container Registry**: Use Azure Container Registry (ACR) for storing Docker images
4. **Monitoring**: Use Azure Monitor and Application Insights

## Future Implementation

When implementing, ensure:
- All secrets are stored in Azure Key Vault
- Managed Identities are used for service authentication
- Network security groups properly restrict access
- Backups are configured for the database
- Monitoring and alerting are set up

The configuration will use environment variables for Azure credentials, similar to AWS:
```bash
export ARM_CLIENT_ID="your-client-id"
export ARM_CLIENT_SECRET="your-client-secret"  # Or use Azure CLI login
export ARM_SUBSCRIPTION_ID="your-subscription-id"
export ARM_TENANT_ID="your-tenant-id"
```

