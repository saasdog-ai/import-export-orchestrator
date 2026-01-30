# AWS Secrets Manager for sensitive configuration

# Database URL secret (contains password, host, and credentials)
resource "aws_secretsmanager_secret" "database_url" {
  name        = "${var.project_name}-database-url-${var.environment}"
  description = "Database connection URL for ${var.project_name} ${var.environment}"

  tags = merge(var.common_tags, {
    Name        = "${var.project_name}-database-url-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  })
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id     = aws_secretsmanager_secret.database_url.id
  secret_string = "postgresql+asyncpg://${var.database_username}:${var.database_password}@${aws_db_instance.main.endpoint}/${var.database_name}"
}
