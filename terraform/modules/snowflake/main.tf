terraform {
  required_providers {
    snowflake = {
      source  = "snowflakedb/snowflake"
      version = "~> 1.0"
    }
  }
}

resource "snowflake_database" "real_estate" {
  name = var.database_name
}

resource "snowflake_schema" "staging" {
  database = snowflake_database.real_estate.name
  name     = "STAGING"
}

resource "snowflake_schema" "analytics" {
  database = snowflake_database.real_estate.name
  name     = "ANALYTICS"
}

resource "snowflake_warehouse" "transform_wh" {
  name           = "TRANSFORM_WH"
  warehouse_size = "XSMALL"
  auto_suspend   = 60
  auto_resume    = true
}

resource "snowflake_account_role" "pipeline_role" {
  name = "PIPELINE_ROLE"
}

resource "snowflake_grant_privileges_to_account_role" "warehouse_usage" {
  account_role_name = snowflake_account_role.pipeline_role.name
  privileges = ["USAGE"]

  on_account_object {
    object_type = "WAREHOUSE"
    object_name = snowflake_warehouse.transform_wh.name
  }
}

resource "snowflake_grant_privileges_to_account_role" "database_usage" {
  account_role_name = snowflake_account_role.pipeline_role.name
  privileges = ["USAGE", "CREATE SCHEMA"]

  on_account_object {
    object_type = "DATABASE"
    object_name = snowflake_database.real_estate.name
  }
}

resource "snowflake_grant_privileges_to_account_role" "schema_privileges" {
  for_each          = toset(["STAGING", "ANALYTICS"])
  account_role_name = snowflake_account_role.pipeline_role.name
  privileges        = ["USAGE", "CREATE TABLE", "CREATE STAGE", "CREATE SEQUENCE"]

  depends_on = [
    snowflake_schema.staging,
    snowflake_schema.analytics,
  ]

  on_schema {
    schema_name = "\"${var.database_name}\".\"${each.value}\""
  }
}

resource "snowflake_user" "pipeline_user" {
  name              = "pipeline_user"
  default_role      = snowflake_account_role.pipeline_role.name
  default_warehouse = snowflake_warehouse.transform_wh.name
}

resource "snowflake_grant_account_role" "pipeline_user_role" {
  role_name = snowflake_account_role.pipeline_role.name
  user_name = snowflake_user.pipeline_user.name
}

resource "snowflake_storage_integration" "s3_integration" {
  name    = "S3_INTEGRATION"
  type    = "EXTERNAL_STAGE"
  enabled = true

  storage_provider          = "S3"
  storage_aws_role_arn      = var.snowflake_iam_role_arn
  storage_allowed_locations = ["s3://${var.bucket_name}/staging/"]
}

# External stage — named pointer to the S3 staging prefix
resource "snowflake_stage" "s3_stage" {
  name                = "S3_STAGE"
  database            = snowflake_database.real_estate.name
  schema              = snowflake_schema.staging.name
  storage_integration = snowflake_storage_integration.s3_integration.name
  url                 = "s3://${var.bucket_name}/staging/"

  file_format = "TYPE = PARQUET"
}
