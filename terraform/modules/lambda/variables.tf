variable "function_name" {
  type = string
}

variable "handler" {
  type    = string
  default = "handler.lambda_handler"
}

variable "runtime" {
  type    = string
  default = "python3.12"
}

variable "timeout" {
  type    = number
  default = 300
}

variable "memory_size" {
  type    = number
  default = 512
}

variable "role_arn" {
  type = string
}

variable "zip_path" {
  type = string
}

variable "environment_variables" {
  type    = map(string)
  default = {}
}

variable "sns_topic_arn" {
  type = string
}
