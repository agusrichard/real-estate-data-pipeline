variable "aws_region" {
  type        = string
  description = "AWS region to deploy resources into"
}

variable "bucket_name" {
  type        = string
  description = "Name for the S3 pipeline bucket"
}

variable "snowflake_organization" { type = string }
variable "snowflake_account" { type = string }
variable "snowflake_username" { type = string }
variable "snowflake_password" {
  type      = string
  sensitive = true
}

