# Production Readiness Checklist

Items to address before deploying to production.

## Infrastructure Security

- [ ] **Enable CloudFront for UI hosting** - Currently using S3 website hosting (HTTP only). CloudFront provides:
  - HTTPS encryption
  - DDoS protection
  - Edge caching
  - Custom domain support
  - Note: Requires AWS account verification

- [ ] **S3 bucket public access** - Currently UI bucket allows public access for S3 website hosting. With CloudFront:
  - Block all public access on S3
  - Use Origin Access Control (OAC) for CloudFront-only access
  - Config exists in `ui.tf` but CloudFront is commented out

- [ ] **Enable Container Insights** - Currently disabled to stay within free tier. For production:
  - Enable for monitoring and alerting
  - Set up CloudWatch alarms
  - Location: `infra/aws/terraform/ecs.tf`

- [ ] **Increase CloudWatch log retention** - Currently 1 day for dev. For production:
  - Set to 30-90 days for compliance/debugging
  - Location: `infra/aws/terraform/ecs.tf`

## Application Security

- [ ] **JWT Secret Key** - Must be a strong, unique secret in production
  - Set via `JWT_SECRET_KEY` environment variable
  - Never use default value in production

- [ ] **CORS Origins** - Currently includes localhost for dev. For production:
  - Remove localhost origins
  - Only allow production domain(s)
  - Location: `infra/aws/terraform/ecs.tf` (ALLOWED_ORIGINS)

- [ ] **Database Password** - Ensure strong password, consider using AWS Secrets Manager
  - Currently passed via terraform variable
  - Consider rotating credentials periodically

- [ ] **Rate Limiting** - Verify rate limits are appropriate for production traffic
  - Currently configured in `app/core/config.py`

## Database

- [ ] **RDS Instance Size** - Currently `db.t3.micro` for dev
  - Size appropriately for production workload
  - Consider Multi-AZ for high availability
  - Enable automated backups with appropriate retention

- [ ] **Database Encryption** - Ensure encryption at rest is enabled

## Networking

- [ ] **NAT Gateway** - Currently single NAT Gateway
  - Consider NAT Gateway per AZ for high availability
  - Note: Increases cost

- [ ] **VPC Flow Logs** - Enable for network monitoring and security analysis

## Monitoring & Alerting

- [ ] **CloudWatch Alarms** - Set up alerts for:
  - ECS task failures
  - High CPU/memory usage
  - Database connections
  - API error rates
  - Queue depth (SQS)

- [ ] **Health Checks** - Verify ALB health check settings are appropriate

## Cost Optimization

- [ ] **Right-size resources** - Review and adjust:
  - ECS task CPU/memory
  - RDS instance class
  - Consider Reserved Instances for predictable workloads

## CI/CD

- [ ] **Environment-specific configs** - Ensure dev/staging/prod have appropriate settings
  - Different ALLOWED_ORIGINS per environment
  - Different log retention per environment
  - Different instance sizes per environment

## Documentation

- [ ] **Runbook** - Document common operational procedures
- [ ] **Architecture diagram** - Keep up to date
- [ ] **API documentation** - Ensure OpenAPI spec is complete

---

## Current Dev-Only Settings (to change for prod)

| Setting | Dev Value | Prod Recommendation |
|---------|-----------|---------------------|
| Container Insights | disabled | enabled |
| Log Retention | 1 day | 30-90 days |
| UI Hosting | S3 HTTP | CloudFront HTTPS |
| S3 Public Access | allowed | blocked (use OAC) |
| CORS Origins | includes localhost | production domains only |
| RDS Instance | db.t3.micro | db.t3.small or larger |
| ECS Desired Count | 1 | 2+ for HA |
