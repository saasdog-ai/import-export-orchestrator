# AWS Secrets Manager for sensitive configuration
# These resources are only created when use_shared_infra = false
# In shared mode, we use the shared_db_credentials_secret_arn variable

# Database URL secret (contains password, host, and credentials)
resource "aws_secretsmanager_secret" "database_url" {
  count       = var.use_shared_infra ? 0 : 1
  name        = "${var.project_name}-database-url-${var.environment}"
  description = "Database connection URL for ${var.project_name} ${var.environment}"

  tags = merge(var.common_tags, {
    Name        = "${var.project_name}-database-url-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  })
}

resource "aws_secretsmanager_secret_version" "database_url" {
  count         = var.use_shared_infra ? 0 : 1
  secret_id     = aws_secretsmanager_secret.database_url[0].id
  secret_string = "postgresql+asyncpg://${var.database_username}:${var.database_password}@${aws_db_instance.main[0].endpoint}/${var.database_name}"
}
