# Claude Code Features for aws-baseline

This directory contains custom Claude Code features tailored for the aws-baseline project.

## Overview

The aws-baseline project includes **9 custom features** that enhance development workflow, ensure code quality, prevent errors, and automate repetitive tasks:

- **4 Hooks** - Automated safety checks and quality gates
- **5 Slash Commands** - Streamlined workflows for common tasks

## Hooks

Hooks automatically run before or after tool executions to enforce safety and quality standards.

### 1. AWS Profile Validation Hook 🔍

**Trigger:** Before any `awsinv` command
**Purpose:** Prevents wrong-account operations by validating AWS credentials

**Features:**
- Verifies AWS credentials are valid
- Displays current AWS account ID and profile
- Warns when running destructive operations on production accounts
- Adds 3-second delay for production destructive operations

**Customization:**
Edit `.claude/hooks/aws-profile-validator.sh` and update the `PROD_ACCOUNTS` array with your production account IDs:

```bash
PROD_ACCOUNTS=("123456789012" "999888777666")
```

### 2. Pre-Commit Quality Check Hook ✨

**Trigger:** Before any `git commit` command
**Purpose:** Ensures code quality before commits

**Features:**
- Runs `invoke quality --fix` automatically
- Auto-fixes formatting and linting issues
- Runs type checking with mypy
- Blocks commit if quality checks fail

**Benefits:**
- Prevents CI failures
- Maintains consistent code style
- Catches type errors early

### 3. Deployment Safety Hook 🚨

**Trigger:** Before `gh release create` or PyPI publish commands
**Purpose:** Prevents accidental or unsafe releases

**Features:**
- Verifies on main branch
- Checks for uncommitted changes
- Runs full test suite
- Verifies version was bumped
- Warns if CHANGELOG not updated

**Safety:**
- Cannot release from feature branches
- Cannot release with failing tests
- Cannot release without version bump

### 4. Test Coverage Guardian Hook 📊

**Trigger:** After running tests (`pytest` or `invoke test`)
**Purpose:** Prevents test coverage regression

**Features:**
- Extracts current coverage percentage
- Compares against minimum threshold (stored in `.min_coverage`)
- Blocks if coverage decreases
- Auto-updates threshold when coverage improves

**Current Threshold:** 39%

The `.min_coverage` file tracks the minimum acceptable coverage. This automatically increases when you improve coverage!

## Slash Commands

Slash commands provide interactive workflows for complex tasks.

### 1. /snapshot-all-accounts

**Purpose:** Take snapshots across multiple AWS accounts
**Time Saved:** 30+ minutes per multi-account snapshot session

**Usage:**
```
/snapshot-all-accounts
```

**Features:**
- Automatically discovers AWS profiles from `~/.aws/config`
- Validates credentials for each account
- Creates inventories automatically
- Takes snapshots in sequence or parallel
- Provides detailed success/failure summary
- Tracks progress with todo list

**Example Output:**
```
📊 Multi-Account Snapshot Summary

✅ Successfully snapshotted:
   - prod-account (123456789012) - 245 resources
   - staging-account (234567890123) - 189 resources
   - dev-account (345678901234) - 312 resources

❌ Failed accounts:
   - test-account: credential error

📈 Total: 4 accounts, 3 succeeded (746 resources), 1 failed
⏱️  Duration: 12 minutes
```

### 2. /release

**Purpose:** Automate the complete release process
**Time Saved:** 15-20 minutes per release

**Usage:**
```
/release
```

**Complete Workflow:**
1. Pre-release checks (branch, uncommitted changes, tests)
2. Version bumping in pyproject.toml
3. CHANGELOG.md update
4. Git commit and tag
5. Push to GitHub
6. Create GitHub release
7. Build package
8. Publish to PyPI (with Test PyPI option)
9. Verification and post-release summary

**Safety Features:**
- Interactive prompts at each step
- Shows diffs before committing
- Asks for confirmation before publishing
- Recommends Test PyPI before production
- Runs full test suite before allowing release

### 3. /compare-snapshots

**Purpose:** Compare any two historical snapshots
**Time Saved:** 10 minutes per comparison

**Usage:**
```
/compare-snapshots
```

**Features:**
- Compare any two snapshots (not just current vs baseline)
- Identifies added, removed, and modified resources
- Shows resource type and regional breakdowns
- Calculates net change and growth percentage
- Provides insights and recommendations
- Export to JSON, CSV, or TXT

**Example Report:**
```
📊 Snapshot Comparison Report

Snapshot 1: baseline-jan (2025-01-01)
Snapshot 2: baseline-feb (2025-02-01)
Time Span: 31 days

📈 Summary
Total in Snapshot 1: 245 resources
Total in Snapshot 2: 248 resources

Changes:
  ➕ Added:      5 resources
  ➖ Removed:    2 resources
  🔄 Modified:   3 resources
  ✓ Unchanged:  240 resources

Net Change: +3 resources (+1.2%)
```

### 4. /new-collector

**Purpose:** Generate new AWS resource collector
**Time Saved:** 1 hour per new service

**Usage:**
```
/new-collector
```

**Generates:**
- Complete collector implementation following project patterns
- Unit tests with mocking
- Integration into collector registry
- Implementation checklist

**Example:**
```
/new-collector

User: Service is EFS
User: Collecting File Systems
User: Boto3 client is 'efs'
```

**Output:**
- `src/snapshot/resource_collectors/efs_collector.py`
- `tests/unit/snapshot/resource_collectors/test_efs_collector.py`
- Updated `src/snapshot/resource_collectors/__init__.py`
- Checklist for testing and documentation

### 5. /boto3-docs

**Purpose:** Quick boto3 API reference
**Time Saved:** 5 minutes per lookup

