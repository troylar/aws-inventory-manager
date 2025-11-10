#!/bin/bash
# AWS Profile Validation Hook
# Validates AWS profile before awsinv commands

COMMAND="$1"

# Only check awsinv commands
if [[ ! "$COMMAND" =~ awsinv ]]; then
  exit 0
fi

# Extract profile from command if specified
PROFILE=""
if [[ "$COMMAND" =~ --profile[[:space:]]+([^[:space:]]+) ]]; then
  PROFILE="${BASH_REMATCH[1]}"
else
  PROFILE="${AWS_PROFILE:-default}"
fi

# Get current AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --profile "$PROFILE" --query Account --output text 2>/dev/null)

if [ $? -ne 0 ]; then
  echo "❌ ERROR: Cannot validate AWS credentials for profile '$PROFILE'"
  echo "   Run: aws configure --profile $PROFILE"
  exit 1
fi

# Check if this is a destructive operation
DESTRUCTIVE_OPS=("delete" "restore" "cleanup")
IS_DESTRUCTIVE=false

for op in "${DESTRUCTIVE_OPS[@]}"; do
  if [[ "$COMMAND" =~ $op ]]; then
    IS_DESTRUCTIVE=true
    break
  fi
done

# Display account information
echo "🔍 AWS Account Validation"
echo "   Profile: $PROFILE"
echo "   Account: $ACCOUNT_ID"

# Warn on production accounts for destructive operations
# TODO: Replace with your actual production account IDs
PROD_ACCOUNTS=("123456789012" "999888777666")
if [[ "$IS_DESTRUCTIVE" == "true" ]]; then
  for prod_account in "${PROD_ACCOUNTS[@]}"; do
    if [[ "$ACCOUNT_ID" == "$prod_account" ]]; then
      echo ""
      echo "⚠️  WARNING: Destructive operation on PRODUCTION account!"
      echo "   Press Ctrl+C to cancel or wait 3 seconds to continue..."
      sleep 3
      break
    fi
  done
fi

echo "✅ AWS profile validated"
exit 0
