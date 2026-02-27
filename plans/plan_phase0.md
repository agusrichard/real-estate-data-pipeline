# Phase 0: AWS Prerequisites (Before Any Code)

Complete these steps once before starting Phase 1. They cannot be done with Terraform — they must exist first.

### Pre-step 1: AWS Account & CLI

- Make sure you have an AWS account and the AWS CLI installed:
  ```bash
  brew install awscli
  ```
- Run `aws configure` and enter your access key, secret, default region, and output format
- Verify it works:
  ```bash
  aws sts get-caller-identity  # should print your account ID
  ```

### Pre-step 2: Create an IAM User for Terraform

- In the AWS Console, create a user named `terraform-deployer`
- Attach `AdministratorAccess` for now (can be scoped down later)
- Generate access keys and re-run `aws configure` with those credentials

### Pre-step 3: Manually Create the Terraform State Backend Resources

These two resources must exist before `terraform init` — Terraform cannot create its own backend.

```bash
# S3 bucket for state (pick a globally unique name)
aws s3api create-bucket \
  --bucket my-real-estate-tf-state \
  --region us-east-1

# Enable versioning (lets you recover from bad state)
aws s3api put-bucket-versioning \
  --bucket my-real-estate-tf-state \
  --versioning-configuration Status=Enabled

# DynamoDB table for state locking (prevents concurrent applies)
aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### Pre-step 4: Install Terraform

```bash
brew tap hashicorp/tap
brew install hashicorp/tap/terraform
terraform -version  # verify
```

**Checkpoint:** `aws sts get-caller-identity` returns your account ID, and `terraform -version` prints a version number.
