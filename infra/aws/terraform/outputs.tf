# Outputs

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}

output "rds_database_name" {
  description = "RDS database name"
  value       = aws_db_instance.main.db_name
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
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

