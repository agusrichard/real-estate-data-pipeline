variable "bucket_name" {
  type        = string
  description = "S3 bucket name where staged Parquet files are stored"
}

variable "database_name" {
  type        = string
  description = "Name of the Snowflake database"
  default     = "REAL_ESTATE"
}

variable "snowflake_iam_role_arn" {
  type        = string
  description = "ARN of the AWS IAM role that Snowflake assumes to read from S3"
}
