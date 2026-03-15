variable "bucket_arn" {
  type        = string
  description = "ARN of the S3 bucket Snowflake will read from"
}

variable "snowflake_iam_user_arn" {
  type        = string
  description = "STORAGE_AWS_IAM_USER_ARN from DESC INTEGRATION S3_INTEGRATION"
}

variable "snowflake_external_id" {
  type        = string
  description = "STORAGE_AWS_EXTERNAL_ID from DESC INTEGRATION S3_INTEGRATION"
}
