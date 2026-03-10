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

module "snowflake" {
  source      = "./modules/snowflake"
  bucket_name = var.bucket_name
}
