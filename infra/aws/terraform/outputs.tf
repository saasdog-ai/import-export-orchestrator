# Outputs

output "vpc_id" {
  description = "ID of the VPC"
  value       = local.vpc_id
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = local.public_subnet_ids
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = local.private_subnet_ids
}

output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = local.rds_endpoint
  sensitive   = true
}

output "rds_database_name" {
  description = "RDS database name"
  value       = var.database_name
}

output "ecs_cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = local.ecs_cluster_arn
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = local.ecs_cluster_name
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.main.name
}

output "task_definition_arn" {
  description = "ARN of the ECS task definition"
  value       = aws_ecs_task_definition.main.arn
}

output "alb_dns_name" {
  description = "DNS name of the ALB (if enabled)"
  value       = var.enable_alb ? aws_lb.main[0].dns_name : null
}

output "s3_bucket_name" {
  description = "Name of the S3 bucket for export files"
  value       = aws_s3_bucket.exports.id
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket for export files"
  value       = aws_s3_bucket.exports.arn
}

output "sqs_queue_url" {
  description = "URL of the SQS queue for job processing"
  value       = aws_sqs_queue.job_runner.url
}

output "sqs_queue_arn" {
  description = "ARN of the SQS queue for job processing"
  value       = aws_sqs_queue.job_runner.arn
}

output "sqs_queue_name" {
  description = "Name of the SQS queue for job processing"
  value       = aws_sqs_queue.job_runner.name
}

output "sqs_dlq_url" {
  description = "URL of the SQS dead letter queue"
  value       = aws_sqs_queue.job_runner_dlq.url
}

# Note: ECR repository outputs are defined in ecr.tf

# =============================================================================
# Shared Infrastructure Outputs
# =============================================================================
# When this project creates infrastructure in standalone mode (use_shared_infra = false),
# it can export these values for other projects to use in shared mode.
# Copy the output of 'shared_infra_tfvars' into another project's terraform.tfvars.

output "ecs_security_group_id" {
  description = "ECS tasks security group ID"
  value       = local.ecs_security_group_id
}

output "alb_security_group_id" {
  description = "ALB security group ID"
  value       = local.alb_security_group_id
}

output "rds_security_group_id" {
  description = "RDS security group ID"
  value       = local.rds_security_group_id
}

output "db_credentials_secret_arn" {
  description = "ARN of the database credentials secret in Secrets Manager"
  value       = local.db_credentials_secret_arn
  sensitive   = true
}

output "shared_infra_tfvars" {
  description = "Copy this into another project's terraform.tfvars to use shared infrastructure"
  value       = var.use_shared_infra ? "Already using shared infrastructure" : <<-EOT
# Shared Infrastructure Configuration
# Copy these values into another project's terraform.tfvars

use_shared_infra = true
shared_project_name = "${local.infra_name}"

# VPC & Networking
shared_vpc_id = "${local.vpc_id}"
shared_public_subnet_ids = ${jsonencode(local.public_subnet_ids)}
shared_private_subnet_ids = ${jsonencode(local.private_subnet_ids)}

# Security Groups
shared_alb_security_group_id = "${local.alb_security_group_id}"
shared_ecs_security_group_id = "${local.ecs_security_group_id}"
shared_rds_security_group_id = "${local.rds_security_group_id}"

# ECS Cluster
shared_ecs_cluster_arn = "${local.ecs_cluster_arn}"

# RDS (create your own database in the shared RDS or use the provided endpoint)
shared_rds_endpoint = "${local.rds_endpoint}"
shared_db_credentials_secret_arn = "${local.db_credentials_secret_arn}"
EOT
}
