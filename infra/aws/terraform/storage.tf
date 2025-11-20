# S3 Bucket for Export Files

resource "aws_s3_bucket" "exports" {
  bucket = "${var.project_name}-exports-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-exports-${var.environment}"
  })
}

# Enable versioning for export files
resource "aws_s3_bucket_versioning" "exports" {
  bucket = aws_s3_bucket.exports.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Enable server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "exports" {
  bucket = aws_s3_bucket.exports.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "exports" {
  bucket = aws_s3_bucket.exports.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle policy to transition old files to cheaper storage
resource "aws_s3_bucket_lifecycle_configuration" "exports" {
  bucket = aws_s3_bucket.exports.id

  rule {
    id     = "transition-to-glacier"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365  # Delete files after 1 year
    }
  }
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

