<div align="center">

# 📦 AWS Inventory Manager

### *Your AWS Environment, Tracked, Secured, and Understood*

[![CI](https://github.com/troylar/aws-inventory-manager/actions/workflows/ci.yml/badge.svg)](https://github.com/troylar/aws-inventory-manager/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/troylar/aws-inventory-manager/branch/main/graph/badge.svg)](https://codecov.io/gh/troylar/aws-inventory-manager)
[![PyPI version](https://img.shields.io/pypi/v/aws-inventory-manager.svg)](https://pypi.org/project/aws-inventory-manager/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Point-in-time snapshots** • **Security scanning** • **Configuration drift** • **Cost analysis** • **27 AWS services**

[Quick Start](#quick-start) • [Features](#features) • [Documentation](#documentation) • [Contributing](#contributing)

</div>

---

## 🎯 Why AWS Inventory Manager?

Managing AWS environments is complex. Resources multiply, configurations drift, security issues creep in, and costs spiral. AWS Inventory Manager gives you **visibility, control, and confidence**.

### What You Get

```bash
# Capture your entire AWS environment in seconds
awsinv snapshot create baseline --regions us-east-1,us-west-2

# Know exactly what changed
awsinv delta --show-diff  # See field-level configuration changes

# Find security issues before they find you
awsinv security scan --severity HIGH  # CIS Benchmark aligned

# Track costs by team, environment, or account
awsinv cost --inventory team-alpha
```

### The Problem It Solves

- **"What changed?"** - See exactly which resources were added, removed, or modified, down to the field level
- **"Are we secure?"** - Automated security scanning against CIS AWS Foundations Benchmark
- **"How much does this cost?"** - Per-inventory cost tracking and attribution
- **"Can we go back?"** - Point-in-time snapshots let you understand and restore previous states
- **"Who owns what?"** - Tag-based filtering and team/environment isolation

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 📸 **Snapshot & Track**
- Capture 27 AWS services across regions
- Point-in-time resource inventory
- Tag-based filtering (team, env, project)
- Multi-account support
- Export to JSON/CSV/TXT

</td>
<td width="50%">

### 🔍 **Configuration Drift**
- Field-level change detection
- See exactly what changed: tags, config, security
- Color-coded terminal output
- Before/after comparison
- Drift reports in JSON

</td>
</tr>
<tr>
<td>

### 🔒 **Security Scanning**
- 12+ security checks (CIS aligned)
- Find public S3 buckets, open ports, old credentials
- Severity levels: CRITICAL → LOW
- Remediation guidance
- Compliance reports (JSON/CSV)

</td>
<td>

### 💰 **Cost Analysis**
- Per-inventory cost tracking
- Compare costs across teams/environments
- Date range analysis
- Service-level breakdown
- Cost attribution by tags

</td>
</tr>
</table>

---

## 🚀 Quick Start

### Installation

```bash
pip install aws-inventory-manager
```

### 60-Second Demo

```bash
# 1. Create an inventory (logical grouping)
awsinv inventory create production --description "Production resources"

# 2. Take a snapshot
awsinv snapshot create baseline --regions us-east-1 --inventory production

# 3. See what you have
awsinv snapshot report --inventory production

# 4. Scan for security issues
awsinv security scan --inventory production

# 5. Track changes over time
awsinv delta --inventory production --show-diff
```

**That's it!** You now have visibility into your AWS environment.

---

## 📖 Complete Walkthrough

### Step 1: Create Your First Inventory

An **inventory** is a named collection that organizes your snapshots.

```bash
awsinv inventory create prod-baseline \
  --description "Production baseline resources"
```

<details>
<summary><b>💡 Pro Tip:</b> Use tag filters for team/environment isolation</summary>

```bash
# Track only resources belonging to Team Alpha
awsinv inventory create team-alpha \
  --include-tags "Team=Alpha" \
  --description "Team Alpha resources"

# Exclude development resources
awsinv inventory create non-dev \
  --exclude-tags "Environment=development"
```
</details>

---

### Step 2: Capture Your AWS Environment

Take a **snapshot** to capture the current state of your AWS resources.

```bash
awsinv snapshot create initial \
  --regions us-east-1 \
  --inventory prod-baseline
```

**What gets captured:**
- 27 AWS services (S3, EC2, RDS, Lambda, EFS, ElastiCache, and more)
- Full resource configurations
- Tags, metadata, encryption settings
- All in < 30 seconds

<details>
<summary><b>What's captured?</b> Click to see all 27 services</summary>

- **Compute:** EC2, Lambda, ECS, EKS
- **Storage:** S3, EFS, EBS Volumes
- **Database:** RDS, DynamoDB, ElastiCache
- **Networking:** VPCs, Security Groups, Load Balancers, Route53
- **Security:** IAM, KMS, Secrets Manager
- **DevOps:** CodePipeline, CodeBuild, CloudFormation
- **Monitoring:** CloudWatch, EventBridge, SNS, SQS
- **More:** Step Functions, WAF, Systems Manager, Backup

</details>

---

### Step 3: Generate Reports

```bash
# Summary view - see resource counts by service
awsinv snapshot report --inventory prod-baseline

# Detailed view - see all resources with full metadata
awsinv snapshot report --inventory prod-baseline --detailed

# Filter by resource type
awsinv snapshot report --resource-type s3 --inventory prod-baseline

# Export to JSON, CSV, or TXT
awsinv snapshot report --export report.json --inventory prod-baseline
```

**Example output:**
```
Resources by service:
┏━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Service               ┃ Count ┃
┡━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ AWS::EC2::Instance    │     5 │
│ AWS::S3::Bucket       │    12 │
│ AWS::RDS::DBInstance  │     3 │
│ AWS::Lambda::Function │     8 │
└───────────────────────┴───────┘
```

---

### Step 4: Track Changes (Delta)

See exactly what changed since your baseline.

```bash
# Basic delta - shows which resources changed
awsinv delta --snapshot initial --inventory prod-baseline

# Enhanced delta - shows WHAT changed (field-level)
awsinv delta --snapshot initial --inventory prod-baseline --show-diff
```

**Field-level drift output:**
```
Configuration Changes:
  Instance i-abc123:
    InstanceType: t2.micro → t2.small
    Tags.Environment: dev → prod

Security Changes:
  Bucket my-bucket:
    PublicAccessBlockConfiguration.BlockPublicAcls: true → false  ⚠️
```

<details>
<summary><b>🎨 Color-coded output</b></summary>

- 🔴 **Red** - Removed fields
- 🟢 **Green** - Added fields
- 🟡 **Yellow** - Security-critical changes
- 🔵 **Cyan** - Configuration changes

</details>

---

### Step 5: Scan for Security Issues

Find misconfigurations **before** they become incidents.

```bash
# Scan for all security issues
awsinv security scan --inventory prod-baseline

# Filter by severity
awsinv security scan --severity CRITICAL --inventory prod-baseline

# Show only CIS Benchmark findings
awsinv security scan --cis-only --inventory prod-baseline

# Export for compliance reporting
awsinv security scan --export findings.json --inventory prod-baseline
```

**Security checks include:**

| Check | Severity | CIS Control |
|-------|----------|-------------|
| Public S3 buckets | **CRITICAL** | 2.1.5 |
| Open SSH/RDP ports (22, 3389) | **HIGH** | 5.2, 5.3 |
| Open database ports (3306, 5432, etc.) | **HIGH** | 5.2, 5.3 |
| Publicly accessible RDS | **HIGH** | - |
| Unencrypted storage (RDS, ElastiCache) | **HIGH** | - |
| EC2 with IMDSv1 | **MEDIUM** | - |
| IAM keys > 90 days old | **MEDIUM** | 1.4 |
| Secrets not rotated | **MEDIUM** | - |

**Example output:**
```
🔍 Scanning snapshot: prod-baseline

Security Findings (5 issues):

[CRITICAL] Public S3 Bucket (CIS 2.1.5)
  Resource: arn:aws:s3:::my-public-bucket
  Finding: Bucket is publicly accessible
  Remediation: Enable S3 Block Public Access settings

[HIGH] Security Group - Open SSH
  Resource: sg-12345 (web-servers)
  Finding: Port 22 open to 0.0.0.0/0
  Remediation: Restrict SSH access to specific IP ranges

CIS Benchmark Summary:
  Controls checked: 6  Failed: 2  Passed: 4
```

---

### Step 6: Analyze Costs

Track and attribute AWS costs by inventory.

```bash
# Costs since snapshot was created
awsinv cost --snapshot initial --inventory prod-baseline

# Costs for specific date range
awsinv cost --snapshot initial --inventory prod-baseline \
  --start-date 2025-01-01 \
  --end-date 2025-01-31

# Show breakdown by service
awsinv cost --inventory prod-baseline --show-services
```

---

## 🎯 Real-World Use Cases

### 1. Multi-Team Cost Attribution

```bash
# Create team-specific inventories
awsinv inventory create team-frontend --include-tags "Team=Frontend"
awsinv inventory create team-backend --include-tags "Team=Backend"

# Track costs per team
awsinv cost --inventory team-frontend
awsinv cost --inventory team-backend
```

### 2. Security Compliance Audits

```bash
# Scan production for CIS compliance
awsinv security scan --inventory production --cis-only --export cis-audit.csv

# Track remediation progress over time
awsinv snapshot create after-remediation --inventory production
awsinv security scan --inventory production
```

### 3. Configuration Drift Detection

```bash
# Baseline before deployment
awsinv snapshot create pre-deploy --inventory production

# Deploy changes...

# See exactly what changed
awsinv delta --snapshot pre-deploy --show-diff --inventory production
```

### 4. Multi-Account Management

```bash
# Snapshot production account
awsinv --profile prod-account snapshot create prod-baseline

# Snapshot staging account
awsinv --profile staging-account snapshot create staging-baseline

# Compare environments
awsinv delta --snapshot prod-baseline --profile prod-account
awsinv delta --snapshot staging-baseline --profile staging-account
```

---

## 📊 Supported AWS Services (27 Total)

<table>
<tr>
<td width="25%">

**Compute**
- EC2 Instances
- Lambda Functions
- ECS Clusters
- EKS Clusters

</td>
<td width="25%">

**Storage**
- S3 Buckets
- EBS Volumes
- EFS File Systems
- Backup Vaults

</td>
<td width="25%">

**Database**
- RDS Instances
- DynamoDB Tables
- ElastiCache Clusters
- Aurora Clusters

</td>
<td width="25%">

**Security**
- IAM Roles/Users
- KMS Keys
- Secrets Manager
- Security Groups

</td>
</tr>
<tr>
<td>

**Networking**
- VPCs
- Subnets
- Load Balancers
- Route53 Zones

</td>
<td>

**DevOps**
- CodePipeline
- CodeBuild
- CloudFormation
- Step Functions

</td>
<td>

**Monitoring**
- CloudWatch Alarms
- CloudWatch Logs
- SNS Topics
- SQS Queues

</td>
<td>

**Other**
- API Gateway
- EventBridge
- WAF
- Systems Manager

</td>
</tr>
</table>

---

## 🔒 Security Scanning Details

### What Gets Scanned

The security scanner performs **12+ checks** aligned with **CIS AWS Foundations Benchmark**:

```bash
awsinv security scan --inventory production
```

| Category | Checks | Severity |
|----------|--------|----------|
| **Storage** | Public S3 buckets, unencrypted RDS/ElastiCache | CRITICAL / HIGH |
| **Network** | Open ports (SSH, RDP, databases) to 0.0.0.0/0 | HIGH |
| **Compute** | EC2 with IMDSv1 enabled | MEDIUM |
| **IAM** | Access keys older than 90 days | MEDIUM |
| **Secrets** | Secrets Manager not rotated in 90+ days | MEDIUM |

### Output Formats

```bash
# Terminal output with colors
awsinv security scan --inventory prod

# JSON for automation
awsinv security scan --inventory prod --export findings.json

# CSV for spreadsheets
awsinv security scan --inventory prod --export findings.csv --format csv
```

---

## 🛠️ Configuration

### Storage Location

By default, snapshots are stored in `~/.snapshots`. Customize this:

```bash
# Environment variable (persistent)
export AWS_INVENTORY_STORAGE_PATH=/path/to/snapshots

# CLI parameter (one-time)
awsinv --storage-path /custom/path inventory list
```

**Precedence:** CLI parameter > Environment variable > Default

### AWS Profiles

Use AWS CLI profiles for multi-account management:

```bash
# All commands support --profile
awsinv --profile production snapshot create baseline
awsinv --profile staging security scan
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     AWS Inventory Manager               │
├─────────────────────────────────────────────────────────┤
│  CLI (Typer + Rich)                                     │
│    ├─ inventory    (Organize snapshots)                 │
│    ├─ snapshot     (Capture resources)                  │
│    ├─ delta        (Track changes)                      │
│    ├─ security     (Scan misconfigurations)             │
│    └─ cost         (Analyze spending)                   │
├─────────────────────────────────────────────────────────┤
│  Core Engine                                            │
│    ├─ 27 Resource Collectors (boto3)                    │
│    ├─ Configuration Differ (field-level)                │
│    ├─ Security Scanner (CIS aligned)                    │
│    └─ Cost Analyzer (AWS Cost Explorer)                 │
├─────────────────────────────────────────────────────────┤
│  Storage (YAML)                                         │
│    ├─ ~/.snapshots/inventories.yaml                     │
│    └─ ~/.snapshots/<snapshot-name>.yaml                 │
└─────────────────────────────────────────────────────────┘
```

**Tech Stack:**
- **Language:** Python 3.8+
- **CLI:** Typer (beautiful terminal UI with Rich)
- **AWS SDK:** boto3
- **Storage:** YAML (human-readable)
- **Testing:** pytest (509 tests, 52% coverage)

---

## 🧪 Development

### Setup

```bash
# Clone and install
git clone https://github.com/troylar/aws-inventory-manager.git
cd aws-inventory-manager
pip install -e ".[dev]"

# Verify
awsinv --help
```

### Testing

```bash
invoke test              # Run all tests with coverage
invoke test-unit         # Unit tests only
invoke test-integration  # Integration tests only
invoke coverage-report   # Generate HTML coverage report
```

### Code Quality

```bash
invoke quality           # Run all checks (format, lint, typecheck)
invoke quality --fix     # Auto-fix issues
invoke format            # Format with black
invoke lint              # Lint with ruff
invoke typecheck         # Type check with mypy
```

### Build & Release

```bash
invoke clean    # Clean build artifacts
invoke build    # Build package
invoke version  # Show version
invoke ci       # Run all CI checks
```

---

## 📚 Command Reference

### Quick Command Index

```bash
# INVENTORY MANAGEMENT
awsinv inventory create <name> [--description "..."] [--include-tags "..."]
awsinv inventory list
awsinv inventory show <name>
awsinv inventory delete <name>

# SNAPSHOTS
awsinv snapshot create [name] [--regions us-east-1] [--inventory <name>]
awsinv snapshot list [--inventory <name>]
awsinv snapshot report [--inventory <name>] [--detailed] [--export file.json]
awsinv snapshot show <name>

# ANALYSIS
awsinv delta [--snapshot <name>] [--show-diff] [--inventory <name>]
awsinv security scan [--inventory <name>] [--severity HIGH] [--export findings.json]
awsinv cost [--inventory <name>] [--start-date YYYY-MM-DD] [--show-services]

# GLOBAL OPTIONS
--profile <aws-profile>        # AWS CLI profile
--storage-path <path>          # Custom snapshot storage location
--help                         # Show help for any command
```

### Full Command Documentation

<details>
<summary><b>Inventory Commands</b></summary>

```bash
# Create an inventory
awsinv inventory create <name> \
  [--description "Description"] \
  [--include-tags "Key1=Value1,Key2=Value2"] \
  [--exclude-tags "Key3=Value3"] \
  [--profile <aws-profile>]

# List all inventories
awsinv inventory list [--profile <aws-profile>]

# Show inventory details
awsinv inventory show <name> [--profile <aws-profile>]

# Delete an inventory
awsinv inventory delete <name> [--force] [--profile <aws-profile>]

# Migrate legacy snapshots
awsinv inventory migrate [--profile <aws-profile>]
```

</details>

<details>
<summary><b>Snapshot Commands</b></summary>

```bash
# Create a snapshot
awsinv snapshot create [name] \
  [--inventory <inventory-name>] \
  [--regions <region1,region2>] \
  [--include-tags "Key=Value"] \
  [--exclude-tags "Key=Value"] \
  [--before-date YYYY-MM-DD] \
  [--after-date YYYY-MM-DD] \
  [--compress] \
  [--profile <aws-profile>]

# Generate snapshot report
awsinv snapshot report [snapshot-name] \
  [--inventory <inventory-name>] \
  [--resource-type <type>] \
  [--region <region>] \
  [--detailed] \
  [--page-size <number>] \
  [--export <file.json|file.csv|file.txt>] \
  [--profile <aws-profile>]

# List all snapshots
awsinv snapshot list [--profile <aws-profile>]

# Show snapshot details
awsinv snapshot show <name> [--profile <aws-profile>]
```

</details>

<details>
<summary><b>Analysis Commands</b></summary>

```bash
# View resource delta
awsinv delta \
  [--inventory <inventory-name>] \
  [--snapshot <snapshot-name>] \
  [--resource-type <type>] \
  [--region <region>] \
  [--show-details] \
  [--show-diff] \
  [--export <file.json|file.csv>] \
  [--profile <aws-profile>]

# Analyze costs
awsinv cost \
  [--inventory <inventory-name>] \
  [--snapshot <snapshot-name>] \
  [--start-date YYYY-MM-DD] \
  [--end-date YYYY-MM-DD] \
  [--granularity DAILY|MONTHLY] \
  [--show-services] \
  [--export <file.json|file.csv>] \
  [--profile <aws-profile>]

# Security scan
awsinv security scan \
  [--inventory <inventory-name>] \
  [--snapshot <snapshot-name>] \
  [--severity <CRITICAL|HIGH|MEDIUM|LOW>] \
  [--cis-only] \
  [--export <file.json|file.csv>] \
  [--profile <aws-profile>]
```

</details>

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make your changes**
4. **Run tests** (`invoke test`)
5. **Run quality checks** (`invoke quality`)
6. **Commit** (`git commit -m 'feat: add amazing feature'`)
7. **Push** (`git push origin feature/amazing-feature`)
8. **Open a Pull Request**

### Development Guidelines

- Follow existing code style (enforced by black, ruff, mypy)
- Write tests for new features
- Update documentation
- Keep commits atomic and well-described

---

## 📜 License

MIT License - see [LICENSE](LICENSE) for details

---

## 🆘 Support

- **Issues:** [GitHub Issues](https://github.com/troylar/aws-inventory-manager/issues)
- **Documentation:** [README](https://github.com/troylar/aws-inventory-manager#readme)
- **Discussions:** [GitHub Discussions](https://github.com/troylar/aws-inventory-manager/discussions)

---

## 🎉 Acknowledgments

Built with:
- [Typer](https://typer.tiangolo.com/) - Beautiful CLI framework
- [Rich](https://rich.readthedocs.io/) - Terminal formatting
- [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) - AWS SDK
- [pytest](https://pytest.org/) - Testing framework

---

<div align="center">

**Made with ❤️ for AWS practitioners**

[![Star on GitHub](https://img.shields.io/github/stars/troylar/aws-inventory-manager?style=social)](https://github.com/troylar/aws-inventory-manager)

**Version** 0.3.0 • **Python** 3.8 - 3.13 • **Status** Alpha

[⬆ Back to Top](#-aws-inventory-manager)

</div>
