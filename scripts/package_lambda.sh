#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/package_lambda.sh <path-to-lambda-folder>
# Example: ./scripts/package_lambda.sh lambdas/ingest_rentcast

if [ $# -ne 1 ]; then
  echo "Usage: $0 <path-to-lambda-folder>"
  exit 1
fi

LAMBDA_DIR="$1"

if [ ! -d "$LAMBDA_DIR" ]; then
  echo "Error: directory '$LAMBDA_DIR' does not exist"
  exit 1
fi

if [ ! -f "$LAMBDA_DIR/handler.py" ]; then
  echo "Error: '$LAMBDA_DIR/handler.py' not found"
  exit 1
fi

if [ ! -f "$LAMBDA_DIR/requirements.txt" ]; then
  echo "Error: '$LAMBDA_DIR/requirements.txt' not found"
  exit 1
fi

PACKAGE_DIR="$LAMBDA_DIR/package"
ZIP_PATH="$LAMBDA_DIR/lambda.zip"

echo "Packaging Lambda in: $LAMBDA_DIR"

echo "Cleaning previous build..."
rm -rf "$PACKAGE_DIR" "$ZIP_PATH"

echo "Installing dependencies..."
.venv/bin/pip3 install \
  -r "$LAMBDA_DIR/requirements.txt" \
  --target "$PACKAGE_DIR" \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 3.12 \
  --only-binary=:all: \
  --quiet

echo "Copying lambda source files..."
cp "$LAMBDA_DIR"/*.py "$PACKAGE_DIR/"

COMMON_DIR="$(dirname "$LAMBDA_DIR")/common"
if [ -d "$COMMON_DIR" ]; then
  echo "Copying common module..."
  cp -r "$COMMON_DIR" "$PACKAGE_DIR/common"
fi

echo "Creating zip..."
cd "$PACKAGE_DIR"
zip -r "../lambda.zip" . --quiet
cd - > /dev/null

echo "Done: $ZIP_PATH ($(du -sh "$ZIP_PATH" | cut -f1))"

LAMBDA_NAME=$(basename "$LAMBDA_DIR")
MODULE_NAME="${LAMBDA_NAME}_lambda"
TERRAFORM_DIR="$(dirname "$(dirname "$LAMBDA_DIR")")/terraform"

echo "Applying Terraform for module.$MODULE_NAME..."
AWS_PROFILE=real-estate-dp terraform -chdir="$TERRAFORM_DIR" apply \
  -var-file="environments/dev.tfvars" \
  -target="module.$MODULE_NAME" \
  -auto-approve
