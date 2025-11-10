#!/bin/bash
# Pre-commit quality check hook
# Runs quality checks before git commits

COMMAND="$1"

# Only check git commit commands
if [[ ! "$COMMAND" =~ "git commit" ]]; then
  exit 0
fi

echo "🔍 Running pre-commit quality checks..."
echo ""

# Run quality checks (format, lint, typecheck)
invoke quality --fix

if [ $? -ne 0 ]; then
  echo ""
  echo "❌ Quality checks failed!"
  echo ""
  echo "Options:"
  echo "  1. Fix the issues above and retry"
  echo "  2. Run 'invoke quality --fix' to auto-fix"
  echo "  3. Skip this check (not recommended)"
  exit 1
fi

echo ""
echo "✅ All quality checks passed!"
exit 0
