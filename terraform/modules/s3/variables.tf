variable "bucket_name" {
  type        = string
  description = "Globally unique name for the S3 bucket"
}

variable "expiration_days" {
  type        = number
  description = "Days before raw objects are expired"
  default     = 90
}