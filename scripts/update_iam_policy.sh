#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/update_iam_policy.sh [--profile <profile>] <policy-name> <path-to-policy-json>
# Example: ./scripts/update_iam_policy.sh --profile my-profile real-estate-dp-tf-policy-cloudwatch iam-policies/policy-cloudwatch.json

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

echo "Looking up policy ARN for: $POLICY_NAME"
POLICY_ARN=$(aws "${AWS_OPTS[@]}" iam list-policies \
  --scope Local \
  --query "Policies[?PolicyName=='$POLICY_NAME'].Arn" \
  --output text)

if [ -z "$POLICY_ARN" ]; then
  echo "Error: policy '$POLICY_NAME' not found"
  exit 1
fi

# IAM allows max 5 versions per policy — delete the oldest non-default version if needed
VERSION_COUNT=$(aws "${AWS_OPTS[@]}" iam list-policy-versions \
  --policy-arn "$POLICY_ARN" \
  --query "length(Versions)" \
  --output text)

if [ "$VERSION_COUNT" -ge 5 ]; then
  echo "Max versions reached — deleting oldest non-default version"
  OLDEST_VERSION=$(aws "${AWS_OPTS[@]}" iam list-policy-versions \
    --policy-arn "$POLICY_ARN" \
    --query "Versions[?IsDefaultVersion==\`false\`] | [-1].VersionId" \
    --output text)
  aws "${AWS_OPTS[@]}" iam delete-policy-version \
    --policy-arn "$POLICY_ARN" \
    --version-id "$OLDEST_VERSION"
fi

echo "Creating new policy version for: $POLICY_ARN"
aws "${AWS_OPTS[@]}" iam create-policy-version \
  --policy-arn "$POLICY_ARN" \
  --policy-document "file://$POLICY_FILE" \
  --set-as-default

echo "Done: $POLICY_ARN updated"
