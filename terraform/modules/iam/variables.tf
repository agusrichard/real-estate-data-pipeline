variable "bucket_arn" {
  type        = string
  description = "ARN of the S3 bucket to grant Lambda access to"
}

variable "role_name" {
  type        = string
  description = "Name for the Lambda IAM role"
}

variable "secret_arn" {
  type        = string
  description = "ARN of the Secrets Manager secret the Lambda role is allowed to read"
}
