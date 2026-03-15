resource "aws_secretsmanager_secret" "rentcast_api_key" {
  name        = "rentcast/api-key"
  description = "RentCast API key for the ingest-rentcast Lambda. Populate the value manually after apply."
}

resource "aws_sns_topic" "pipeline_alerts" {
  name = "real-estate-pipeline-alerts"
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

module "transform_kaggle_lambda" {
  source        = "./modules/lambda"
  function_name = "transform-kaggle"
  role_arn      = module.iam.lambda_role_arn
  zip_path      = "../lambdas/transform_kaggle/lambda.zip"
  timeout       = 300
  memory_size   = 1024
  sns_topic_arn = aws_sns_topic.pipeline_alerts.arn
  environment_variables = {
    BUCKET_NAME = module.s3.bucket_name
  }
}

module "transform_rentcast_lambda" {
  source        = "./modules/lambda"
  function_name = "transform-rentcast"
  role_arn      = module.iam.lambda_role_arn
  zip_path      = "../lambdas/transform_rentcast/lambda.zip"
  timeout       = 300
  memory_size   = 1024
  sns_topic_arn = aws_sns_topic.pipeline_alerts.arn
  environment_variables = {
    BUCKET_NAME = module.s3.bucket_name
  }
}

module "load_lambda" {
  source        = "./modules/lambda"
  function_name = "load"
  role_arn      = module.iam.lambda_role_arn
  zip_path      = "../lambdas/load/lambda.zip"
  timeout       = 300
  memory_size   = 512
  sns_topic_arn = aws_sns_topic.pipeline_alerts.arn
  environment_variables = {
    BUCKET_NAME         = module.s3.bucket_name
    SNOWFLAKE_SECRET_ID = "real-estate-pipeline/snowflake"
  }
}

module "snowflake_iam" {
  source                 = "./modules/snowflake_iam"
  bucket_arn             = module.s3.bucket_arn
  snowflake_iam_user_arn = var.snowflake_iam_user_arn
  snowflake_external_id  = var.snowflake_external_id
}

resource "aws_iam_role_policy" "lambda_read_snowflake_secret" {
  name = "lambda-read-snowflake-secret"
  role = module.iam.lambda_role_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = module.snowflake_iam.secret_arn
    }]
  })
}
