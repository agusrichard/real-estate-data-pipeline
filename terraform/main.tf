module "s3" {
  source      = "./modules/s3"
  bucket_name = var.bucket_name
}

module "iam" {
  source     = "./modules/iam"
  bucket_arn = module.s3.bucket_arn
  role_name  = "real-estate-lambda-role"
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