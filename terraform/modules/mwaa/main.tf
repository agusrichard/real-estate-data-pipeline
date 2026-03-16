resource "aws_vpc" "mwaa" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = merge(var.tags, { Name = "${var.environment_name}-mwaa-vpc" })
}

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.mwaa.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone = data.aws_availability_zones.available.names[count.index]
  tags              = merge(var.tags, { Name = "${var.environment_name}-private-${count.index}" })
}

resource "aws_subnet" "public" {
  vpc_id            = aws_vpc.mwaa.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, 2)
  availability_zone = data.aws_availability_zones.available.names[0]
  tags              = merge(var.tags, { Name = "${var.environment_name}-public" })
}

resource "aws_internet_gateway" "mwaa" {
  vpc_id = aws_vpc.mwaa.id
  tags   = merge(var.tags, { Name = "${var.environment_name}-igw" })
}

resource "aws_eip" "nat" {
  domain = "vpc"
  tags   = merge(var.tags, { Name = "${var.environment_name}-nat-eip" })
}

resource "aws_nat_gateway" "mwaa" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public.id
  tags          = merge(var.tags, { Name = "${var.environment_name}-nat" })
  depends_on    = [aws_internet_gateway.mwaa]
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.mwaa.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.mwaa.id
  }
  tags = merge(var.tags, { Name = "${var.environment_name}-private-rt" })
}

resource "aws_route_table_association" "private" {
  count          = 2
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.mwaa.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.mwaa.id
  }
  tags = merge(var.tags, { Name = "${var.environment_name}-public-rt" })
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "mwaa" {
  vpc_id      = aws_vpc.mwaa.id
  name        = "${var.environment_name}-mwaa-sg"
  description = "Security group for MWAA environment"

  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.environment_name}-mwaa-sg" })
}

resource "aws_s3_bucket" "mwaa_dags" {
  bucket = "${var.environment_name}-mwaa-dags"
  tags   = var.tags
}

resource "aws_s3_bucket_versioning" "mwaa_dags" {
  bucket = aws_s3_bucket.mwaa_dags.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "mwaa_dags" {
  bucket                  = aws_s3_bucket.mwaa_dags.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_iam_role" "mwaa_execution" {
  name = "${var.environment_name}-mwaa-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = ["airflow.amazonaws.com", "airflow-env.amazonaws.com"] }
        Action    = "sts:AssumeRole"
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "mwaa_execution" {
  name = "${var.environment_name}-mwaa-execution-policy"
  role = aws_iam_role.mwaa_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:GetObject*", "s3:PutObject*", "s3:ListBucket", "s3:GetBucketLocation"]
        Resource = [
          aws_s3_bucket.mwaa_dags.arn,
          "${aws_s3_bucket.mwaa_dags.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = ["lambda:InvokeFunction"]
        Resource = [
          "arn:aws:lambda:*:*:function:ingest-*",
          "arn:aws:lambda:*:*:function:transform-*",
          "arn:aws:lambda:*:*:function:load"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream", "logs:CreateLogGroup",
          "logs:PutLogEvents", "logs:GetLogEvents",
          "logs:GetLogRecord", "logs:GetLogGroupFields",
          "logs:GetQueryResults", "logs:DescribeLogGroups"
        ]
        Resource = "arn:aws:logs:*:*:log-group:airflow-*"
      },
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = "arn:aws:secretsmanager:*:*:secret:airflow/*"
      },
      {
        Effect   = "Allow"
        Action   = ["airflow:PublishMetrics"]
        Resource = "arn:aws:airflow:*:*:environment/${var.environment_name}"
      },
      {
        Effect   = "Allow"
        Action   = ["sqs:*"]
        Resource = "arn:aws:sqs:*:*:airflow-celery-*"
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt", "kms:DescribeKey", "kms:GenerateDataKey*", "kms:Encrypt"
        ]
        Resource = "*"
        Condition = {
          StringLike = { "kms:ViaService" = "sqs.*.amazonaws.com" }
        }
      }
    ]
  })
}

resource "aws_mwaa_environment" "this" {
  name               = var.environment_name
  airflow_version    = var.airflow_version
  environment_class  = var.environment_class
  max_workers        = var.max_workers
  execution_role_arn = aws_iam_role.mwaa_execution.arn

  source_bucket_arn    = aws_s3_bucket.mwaa_dags.arn
  dag_s3_path          = "dags/"
  requirements_s3_path = "requirements.txt"

  webserver_access_mode = "PUBLIC_ONLY"

  network_configuration {
    security_group_ids = [aws_security_group.mwaa.id]
    subnet_ids         = aws_subnet.private[*].id
  }

  logging_configuration {
    dag_processing_logs {
      enabled   = true
      log_level = "INFO"
    }
    scheduler_logs {
      enabled   = true
      log_level = "INFO"
    }
    task_logs {
      enabled   = true
      log_level = "INFO"
    }
    webserver_logs {
      enabled   = true
      log_level = "INFO"
    }
    worker_logs {
      enabled   = true
      log_level = "INFO"
    }
  }

  airflow_configuration_options = {
    "core.default_timezone" = "UTC"
  }

  tags = var.tags
}
