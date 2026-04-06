variable "environment" { type = string }

resource "aws_s3_bucket" "mlflow_artifacts" {
  bucket = "neuralops-mlflow-${var.environment}-${data.aws_caller_identity.current.account_id}"
  tags   = { Project = "neuralops", Environment = var.environment, Purpose = "mlflow-artifacts" }
}

resource "aws_s3_bucket_versioning" "mlflow_artifacts" {
  bucket = aws_s3_bucket.mlflow_artifacts.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "mlflow_artifacts" {
  bucket = aws_s3_bucket.mlflow_artifacts.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "mlflow_artifacts" {
  bucket                  = aws_s3_bucket.mlflow_artifacts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

data "aws_caller_identity" "current" {}

output "bucket_name" { value = aws_s3_bucket.mlflow_artifacts.bucket }
output "bucket_arn"  { value = aws_s3_bucket.mlflow_artifacts.arn }
