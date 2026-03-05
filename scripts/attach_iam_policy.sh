#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/attach_iam_policy.sh [--profile <profile>] <policy-name> <path-to-policy-json>
# Example: ./scripts/attach_iam_policy.sh --profile my-profile real-estate-dp-tf-policy-sns iam-policies/policy-sns.json

IAM_USER="real-estate-dp-tf"

AWS_OPTS=()
if [ "${1:-}" = "--profile" ]; then
  AWS_OPTS=(--profile "$2")
  shift 2
fi

if [ $# -ne 2 ]; then
  echo "Usage: $0 [--profile <profile>] <policy-name> <path-to-policy-json>"
  exit 1
fi

POLICY_NAME="$1"
POLICY_FILE="$2"

if [ ! -f "$POLICY_FILE" ]; then
  echo "Error: policy file '$POLICY_FILE' does not exist"
  exit 1
fi

echo "Creating policy: $POLICY_NAME"
POLICY_ARN=$(aws "${AWS_OPTS[@]}" iam create-policy \
  --policy-name "$POLICY_NAME" \
  --policy-document "file://$POLICY_FILE" \
  --query "Policy.Arn" \
  --output text)

echo "Attaching policy to user: $IAM_USER"
aws "${AWS_OPTS[@]}" iam attach-user-policy \
  --user-name "$IAM_USER" \
  --policy-arn "$POLICY_ARN"

echo "Done: $POLICY_ARN attached to $IAM_USER"
