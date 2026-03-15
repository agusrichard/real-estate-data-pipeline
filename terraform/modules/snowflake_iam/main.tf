resource "aws_iam_role" "snowflake_s3_access" {
  name = "snowflake-s3-access-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { AWS = var.snowflake_iam_user_arn }
      Action    = "sts:AssumeRole"
      Condition = {
        StringEquals = {
          "sts:ExternalId" = var.snowflake_external_id
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "snowflake_s3_read" {
  name = "snowflake-s3-read"
  role = aws_iam_role.snowflake_s3_access.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["s3:GetObject", "s3:ListBucket"]
      Resource = [
        var.bucket_arn,
        "${var.bucket_arn}/staging/*"
      ]
    }]
  })
}

resource "aws_secretsmanager_secret" "snowflake_credentials" {
  name        = "real-estate-pipeline/snowflake"
  description = "Snowflake credentials for the pipeline service account"
}
