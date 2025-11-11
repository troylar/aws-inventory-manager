#!/bin/bash
# Deployment Safety Hook
# Validates releases before publishing to PyPI

COMMAND="$1"

# Check for PyPI publish commands
if [[ ! "$COMMAND" =~ "gh release create" ]] && [[ ! "$COMMAND" =~ "pypi" ]]; then
  exit 0
fi

echo "🚨 DEPLOYMENT SAFETY CHECK"
echo ""

# 1. Check if on main branch
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [[ "$BRANCH" != "main" ]]; then
  echo "❌ ERROR: Not on main branch (current: $BRANCH)"
  echo "   Releases must be from main branch"
  exit 1
fi

# 2. Check for uncommitted changes
if [[ -n $(git status -s) ]]; then
  echo "❌ ERROR: Uncommitted changes detected"
  echo "   Commit all changes before releasing"
  git status -s
  exit 1
fi

# 3. Check if tests pass
echo "🧪 Running tests..."
invoke test
if [ $? -ne 0 ]; then
  echo "❌ ERROR: Tests failed"
  exit 1
fi

# 4. Check if version was bumped
VERSION=$(python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])" 2>/dev/null)
if [ -z "$VERSION" ]; then
  # Try older Python without tomllib
  VERSION=$(python -c "import toml; print(toml.load(open('pyproject.toml', 'r'))['project']['version'])" 2>/dev/null)
fi

LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "0.0.0")

if [[ "$VERSION" == "$LAST_TAG" ]] || [[ "v$VERSION" == "$LAST_TAG" ]]; then
  echo "❌ ERROR: Version not bumped"
  echo "   Current: $VERSION"
  echo "   Last tag: $LAST_TAG"
  echo "   Update version in pyproject.toml"
  exit 1
fi

# 5. Check CHANGELOG updated
if ! grep -q "$VERSION" CHANGELOG.md 2>/dev/null; then
  echo "⚠️  WARNING: Version $VERSION not found in CHANGELOG.md"
  echo "   Consider updating the changelog"
  echo ""
fi

echo ""
echo "✅ All deployment safety checks passed!"
echo "   Version: $VERSION"
echo "   Branch: $BRANCH"
echo "   Tests: PASSED"
echo ""
exit 0
