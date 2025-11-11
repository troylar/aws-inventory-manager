# Compare Two Snapshots

Compare any two snapshots to see what changed between them.

## Task

Help the user compare two different snapshots to identify resource differences.

## Steps

### 1. Ask User for Snapshot Details

Ask the user:
- **First snapshot name** (older/baseline snapshot)
- **Second snapshot name** (newer snapshot to compare against)
- **Inventory name** (optional, defaults to "default")
- **AWS profile** (optional, uses default if not specified)
- **Filter options** (optional):
  - Resource type filter (e.g., "ec2", "s3", "lambda")
  - Region filter (e.g., "us-east-1")

### 2. Verify Snapshots Exist

```bash
# List snapshots to verify they exist
awsinv snapshot list --inventory <inventory> --profile <profile>
```

If either snapshot doesn't exist, show available snapshots and ask user to choose valid ones.

### 3. Load Both Snapshots

Export both snapshots to temporary JSON files:

```bash
# Export first snapshot
awsinv snapshot show <snapshot1> \
  --inventory <inventory> \
  --profile <profile> \
  --export /tmp/snapshot1.json

# Export second snapshot
awsinv snapshot show <snapshot2> \
  --inventory <inventory> \
  --profile <profile> \
  --export /tmp/snapshot2.json
```

### 4. Parse and Compare

Read both JSON files using Python or bash:

```python
import json

# Load snapshots
with open('/tmp/snapshot1.json') as f:
    snapshot1 = json.load(f)
with open('/tmp/snapshot2.json') as f:
    snapshot2 = json.load(f)

# Extract resources
resources1 = {r['arn']: r for r in snapshot1.get('resources', [])}
resources2 = {r['arn']: r for r in snapshot2.get('resources', [])}

# Compare
arns1 = set(resources1.keys())
arns2 = set(resources2.keys())

added = arns2 - arns1
removed = arns1 - arns2
common = arns1 & arns2

# Check for modifications in common resources
modified = []
for arn in common:
    if resources1[arn].get('config_hash') != resources2[arn].get('config_hash'):
        modified.append(arn)
```

### 5. Generate Comparison Report

Create a comprehensive report:

```
📊 Snapshot Comparison Report
═══════════════════════════════════════════════════════════

Snapshot 1: <name> (created: <date>)
Snapshot 2: <name> (created: <date>)
Inventory:  <inventory>
Time Span:  <duration-between-snapshots>

📈 Summary
───────────────────────────────────────────────────────────
Total in Snapshot 1: <count> resources
Total in Snapshot 2: <count> resources

Changes:
  ➕ Added:      <count> resources
  ➖ Removed:    <count> resources
  🔄 Modified:   <count> resources
  ✓ Unchanged:  <count> resources

Net Change: +<net> resources

➕ Added Resources (<count> total)
───────────────────────────────────────────────────────────
By Service:
  - EC2: <count> resources
  - S3: <count> resources
  - Lambda: <count> resources
  ...

Details:
  - ec2:instance | i-1234567890abcdef0 | us-east-1
    arn: arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0
    tags: Environment=prod, Team=platform

  - s3:bucket | my-new-bucket | us-east-1
    arn: arn:aws:s3:::my-new-bucket
    tags: Environment=prod

➖ Removed Resources (<count> total)
───────────────────────────────────────────────────────────
By Service:
  - Lambda: <count> resources
  - DynamoDB: <count> resources
  ...

Details:
  - lambda:function | old-function | us-east-1
    arn: arn:aws:lambda:us-east-1:123456789012:function:old-function

🔄 Modified Resources (<count> total)
───────────────────────────────────────────────────────────
Resources with configuration changes:

  - ec2:instance | i-abcdef1234567890 | us-east-1
    arn: arn:aws:ec2:us-east-1:123456789012:instance/i-abcdef1234567890
    note: Configuration hash changed (tags, metadata, or properties updated)

  - s3:bucket | existing-bucket | us-east-1
    arn: arn:aws:s3:::existing-bucket
    note: Configuration hash changed

📋 Resource Type Breakdown
───────────────────────────────────────────────────────────
Resource Type         | Snapshot 1 | Snapshot 2 | Change
──────────────────────┼────────────┼────────────┼────────
ec2:instance          |     45     |     48     |   +3
s3:bucket             |     12     |     13     |   +1
lambda:function       |     23     |     20     |   -3
dynamodb:table        |      8     |      8     |    0
...

📍 Regional Distribution
───────────────────────────────────────────────────────────
Region          | Snapshot 1 | Snapshot 2 | Change
────────────────┼────────────┼────────────┼────────
us-east-1       |     89     |     92     |   +3
us-west-2       |     34     |     34     |    0
eu-west-1       |     12     |     15     |   +3
...
```

### 6. Apply Filters

If user requested filters:
- Filter by resource type (e.g., only show EC2 changes)
- Filter by region (e.g., only show us-east-1 changes)
- Show filtered results

### 7. Export Option

Ask if user wants to export comparison:

**Export formats:**
- **JSON**: Full comparison data with all resource details
- **CSV**: Tabular format for spreadsheet analysis
- **TXT**: Text summary (same as terminal output)

```bash
# Example export structure for JSON:
{
  "snapshot1": {"name": "...", "created_at": "...", "resource_count": 123},
  "snapshot2": {"name": "...", "created_at": "...", "resource_count": 126},
  "comparison": {
    "added": [...],
    "removed": [...],
    "modified": [...],
    "unchanged_count": 120
  },
  "summary": {
    "total_changes": 6,
    "net_change": 3
  }
}
```

### 8. Insights and Recommendations

Provide insights based on comparison:

```
💡 Insights
───────────────────────────────────────────────────────────
- Infrastructure growth: +3 resources (+2.4%)
- Most active region: us-east-1 (+3 resources)
- Most changed service: EC2 (+3 instances)
- Removals detected: 3 Lambda functions deleted
- Configuration changes: 2 resources modified
```

## Example Usage

**Basic:**
```
/compare-snapshots
```

Then answer prompts:
- Snapshot 1: "baseline-jan"
- Snapshot 2: "baseline-feb"
- Inventory: "production"

**Advanced (in conversation):**
```
/compare-snapshots

User: Compare "snapshot-20250101" to "snapshot-20250201"
User: In the "prod-baseline" inventory
User: Only show EC2 changes
User: Export to comparison-report.json
```

## Use Cases

1. **Monthly baseline comparison** - See infrastructure changes month-over-month
2. **Before/after deployment** - Verify deployment created expected resources
3. **Audit trail** - Document changes for compliance
4. **Cost analysis prep** - Identify new resources that may impact costs
5. **Drift detection** - Find unauthorized changes between snapshots

## Notes

- Works with any two snapshots in the same or different inventories
- Useful for understanding changes between specific time periods
- Can compare across different inventories if resources overlap
- Modification detection is based on config_hash (SHA256)
- Modified resources show that something changed, but not exactly what
- Clean up temporary files after comparison

## Safety

- Read-only operation - doesn't modify anything
- Temporary JSON files are stored in /tmp
- Large snapshots (1000+ resources) may take longer to compare
- Consider using filters for large snapshots to focus on specific changes
