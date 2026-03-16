output "mwaa_webserver_url" {
  description = "URL of the MWAA Airflow web UI"
  value       = aws_mwaa_environment.this.webserver_url
}

output "mwaa_arn" {
  description = "ARN of the MWAA environment"
  value       = aws_mwaa_environment.this.arn
}

output "dags_bucket_name" {
  description = "Name of the S3 bucket for DAGs"
  value       = aws_s3_bucket.mwaa_dags.id
}

output "mwaa_execution_role_arn" {
  description = "ARN of the MWAA execution role"
  value       = aws_iam_role.mwaa_execution.arn
}
