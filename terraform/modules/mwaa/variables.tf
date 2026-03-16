variable "environment_name" {
  description = "Name for the MWAA environment"
  type        = string
  default     = "real-estate-pipeline"
}

variable "airflow_version" {
  description = "Apache Airflow version"
  type        = string
  default     = "3.0.6"
}

variable "environment_class" {
  description = "MWAA environment class (mw1.small, mw1.medium, mw1.large)"
  type        = string
  default     = "mw1.small"
}

variable "max_workers" {
  description = "Maximum number of workers"
  type        = number
  default     = 2
}

variable "vpc_cidr" {
  description = "CIDR block for the MWAA VPC"
  type        = string
  default     = "10.1.0.0/16"
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
