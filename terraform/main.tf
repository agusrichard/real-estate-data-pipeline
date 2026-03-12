resource "aws_secretsmanager_secret" "rentcast_api_key" {
  name        = "rentcast/api-key"
  description = "RentCast API key for the ingest-rentcast Lambda. Populate the value manually after apply."
}

resource "aws_sns_topic" "pipeline_alerts" {
  name = "real-estate-pipeline-alerts"
}

# IAM role that Snowflake will assume to read from S3.
# Uses a placeholder trust policy (Deny all) to break the circular dependency with
# the Snowflake storage integration. The null_resource below updates the trust
# policy after the storage integration outputs are known.
resource "aws_iam_role" "snowflake_s3" {
  name = "snowflake-s3-access-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Deny"
      Principal = { AWS = "*" }
      Action    = "sts:AssumeRole"
    }]
  })

  lifecycle {
    ignore_changes = [assume_role_policy]
  }
}

# Updates the IAM role trust policy after the storage integration is created,
# wiring in the real Snowflake IAM user ARN and external ID.
resource "null_resource" "snowflake_trust_policy" {
  depends_on = [module.snowflake]

  triggers = {
    iam_user_arn = module.snowflake.storage_aws_iam_user_arn
    external_id  = module.snowflake.storage_aws_external_id
  }

  provisioner "local-exec" {
    command = <<-EOF
      aws iam update-assume-role-policy \
        --role-name snowflake-s3-access-role \
        --policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"AWS\":\"${module.snowflake.storage_aws_iam_user_arn}\"},\"Action\":\"sts:AssumeRole\",\"Condition\":{\"StringEquals\":{\"sts:ExternalId\":\"${module.snowflake.storage_aws_external_id}\"}}}]}" \
        --profile ${var.aws_profile}
    EOF
  }
}

# S3 read policy — allows Snowflake to read files from the staging prefix
resource "aws_iam_role_policy" "snowflake_s3_read" {
  name = "snowflake-s3-read"
  role = aws_iam_role.snowflake_s3.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["s3:GetObject", "s3:ListBucket"]
      Resource = [
        module.s3.bucket_arn,
        "${module.s3.bucket_arn}/staging/*"
      ]
    }]
  })
}

module "s3" {
  source      = "./modules/s3"
  bucket_name = var.bucket_name
}

module "iam" {
  source     = "./modules/iam"
  bucket_arn = module.s3.bucket_arn
  role_name  = "real-estate-lambda-role"
  secret_arn = aws_secretsmanager_secret.rentcast_api_key.arn
}

module "ingest_kaggle_lambda" {
  source        = "./modules/lambda"
  function_name = "ingest-kaggle"
  role_arn      = module.iam.lambda_role_arn
  zip_path      = "../lambdas/ingest_kaggle/lambda.zip"
  timeout       = 300
  memory_size   = 2048
  sns_topic_arn = aws_sns_topic.pipeline_alerts.arn
  environment_variables = {
    BUCKET_NAME = module.s3.bucket_name
    SOURCE_KEY  = "raw/kaggle/source/realtor-data.csv"
  }
}

module "ingest_rentcast_lambda" {
  source        = "./modules/lambda"
  function_name = "ingest-rentcast"
  role_arn      = module.iam.lambda_role_arn
  zip_path      = "../lambdas/ingest_rentcast/lambda.zip"
  timeout       = 300
  memory_size   = 512
  sns_topic_arn = aws_sns_topic.pipeline_alerts.arn
  environment_variables = {
    BUCKET_NAME        = module.s3.bucket_name
    RENTCAST_SECRET_ID = aws_secretsmanager_secret.rentcast_api_key.name
    TARGET_STATES      = "Alabama,Texas,Florida"
  }
}

module "snowflake" {
  source                 = "./modules/snowflake"
  bucket_name            = var.bucket_name
  snowflake_iam_role_arn = aws_iam_role.snowflake_s3.arn
}

# Snowflake credentials secret — read by the load Lambda at runtime
resource "aws_secretsmanager_secret" "snowflake_creds" {
  name                    = "real-estate-pipeline/snowflake"
  description             = "Snowflake credentials for the pipeline service account"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "snowflake_creds" {
  secret_id = aws_secretsmanager_secret.snowflake_creds.id
  secret_string = jsonencode({
    account      = var.snowflake_account
    organization = var.snowflake_organization
    username     = "pipeline_user"
    password     = var.snowflake_pipeline_password
  })
}

# Allow the Lambda execution role to read the Snowflake secret
resource "aws_iam_role_policy" "lambda_snowflake_secret" {
  name = "lambda-read-snowflake-secret"
  role = module.iam.lambda_role_name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = aws_secretsmanager_secret.snowflake_creds.arn
    }]
  })
}
