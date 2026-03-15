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

variable "snowflake_iam_user_arn" {
  type        = string
  description = "STORAGE_AWS_IAM_USER_ARN from Snowflake DESC INTEGRATION"
}

variable "snowflake_external_id" {
  type        = string
  description = "STORAGE_AWS_EXTERNAL_ID from Snowflake DESC INTEGRATION"
}
