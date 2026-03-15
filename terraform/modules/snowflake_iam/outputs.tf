output "role_arn" {
  value = aws_iam_role.snowflake_s3_access.arn
}

output "secret_arn" {
  value = aws_secretsmanager_secret.snowflake_credentials.arn
}
