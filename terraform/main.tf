module "s3" {
  source      = "./modules/s3"
  bucket_name = var.bucket_name
}

resource "aws_secretsmanager_secret" "rentcast_api_key" {
  name        = "rentcast/api-key"
  description = "RentCast API key for the ingest-rentcast Lambda. Populate the value manually after apply."
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
  environment_variables = {
    BUCKET_NAME        = module.s3.bucket_name
    RENTCAST_SECRET_ID = aws_secretsmanager_secret.rentcast_api_key.name
    TARGET_STATES      = "AL,TX,FL"
  }
}