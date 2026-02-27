# Phase 1 — Step 1: Project Setup & Terraform Foundation

**Objective:** Set up the repository structure, write Terraform for core AWS resources, and verify everything provisions correctly.

---

## What You'll Build

By the end of this step you'll have:
- A clean folder structure committed to Git
- A `pyproject.toml` declaring project dependencies
- Terraform code organized into modules that provisions an S3 bucket and IAM roles
- A working `terraform apply` that you can verify in the AWS Console

---

## Task Breakdown

### 1. Initialize the Git Repository Folder Structure

The README defines the intended folder layout. Create the directories now (even if they're empty) so the structure is visible from the start. Git doesn't track empty folders, so add a `.gitkeep` placeholder inside each empty directory.

Folders to create:
```
lambdas/ingest_kaggle/
lambdas/ingest_rentcast/
lambdas/transform/
terraform/modules/s3/
terraform/modules/iam/
terraform/environments/
tests/
airflow/dags/
snowflake/schemas/
snowflake/queries/
docs/
```

**Why now?** Establishing the structure early makes every future task easier to place. It also signals intent to anyone reading the repo.

---

### 2. Create `pyproject.toml`

This is the standard Python project configuration file (replaces `setup.py` + `requirements.txt`). It declares your dependencies and tooling in one place.

Key dependencies to include:
- `polars` — the DataFrame library used for transformation
- `boto3` — AWS SDK for Python (used inside Lambdas to read/write S3)
- `requests` — HTTP client for the RentCast API
- `pytest` — test runner

Dev dependencies (not bundled into Lambda):
- `ruff` — linter and formatter
- `mypy` — type checker

**Why `pyproject.toml` over `requirements.txt`?** It separates runtime dependencies from dev dependencies, and tools like `ruff` and `mypy` can read their config from it too — fewer config files overall.

---

### 3. Write Terraform for the S3 Bucket (`modules/s3/`)

This module provisions the single S3 bucket that the entire pipeline uses, with the correct folder "prefixes" (S3 doesn't have real folders — prefixes are just naming conventions).

Folder structure to represent via prefix convention:
```
raw/kaggle/
raw/rentcast/
staging/kaggle/
staging/rentcast/
errors/
```

Two important S3 features to configure:

**Versioning** — keeps previous versions of every object. If a bad file overwrites a good one, you can recover the old version. Enable it on the bucket.

**Lifecycle rules** — automatically expire (delete) old objects after a set number of days to control storage costs. The plan calls for expiring raw files after 90 days.

Your `modules/s3/` should contain:
- `main.tf` — the `aws_s3_bucket`, `aws_s3_bucket_versioning`, and `aws_s3_bucket_lifecycle_configuration` resources
- `variables.tf` — input variables (bucket name, expiration days)
- `outputs.tf` — output the bucket name and ARN (other modules will need these)

---

### 4. Write Terraform for IAM Roles (`modules/iam/`)

Lambda functions need permission to do things in AWS. IAM roles define those permissions. You need:

**Lambda execution role** — the identity the Lambda function assumes when it runs. It needs:
- `s3:GetObject`, `s3:PutObject` on the pipeline bucket (read raw data, write results)
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` — so Lambda can write to CloudWatch

How IAM works in Terraform:
1. `aws_iam_role` — creates the role with a *trust policy* (says "Lambda is allowed to assume this role")
2. `aws_iam_policy` — defines the permissions document (what the role can do)
3. `aws_iam_role_policy_attachment` — attaches the policy to the role

Your `modules/iam/` should contain:
- `main.tf` — the three resources above
- `variables.tf` — input variables (bucket ARN, role name)
- `outputs.tf` — output the role ARN (needed when creating the Lambda in Step 2)

---

### 5. Configure the Terraform Backend and AWS Provider

In the root `terraform/` directory, you need two files:

**`provider.tf`** — tells Terraform which cloud to talk to:
```hcl
provider "aws" {
  region = var.aws_region
}
```

**`backend.tf`** — tells Terraform where to store state. Reference the S3 bucket and DynamoDB table you created manually in Phase 0:
```hcl
terraform {
  backend "s3" {
    bucket         = "my-real-estate-tf-state"
    key            = "dev/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-state-lock"
    encrypt        = true
  }
}
```

**Why `encrypt = true`?** State files can contain sensitive values (like resource IDs and ARNs). Enabling encryption at rest is a free, low-effort security improvement.

---

### 6. Create `environments/dev.tfvars`

This file holds variable values specific to the dev environment (bucket name, region, etc.). It keeps your `main.tf` generic and reusable.

Example:
```hcl
aws_region  = "us-east-1"
bucket_name = "my-real-estate-pipeline-dev"
```

**Do not commit real secrets here.** Anything sensitive (API keys, passwords) goes in AWS Secrets Manager later, not in `.tfvars`.

---

### 7. Run `terraform plan` and `terraform apply`

```bash
cd terraform/
terraform init                          # downloads providers, configures backend
terraform plan -var-file=environments/dev.tfvars   # preview changes
terraform apply -var-file=environments/dev.tfvars  # provision resources
```

**`terraform init`** — must be run first. It downloads the AWS provider plugin and connects to the S3 backend. Safe to re-run anytime.

**`terraform plan`** — shows you exactly what will be created, modified, or destroyed. Read this output carefully before applying. Nothing in AWS is changed yet.

**`terraform apply`** — actually creates the resources. Terraform will ask for confirmation. Type `yes`.

After apply, log into the AWS Console → S3 and confirm the bucket exists.

---

### 8. Commit

```
feat: project skeleton and core AWS infrastructure
```

Stage everything: the folder structure, `pyproject.toml`, and all `terraform/` files.

---

## Checkpoint

You should be able to:
- Run `terraform apply` cleanly with no errors
- See the S3 bucket in the AWS Console with versioning enabled
- See the IAM role in the AWS Console under IAM → Roles
- Run `terraform destroy` to tear it all down (optional, but confirms Terraform fully manages the resources)
