#!/bin/bash
# Test Coverage Guardian Hook
# Ensures test coverage doesn't regress

COMMAND="$1"
RESULT="$2"

# Only check after test runs
if [[ ! "$COMMAND" =~ "pytest" ]] && [[ ! "$COMMAND" =~ "invoke test" ]]; then
  exit 0
fi

# Extract coverage percentage from .coverage file or output
if [ -f ".coverage" ]; then
  # Use coverage report to get percentage
  CURRENT_COVERAGE=$(coverage report --precision=0 2>/dev/null | grep "^TOTAL" | awk '{print $NF}' | tr -d '%')
fi

# If still empty, try to extract from result output
if [ -z "$CURRENT_COVERAGE" ] && [ -n "$RESULT" ]; then
  CURRENT_COVERAGE=$(echo "$RESULT" | grep -oP 'TOTAL.*?(\d+)%' | grep -oP '\d+' | tail -1)
fi

if [ -z "$CURRENT_COVERAGE" ]; then
  # Coverage not found, skip check
  exit 0
fi

# Read minimum coverage threshold from file or default to 39%
MIN_COVERAGE_FILE=".min_coverage"
if [ -f "$MIN_COVERAGE_FILE" ]; then
  MIN_COVERAGE=$(cat "$MIN_COVERAGE_FILE")
else
  MIN_COVERAGE=39
fi

echo ""
echo "📊 Test Coverage Check"
echo "   Current: ${CURRENT_COVERAGE}%"
echo "   Minimum: ${MIN_COVERAGE}%"

if [ "$CURRENT_COVERAGE" -lt "$MIN_COVERAGE" ]; then
  echo ""
  echo "❌ ERROR: Test coverage decreased!"
  echo "   Coverage dropped from ${MIN_COVERAGE}% to ${CURRENT_COVERAGE}%"
  echo "   Please add tests to maintain or improve coverage"
  echo ""
  exit 1
fi

if [ "$CURRENT_COVERAGE" -gt "$MIN_COVERAGE" ]; then
  echo "   ✨ Coverage improved! Updating minimum threshold to ${CURRENT_COVERAGE}%"
  echo "$CURRENT_COVERAGE" > "$MIN_COVERAGE_FILE"
fi

echo "✅ Coverage check passed!"
exit 0
