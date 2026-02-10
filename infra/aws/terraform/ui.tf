# -----------------------------------------------------------------------------
# UI Static Hosting with S3
# -----------------------------------------------------------------------------
# This configuration deploys the React UI as a static website

# S3 bucket for UI static files
resource "aws_s3_bucket" "ui" {
  count  = var.enable_ui ? 1 : 0
  bucket = "${local.name_prefix}-ui-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-ui-${var.environment}"
  })
}

# Allow public access for S3 website hosting
resource "aws_s3_bucket_public_access_block" "ui" {
  count  = var.enable_ui ? 1 : 0
  bucket = aws_s3_bucket.ui[0].id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# S3 static website hosting configuration
resource "aws_s3_bucket_website_configuration" "ui" {
  count  = var.enable_ui ? 1 : 0
  bucket = aws_s3_bucket.ui[0].id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html"
  }
}

# S3 bucket versioning for rollback capability
resource "aws_s3_bucket_versioning" "ui" {
  count  = var.enable_ui ? 1 : 0
  bucket = aws_s3_bucket.ui[0].id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 bucket policy to allow public read access for website hosting
resource "aws_s3_bucket_policy" "ui" {
  count  = var.enable_ui ? 1 : 0
  bucket = aws_s3_bucket.ui[0].id

  depends_on = [aws_s3_bucket_public_access_block.ui]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.ui[0].arn}/*"
      }
    ]
  })
}

# Outputs
output "ui_bucket_name" {
  description = "Name of the S3 bucket for UI files"
  value       = var.enable_ui ? aws_s3_bucket.ui[0].id : null
}

output "ui_url" {
  description = "URL to access the UI (S3 website)"
  value       = var.enable_ui ? "http://${aws_s3_bucket_website_configuration.ui[0].website_endpoint}" : null
}
