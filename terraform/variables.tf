variable "aws_region" {
  type        = string
  description = "AWS region to deploy resources into"
}

variable "aws_profile" {
  type        = string
  description = "AWS CLI profile to use for local-exec provisioners"
  default     = "default"
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

variable "snowflake_pipeline_password" {
  type        = string
  sensitive   = true
  description = "Password for pipeline_user — stored in Secrets Manager for Lambda use"
}

