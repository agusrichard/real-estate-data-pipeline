variable "aws_region" {
  type        = string
  description = "AWS region to deploy resources into"
}

variable "bucket_name" {
  type        = string
  description = "Name for the S3 pipeline bucket"
}