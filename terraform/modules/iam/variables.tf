variable "bucket_arn" {
  type        = string
  description = "ARN of the S3 bucket to grant Lambda access to"
}

variable "role_name" {
  type        = string
  description = "Name for the Lambda IAM role"
}
