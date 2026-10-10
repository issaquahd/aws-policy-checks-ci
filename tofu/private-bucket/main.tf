# GOOD sample OpenTofu config: a private, encrypted bucket plus a read-only
# policy with explicit actions. CI runs `tofu fmt -check` and `tofu validate` here.

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-2"
}

variable "bucket_prefix" {
  description = "Prefix for the generated bucket name"
  type        = string
  default     = "policy-checks-demo-"
}

resource "aws_s3_bucket" "this" {
  bucket_prefix = var.bucket_prefix
}

resource "aws_s3_bucket_public_access_block" "this" {
  bucket                  = aws_s3_bucket.this.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

data "aws_iam_policy_document" "read" {
  statement {
    sid       = "ListBucket"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.this.arn]
  }

  statement {
    sid       = "ReadObjects"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.this.arn}/*"]
  }
}

resource "aws_iam_policy" "read" {
  name_prefix = "policy-checks-demo-read-"
  policy      = data.aws_iam_policy_document.read.json
}

output "bucket_name" {
  value = aws_s3_bucket.this.id
}
