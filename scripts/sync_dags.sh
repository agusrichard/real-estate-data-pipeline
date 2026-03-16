#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/sync_dags.sh
# Syncs DAGs and requirements.txt to the MWAA S3 bucket.

TERRAFORM_DIR="$(dirname "$(dirname "$0")")/terraform"

echo "Fetching MWAA DAGs bucket name from Terraform..."
BUCKET_NAME=$(AWS_PROFILE=real-estate-dp terraform -chdir="$TERRAFORM_DIR" output -raw mwaa_dags_bucket)

if [ -z "$BUCKET_NAME" ]; then
  echo "Error: could not get MWAA DAGs bucket name from Terraform output"
  exit 1
fi

echo "Bucket: $BUCKET_NAME"

echo "Uploading requirements.txt..."
aws s3 cp airflow/requirements.txt "s3://$BUCKET_NAME/requirements.txt" --profile real-estate-dp

echo "Syncing DAGs..."
aws s3 sync airflow/dags/ "s3://$BUCKET_NAME/dags/" --profile real-estate-dp

echo "Done. DAGs and requirements synced to s3://$BUCKET_NAME"