**Usage:**
```
/boto3-docs

User: ec2
```

**Provides:**
- Service overview and client setup
- Common methods (list, describe, create, delete, tag)
- Paginator information
- Tag format examples
- ARN patterns
- Code examples
- Link to full documentation

**Great for:** Writing new collectors, debugging API calls, understanding service patterns

## File Structure

```
.claude/
├── README.md                           # This file
├── settings.local.json                 # Hooks configuration
├── hooks/                              # Hook scripts
│   ├── aws-profile-validator.sh        # AWS account validation
│   ├── pre-commit-quality.sh           # Code quality checks
│   ├── deployment-safety.sh            # Release safety checks
│   └── coverage-guardian.sh            # Test coverage monitoring
└── commands/                           # Slash commands
    ├── snapshot-all-accounts.md        # Multi-account snapshots
    ├── release.md                      # Release automation
    ├── compare-snapshots.md            # Snapshot comparison
    ├── new-collector.md                # Collector generator
    └── boto3-docs.md                   # Boto3 documentation helper
```

## Configuration

### Customizing Hooks

**AWS Profile Validator:**
- Edit `.claude/hooks/aws-profile-validator.sh`
- Update `PROD_ACCOUNTS` array with your production AWS account IDs

**Coverage Guardian:**
- Current threshold stored in `.min_coverage` (currently 39%)
- Automatically updates when coverage improves
- Manually edit `.min_coverage` to set a different threshold

### Disabling Hooks

To temporarily disable all hooks, add to `.claude/settings.local.json`:

```json
{
  "disableAllHooks": true
}
```

To disable a specific hook, remove its entry from the `hooks` section in `.claude/settings.local.json`.

## Usage Examples

### Multi-Account Snapshot Workflow

```
/snapshot-all-accounts

Claude: Which AWS profiles do you want to snapshot?
User: dev-*, staging-*, prod-*

Claude: Which regions should I scan?
User: us-east-1, us-west-2

Claude: [Executes snapshots across all matching profiles]

✅ Successfully snapshotted 5 accounts
```

### Release Workflow

```
/release

Claude: What version are you releasing?
User: 0.4.0

Claude: What type of release? (major/minor/patch)
User: minor

Claude: What are the notable changes?
User: Added EFS collector, improved error handling, updated docs

Claude: [Shows diffs, commits, tags, builds, asks for PyPI confirmation]

✅ Release v0.4.0 Complete!
```

### Compare Snapshots

```
/compare-snapshots

Claude: First snapshot name?
User: baseline-20250101

Claude: Second snapshot name?
User: baseline-20250201

Claude: [Generates detailed comparison report]

📊 Summary: +3 resources, 2 removed, 5 added, 3 modified
```

## Benefits

### Safety & Quality
- ✅ Prevents wrong-account AWS operations
- ✅ Blocks commits with quality issues
- ✅ Prevents unsafe releases
- ✅ Maintains test coverage

### Productivity
- ⚡ Automates multi-account snapshots (saves 30+ min)
- ⚡ Streamlines releases (saves 20+ min)
- ⚡ Accelerates new service additions (saves 1 hour)
- ⚡ Quick API documentation (saves 5 min per lookup)

### Developer Experience
- 🎯 Consistent code quality
- 🎯 Standardized release process
- 🎯 Guided workflows
- 🎯 Automatic validation

## Troubleshooting

### Hook Not Running

1. **Check hook is enabled** in `.claude/settings.local.json`
2. **Verify hook script is executable:**
   ```bash
   chmod +x .claude/hooks/*.sh
   ```
3. **Check matcher pattern** matches the command

### Hook Fails

1. **Read hook output** - error messages provide context
2. **Run hook manually** for debugging:
   ```bash
   .claude/hooks/aws-profile-validator.sh "awsinv snapshot list"
   ```
3. **Check dependencies** (invoke, aws-cli, etc. are installed)

### Command Not Found

1. **Verify command file exists** in `.claude/commands/`
2. **Check file extension** is `.md`
3. **Restart Claude Code** to reload commands

## Development

### Adding New Hooks

1. Create hook script in `.claude/hooks/`
2. Make executable: `chmod +x .claude/hooks/your-hook.sh`
3. Add configuration to `.claude/settings.local.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash(your-pattern*)",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/your-hook.sh \"$COMMAND\""
          }
        ]
      }
    ]
  }
}
```

### Adding New Commands

1. Create markdown file in `.claude/commands/`
2. Follow the command template structure
3. Include clear task description and steps
4. Add examples and usage notes

### Testing Hooks

Test hooks manually:

```bash
# Test AWS profile validator
.claude/hooks/aws-profile-validator.sh "awsinv snapshot create test"

# Test pre-commit quality
.claude/hooks/pre-commit-quality.sh "git commit -m 'test'"

# Test deployment safety
.claude/hooks/deployment-safety.sh "gh release create v0.4.0"

# Test coverage guardian (requires coverage data)
.claude/hooks/coverage-guardian.sh "invoke test" ""
```

## Best Practices

1. **Keep hooks fast** - Slow hooks interrupt workflow
2. **Provide clear error messages** - Help users fix issues
3. **Make hooks optional** - Allow bypassing for special cases
4. **Document customization** - Make it easy to adapt
5. **Test hooks thoroughly** - Avoid breaking workflows

## Support

For issues or questions:
- Check troubleshooting section above
- Review hook scripts for error messages
- Test hooks manually
- See Claude Code documentation: https://docs.claude.com/claude-code

## Version

**Claude Code Features Version:** 1.0.0
**Last Updated:** 2025-01-09
**Compatible with:** aws-inventory-manager v0.3.0+
