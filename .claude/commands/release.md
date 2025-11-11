# Release Workflow

Automate the complete release process for aws-inventory-manager.

## Task

Guide the user through creating and publishing a new release of the aws-inventory-manager package.

## Steps

### 1. Pre-Release Checks

- **Confirm user wants to create a release**
- **Ask for version number** (e.g., 0.4.0, 1.0.0)
  - Show current version from pyproject.toml
  - Suggest next version based on semantic versioning
  - Ask release type: major (breaking), minor (features), or patch (bugfixes)
- **Verify on main branch:**
  ```bash
  git rev-parse --abbrev-ref HEAD
  ```
  - If not on main, ask user to switch to main first
- **Check for uncommitted changes:**
  ```bash
  git status -s
  ```
  - If uncommitted changes exist, ask user to commit or stash first
- **Run full test suite:**
  ```bash
  invoke ci
  ```
  - This runs quality checks and all tests
  - If tests fail, STOP and ask user to fix tests first

### 2. Version Bumping

- **Read current pyproject.toml**
- **Update version** in pyproject.toml from current to new version
- **Show diff** to user for confirmation
- **Ask user to confirm** the change

### 3. Changelog Update

- **Read current CHANGELOG.md**
- **Ask user for notable changes** in this release:
  - New features added
  - Bugs fixed
  - Breaking changes (if any)
  - Other notable changes
- **Generate new changelog section** with format:
  ```markdown
  ## [X.Y.Z] - YYYY-MM-DD

  ### Added
  - New feature 1
  - New feature 2

  ### Fixed
  - Bug fix 1
  - Bug fix 2

  ### Changed
  - Breaking change 1 (if any)

  ### Deprecated
  - Deprecated feature (if any)
  ```
- **Insert at top** of CHANGELOG.md (after title, before previous versions)
- **Show diff** for approval

### 4. Commit Changes

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "chore: bump version to <version>"
```

### 5. Create Git Tag

```bash
git tag -a v<version> -m "Release v<version>"
```

### 6. Push to GitHub

```bash
git push origin main
git push origin v<version>
```

### 7. Create GitHub Release

- Extract changelog notes for this version from CHANGELOG.md
- Create GitHub release:
  ```bash
  gh release create v<version> \
    --title "v<version>" \
    --notes "<changelog-content-for-this-version>"
  ```

### 8. Build Package

```bash
invoke clean
invoke build
```

### 9. Verify Build

```bash
ls -lh dist/
twine check dist/*
```

- Show user the built artifacts
- Verify twine check passes

### 10. Publish to PyPI

**Ask user:** "Publish to Test PyPI first for validation? (recommended)"

**If yes:**
```bash
python -m twine upload --repository testpypi dist/*
```

Then ask: "Test PyPI upload successful. Publish to production PyPI?"

**If yes:**
```bash
python -m twine upload dist/*
```

**Note:** User needs PyPI API token configured in ~/.pypirc

### 11. Verification

- Check PyPI page: https://pypi.org/project/aws-inventory-manager/
- Verify version shows correctly
- Suggest testing installation:
  ```bash
  pip install --upgrade aws-inventory-manager==<version>
  awsinv --version
  ```

### 12. Post-Release Summary

Generate summary:
```
✅ Release v<version> Complete!

📦 PyPI: https://pypi.org/project/aws-inventory-manager/<version>/
🏷️  GitHub: https://github.com/troylar/aws-inventory-manager/releases/tag/v<version>
🎯 Git Tag: v<version>

📋 Released Changes:
<changelog-content>

✨ Next Steps:
- Announce release on social media
- Update documentation if needed
- Close related GitHub issues
- Consider creating announcement on GitHub Discussions
```

## Safety Checks

- **NEVER publish without running tests** - tests must pass via `invoke ci`
- **NEVER skip version bump** - version must be incremented
- **ALWAYS show diffs** before committing changes
- **ALWAYS ask for confirmation** before:
  - Committing changes
  - Pushing to GitHub
  - Publishing to PyPI
- **RECOMMEND Test PyPI** before production publish
- **VERIFY build artifacts** with twine check before uploading

## Error Handling

- If any step fails, STOP and report error to user
- Provide guidance on how to fix common errors
- Allow user to retry failed steps
- Never continue if tests fail

## Prerequisites

User should have:
- PyPI account and API token configured
- GitHub CLI (`gh`) installed and authenticated
- Write access to the repository
- Clean working directory on main branch

## Example Usage

```
/release
```

Then answer prompts for:
- Version number (e.g., "0.4.0")
- Release type (major/minor/patch)
- Changelog entries
- Confirmation at each publish step

## Notes

- The entire process takes ~10-15 minutes
- Most time is spent on test execution
- PyPI publishing is irreversible - be careful!
- Test PyPI is at https://test.pypi.org/
- GitHub releases are created automatically via workflow if tag is pushed
