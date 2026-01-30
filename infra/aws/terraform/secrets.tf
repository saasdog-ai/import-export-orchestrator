# AWS Secrets Manager for sensitive configuration

# Database password secret
resource "aws_secretsmanager_secret" "db_password" {
  name        = "${var.project_name}-db-password-${var.environment}"
  description = "Database password for ${var.project_name} ${var.environment}"

  tags = merge(var.common_tags, {
    Name        = "${var.project_name}-db-password-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  })
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = var.database_password
}
