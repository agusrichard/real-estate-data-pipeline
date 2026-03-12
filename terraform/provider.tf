terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }

    snowflake = {
      source  = "snowflakedb/snowflake"
      version = "~> 1.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

provider "snowflake" {
  organization_name = var.snowflake_organization
  account_name      = var.snowflake_account
  user              = var.snowflake_username
  password          = var.snowflake_password
  role              = "ACCOUNTADMIN"
  preview_features_enabled = ["snowflake_storage_integration_resource", "snowflake_stage_resource"]
}
