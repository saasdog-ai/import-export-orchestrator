# =============================================================================
# Local values - resolve shared vs standalone resources
# =============================================================================
# This file enables the project to work in two modes:
# 1. Standalone mode (use_shared_infra = false): Creates all resources
# 2. Shared mode (use_shared_infra = true): Uses existing shared resources
#
# In shared mode, the project creates only project-specific resources:
# - ECR repository, CloudWatch log group, task definition, ECS service
# - S3 bucket, SQS queue (project-specific)
# - IAM roles (project-specific)
#
# When creating shared infrastructure (standalone mode), resources are named
# using shared_project_name so other projects can reference them with consistent names.

locals {
  # Use shared or create standalone
  use_shared = var.use_shared_infra

  # Resource naming for shared infrastructure (VPC, ECS cluster, RDS, security groups)
  # Uses shared_project_name so multiple projects can share with consistent naming
  infra_name = var.shared_project_name

  # VPC & Networking
  vpc_id             = local.use_shared ? var.shared_vpc_id : aws_vpc.main[0].id
  public_subnet_ids  = local.use_shared ? var.shared_public_subnet_ids : aws_subnet.public[*].id
  private_subnet_ids = local.use_shared ? var.shared_private_subnet_ids : aws_subnet.private[*].id

  # Security Groups
  alb_security_group_id = local.use_shared ? var.shared_alb_security_group_id : (var.enable_alb ? aws_security_group.alb[0].id : "")
  ecs_security_group_id = local.use_shared ? var.shared_ecs_security_group_id : aws_security_group.ecs_tasks[0].id
  rds_security_group_id = local.use_shared ? var.shared_rds_security_group_id : aws_security_group.rds[0].id

  # ECS Cluster
  ecs_cluster_arn  = local.use_shared ? var.shared_ecs_cluster_arn : aws_ecs_cluster.main[0].arn
  ecs_cluster_name = local.use_shared ? split("/", var.shared_ecs_cluster_arn)[1] : aws_ecs_cluster.main[0].name

  # RDS
  rds_endpoint              = local.use_shared ? var.shared_rds_endpoint : aws_db_instance.main[0].endpoint
  db_credentials_secret_arn = local.use_shared ? var.shared_db_credentials_secret_arn : aws_secretsmanager_secret.database_url[0].arn

  # Common tags
  tags = merge(var.common_tags, {
    SharedInfra = local.use_shared ? "true" : "false"
  })
}
