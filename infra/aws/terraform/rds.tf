# RDS Database Resources
# These resources are only created when use_shared_infra = false

# DB Subnet Group
resource "aws_db_subnet_group" "main" {
  count      = var.use_shared_infra ? 0 : 1
  name       = "${local.infra_name}-db-subnet-group-${var.environment}"
  subnet_ids = local.private_subnet_ids

  tags = merge(
    var.common_tags,
    {
      Name = "${local.infra_name}-db-subnet-group-${var.environment}"
    }
  )
}

# RDS Parameter Group
resource "aws_db_parameter_group" "main" {
  count  = var.use_shared_infra ? 0 : 1
  name   = "${local.infra_name}-postgres-${var.environment}"
  family = "postgres${var.postgres_version}"

  parameter {
    name  = "log_statement"
    value = "all"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }

  tags = merge(
    var.common_tags,
    {
      Name = "${local.infra_name}-pg-params-${var.environment}"
    }
  )
}

# RDS Instance
resource "aws_db_instance" "main" {
  count          = var.use_shared_infra ? 0 : 1
  identifier     = "${local.infra_name}-db-${var.environment}"
  engine         = "postgres"
  engine_version = var.postgres_version
  instance_class = var.database_instance_class

  allocated_storage     = var.database_allocated_storage
  max_allocated_storage = var.database_allocated_storage * 2
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = var.database_name
  username = var.database_username
  password = var.database_password

  vpc_security_group_ids = [local.rds_security_group_id]
  db_subnet_group_name   = aws_db_subnet_group.main[0].name
  parameter_group_name   = aws_db_parameter_group.main[0].name

  backup_retention_period = var.rds_backup_retention_period
  backup_window           = var.rds_backup_window
  maintenance_window      = var.rds_maintenance_window

  skip_final_snapshot       = var.environment == "dev"
  final_snapshot_identifier = var.environment != "dev" ? "${local.infra_name}-final-snapshot-${var.environment}-${formatdate("YYYY-MM-DD-hhmm", timestamp())}" : null

  deletion_protection = var.environment == "prod"

  tags = merge(
    var.common_tags,
    {
      Name = "${local.infra_name}-db-${var.environment}"
    }
  )
}
