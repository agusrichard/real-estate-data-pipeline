#!/usr/bin/env bash
set -euo pipefail

# Usage: ./package_lambda.sh <path-to-lambda-folder>
# Example: ./package_lambda.sh lambdas/ingest_rentcast

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
pip install -r "$LAMBDA_DIR/requirements.txt" --target "$PACKAGE_DIR" --quiet

echo "Copying handler..."
cp "$LAMBDA_DIR/handler.py" "$PACKAGE_DIR/handler.py"

echo "Creating zip..."
cd "$PACKAGE_DIR"
zip -r "../lambda.zip" . --quiet
cd - > /dev/null

echo "Done: $ZIP_PATH ($(du -sh "$ZIP_PATH" | cut -f1))"
