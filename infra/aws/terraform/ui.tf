# UI Static Hosting with S3 + CloudFront
# This configuration deploys the React UI as a static website

# S3 bucket for UI static files
resource "aws_s3_bucket" "ui" {
  bucket = "${var.project_name}-ui-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-ui-${var.environment}"
  })
}

# Allow public access for S3 website hosting (testing)
# For production with CloudFront, set these to true
resource "aws_s3_bucket_public_access_block" "ui" {
  bucket = aws_s3_bucket.ui.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# S3 static website hosting configuration
resource "aws_s3_bucket_website_configuration" "ui" {
  bucket = aws_s3_bucket.ui.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html"
  }
}

# S3 bucket versioning for rollback capability
resource "aws_s3_bucket_versioning" "ui" {
  bucket = aws_s3_bucket.ui.id
  versioning_configuration {
    status = "Enabled"
  }
}

# CloudFront Origin Access Control for secure S3 access
resource "aws_cloudfront_origin_access_control" "ui" {
  name                              = "${var.project_name}-ui-oac-${var.environment}"
  description                       = "OAC for ${var.project_name} UI"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# CloudFront Function to rewrite /api/* paths
resource "aws_cloudfront_function" "api_rewrite" {
  name    = "${var.project_name}-api-rewrite-${var.environment}"
  runtime = "cloudfront-js-2.0"
  comment = "Rewrite /api/* to /* for backend routing"
  publish = true
  code    = <<-EOF
    function handler(event) {
      var request = event.request;
      // Remove /api prefix from URI
      if (request.uri.startsWith('/api/')) {
        request.uri = request.uri.substring(4);
      } else if (request.uri === '/api') {
        request.uri = '/';
      }
      return request;
    }
  EOF
}

# CloudFront distribution (disabled - requires AWS account verification)
# Uncomment when account is verified for production deployment
/*
resource "aws_cloudfront_distribution" "ui" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  comment             = "${var.project_name} UI - ${var.environment}"
  price_class         = var.environment == "prod" ? "PriceClass_All" : "PriceClass_100"

  # S3 origin for static files
  origin {
    domain_name              = aws_s3_bucket.ui.bucket_regional_domain_name
    origin_id                = "S3-${aws_s3_bucket.ui.id}"
    origin_access_control_id = aws_cloudfront_origin_access_control.ui.id
  }

  # API origin (ALB) for /api/* requests
  dynamic "origin" {
    for_each = var.enable_alb ? [1] : []
    content {
      domain_name = aws_lb.main[0].dns_name
      origin_id   = "ALB-API"

      custom_origin_config {
        http_port              = 80
        https_port             = 443
        origin_protocol_policy = "http-only"
        origin_ssl_protocols   = ["TLSv1.2"]
      }
    }
  }

  # Default behavior - serve static files from S3
  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${aws_s3_bucket.ui.id}"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
    compress               = true
  }

  # API behavior - proxy to ALB (no caching)
  dynamic "ordered_cache_behavior" {
    for_each = var.enable_alb ? [1] : []
    content {
      path_pattern     = "/api/*"
      allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
      cached_methods   = ["GET", "HEAD"]
      target_origin_id = "ALB-API"

      forwarded_values {
        query_string = true
        headers      = ["Authorization", "X-Client-ID", "Content-Type", "Accept"]
        cookies {
          forward = "all"
        }
      }

      # Rewrite /api/* to /* before forwarding to backend
      function_association {
        event_type   = "viewer-request"
        function_arn = aws_cloudfront_function.api_rewrite.arn
      }

      viewer_protocol_policy = "redirect-to-https"
      min_ttl                = 0
      default_ttl            = 0
      max_ttl                = 0
      compress               = true
    }
  }

  # SPA routing - return index.html for all 404s
  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
    # For custom domain, use:
    # acm_certificate_arn      = var.acm_certificate_arn
    # ssl_support_method       = "sni-only"
    # minimum_protocol_version = "TLSv1.2_2021"
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-ui-cdn-${var.environment}"
  })
}
*/

# S3 bucket policy to allow public read access for website hosting
resource "aws_s3_bucket_policy" "ui" {
  bucket = aws_s3_bucket.ui.id

  depends_on = [aws_s3_bucket_public_access_block.ui]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.ui.arn}/*"
      }
    ]
  })
}

# Outputs
output "ui_bucket_name" {
  description = "Name of the S3 bucket for UI files"
  value       = aws_s3_bucket.ui.id
}

output "ui_bucket_arn" {
  description = "ARN of the S3 bucket for UI files"
  value       = aws_s3_bucket.ui.arn
}

# CloudFront outputs (disabled until account verification)
# output "cloudfront_distribution_id" {
#   description = "ID of the CloudFront distribution"
#   value       = aws_cloudfront_distribution.ui.id
# }

# output "cloudfront_distribution_domain" {
#   description = "Domain name of the CloudFront distribution"
#   value       = aws_cloudfront_distribution.ui.domain_name
# }

output "ui_url" {
  description = "URL to access the UI (S3 website)"
  value       = "http://${aws_s3_bucket_website_configuration.ui.website_endpoint}"
}

# CloudFront URL (when available)
# output "ui_url_cloudfront" {
#   description = "URL to access the UI via CloudFront"
#   value       = "https://${aws_cloudfront_distribution.ui.domain_name}"
# }
