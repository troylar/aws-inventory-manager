# AWS Inventory Manager - Product Roadmap

**Last Updated:** 2025-01-09
**Current Version:** 0.3.0
**GitHub Issues:** https://github.com/troylar/aws-inventory-manager/issues

---

## Overview

This roadmap outlines planned features for aws-inventory-manager, organized by priority and implementation phases. All features have been created as GitHub issues for tracking and discussion.

---

## 🎯 Quick Wins (1 Week - Issues #33)

**Goal:** Maximum value with minimal effort
**Timeline:** 1 week
**Total Effort:** 6-7 days

| Feature | Issue | Effort | Impact |
|---------|-------|--------|--------|
| Configuration Drift Details | #15 | 1-2 days | Makes delta actually useful |
| Security Posture Scanning | #17 | 2-3 days | Immediate security insights |
| EFS Collector | #23 | 1 day | Common storage service |
| ElastiCache Collector | #24 | 1 day | Common caching service |

**Why These?**
- Quick to implement
- Immediate value to users
- Builds on existing functionality
- High user demand

---

## 📋 Phase 1: Core Gaps (4-6 Weeks)

**Goal:** Address critical missing features
**Priority:** 🔴 CRITICAL

### Critical Features

| Feature | Issue | Effort | Status |
|---------|-------|--------|--------|
| **Resource Cleanup/Restoration** | #14 | 2-3 days | Not Started |
| **Configuration Drift Details** | #15 | 1-2 days | Not Started |
| **Multi-Account & Org Support** | #16 | 3-4 days | Not Started |
| **Security Posture Scanning** | #17 | 2-3 days | Not Started |

### Phase 1 Details

#### 1. Resource Cleanup/Restoration (#14)
**Why Critical:** Promised in README but not implemented

**Commands:**
```bash
awsinv restore --snapshot baseline-jan --dry-run
awsinv restore --snapshot baseline-jan --confirm
```

**Features:**
- Dry-run preview
- Tag-based protection
- Dependency analysis
- Deletion audit trail
- Safety checks

**Acceptance Criteria:**
- Deletes only new resources since baseline
- Safety protections prevent critical deletions
- Audit trail logs all actions
- Tests achieve >80% coverage

---

#### 2. Configuration Drift Details (#15)
**Why Critical:** Current delta only shows hash changed, not what changed

**Before:**
```
🔄 Modified: ec2:instance i-1234567890
   Config hash changed
```

**After:**
```
🔄 Modified: ec2:instance i-1234567890

   Tags Changed:
   - Environment: prod → staging
   + Owner: alice

   Security Groups Changed:
   - sg-old123 + sg-new456

   Instance Type: t2.micro → t2.small
```

---

#### 3. Multi-Account & Organizations Support (#16)
**Why Critical:** Essential for enterprise use

**Commands:**
```bash
awsinv snapshot create baseline --all-accounts
awsinv snapshot create baseline --ou ou-abc123
awsinv cost --all-accounts --group-by account
```

**Features:**
- Auto-discover accounts via Organizations API
- Cross-account role assumption
- Parallel scanning
- Consolidated reporting

---

#### 4. Security Posture Scanning (#17)
**Why High Priority:** High ROI, low effort

**Critical Checks:**
- Public S3 buckets
- Security groups with 0.0.0.0/0
- Publicly accessible RDS
- IMDSv1 enabled EC2
- Unrotated secrets/credentials
- IAM over-permissions

**Output:**
```
🚨 Security Scan Results

Critical (5):
  ❌ S3 bucket 'prod-data' is publicly accessible
  ❌ RDS instance 'prod-db' is publicly accessible
  ❌ Security Group 'sg-123' allows 0.0.0.0/0 on port 22

CIS AWS Foundations Benchmark: 67/100 checks passed
```

---

## 💰 Phase 2: Cost & Automation (3-4 Weeks)

**Goal:** Enhanced cost tracking and automation
**Priority:** 🟡 MEDIUM

| Feature | Issue | Effort |
|---------|-------|--------|
| Resource-Level Cost Estimation | #18 | 3-4 days |
| Baseline vs Delta Cost Attribution | #19 | 2 days |
| Cost Anomaly Detection | #20 | 2 days |
| Scheduled Snapshots & Automation | #21 | 2 days |
| Tag Governance & Enforcement | #22 | 2 days |

### Key Features

#### Resource-Level Cost Estimation (#18)
Use AWS Pricing API to estimate costs per resource:
- EC2: instance type × hours × pricing
- S3: storage size × storage class
- RDS: instance + storage + backup
- Lambda: invocations × duration

#### Baseline vs Delta Cost Attribution (#19)
Tag baseline resources, then split costs:
```
💰 Cost Split Report

Baseline Resources:     $2,450.00 (60%)
Delta Resources:        $1,633.33 (40%)
Total:                  $4,083.33
```

#### Scheduled Snapshots (#21)
```bash
awsinv schedule create daily-snapshot --cron "0 2 * * *"
awsinv daemon start
awsinv deploy lambda --schedule "rate(1 day)"
```

#### Tag Governance (#22)
```bash
awsinv tags audit --required "Environment,Owner,CostCenter"
awsinv tags missing --export untagged.csv
awsinv tags apply --from-snapshot baseline --tag-key Baseline --tag-value true
```

---

## 🔧 Phase 3: Service Expansion (4-6 Weeks)

**Goal:** Broader AWS service coverage
**Priority:** 🟢 MEDIUM

| Service | Issue | Effort | Importance |
|---------|-------|--------|------------|
| EFS (File Systems) | #23 | 1 day | High |
| ElastiCache (Redis/Memcached) | #24 | 1 day | High |
| Kinesis (Streaming) | #25 | 1-2 days | Medium |
| Additional Services (Batch) | #26 | 1-2 days each | Medium |
| Glue (ETL) | #32 | 1-2 days | Medium |
| AWS Config Integration | #27 | 3-4 days | Medium |

### Service Expansion Strategy

**Use `/new-collector` command** to rapidly generate collectors!

**High-Priority Services:**
- EFS - File storage (common)
- ElastiCache - Caching layer (common)
- Kinesis - Streaming data
- Glue - ETL jobs
- Athena - Query engine
- OpenSearch - Search/analytics
- AppSync - GraphQL APIs
- Cognito - User authentication

**Medium-Priority:**
- SageMaker - ML endpoints
- Redshift - Data warehouse
- MSK - Managed Kafka
- Transfer Family - SFTP servers

**Goal:** Increase from 25 services to 35+ services

---

## 🚀 Phase 4: Advanced Features (6-8 Weeks)

**Goal:** Enterprise-grade capabilities
**Priority:** 🟢 LOW

| Feature | Issue | Effort |
|---------|-------|--------|
| Resource Dependencies & Relationships | #28 | 4-5 days |
| Compliance Reporting (CIS, NIST) | #29 | 3-4 days |
| Well-Architected Framework Assessment | #30 | 5-7 days |
| Interactive TUI | #31 | 3-4 days |

### Advanced Features Details

#### Resource Dependencies (#28)
```bash
awsinv dependencies show --resource arn:aws:ec2:...
awsinv dependencies graph --export graph.dot
awsinv dependencies check-delete --resource sg-123
```

Builds dependency graph:
- EC2 → Security Group → VPC
- Lambda → IAM Role
- ALB → Target Group → EC2
- Safe deletion order calculation

#### Compliance Reporting (#29)
Map findings to frameworks:
- CIS AWS Foundations Benchmark
- NIST Cybersecurity Framework
- PCI-DSS
- HIPAA
- SOC 2

#### Well-Architected Framework (#30)
Assess against 6 pillars:
- Operational Excellence
- Security
- Reliability
- Performance Efficiency
- Cost Optimization
- Sustainability

#### Interactive TUI (#31)
Terminal UI using Textual:
- Hierarchical navigation
- Search and filter
- Resource details
- Visual dependency graphs
- Cost visualization

---

## 📊 Roadmap Timeline

```
┌─────────────────────────────────────────────────────────────┐
│                    2025 Development Timeline                 │
├─────────────────────────────────────────────────────────────┤
│ Q1 2025 (Jan-Mar)                                           │
│ ├─ Week 1-1:   Quick Wins (#33)                            │
│ ├─ Week 2-6:   Phase 1 (Core Gaps)                         │
│ └─ Week 7-10:  Phase 2 (Cost & Automation) [Start]         │
│                                                              │
│ Q2 2025 (Apr-Jun)                                           │
│ ├─ Week 1-2:   Phase 2 (Cost & Automation) [Complete]      │
│ ├─ Week 3-8:   Phase 3 (Service Expansion)                 │
│ └─ Week 9-12:  Phase 4 (Advanced Features) [Start]         │
│                                                              │
│ Q3 2025 (Jul-Sep)                                           │
│ ├─ Week 1-4:   Phase 4 (Advanced Features) [Complete]      │
│ └─ Week 5-12:  Refinement, Testing, Documentation          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Success Metrics

### Quick Wins Success
- [ ] Security issues detected and remediated
- [ ] Config diff provides useful troubleshooting info
- [ ] EFS and ElastiCache resources tracked
- [ ] Positive user feedback

### Phase 1 Success
- [ ] Restoration capabilities working
- [ ] Multi-account deployments enabled
- [ ] Security baseline established
- [ ] Config drift details actionable

### Phase 2 Success
- [ ] Resource-level cost attribution working
- [ ] Baseline vs delta cost split accurate
- [ ] Scheduled snapshots running automatically
- [ ] Tag compliance >80%

### Phase 3 Success
- [ ] Service coverage >35 AWS services
- [ ] AWS Config integration working
- [ ] All major compute/storage/database services covered

### Phase 4 Success
- [ ] Dependency analysis prevents bad deletions
- [ ] Compliance reporting generated
- [ ] WAF assessment scores calculated
- [ ] TUI provides better UX

---

## 💡 Implementation Tips

### Quick Start
1. **Start with Quick Wins (#33)** - Immediate value
2. **Then tackle Phase 1** - Critical missing features
3. **Use `/new-collector` command** - Accelerates service expansion
4. **Iterate based on user feedback** - Adjust priorities

### Development Workflow
1. Create feature branch from main
2. Implement feature following project patterns
3. Write tests (>80% coverage required)
4. Update documentation
5. Run `invoke quality` and `invoke test`
6. Create PR referencing GitHub issue
7. Merge after review

### Using Claude Code Features
- **`/new-collector`** - Generate new service collectors quickly
- **Pre-commit hook** - Ensures quality automatically
- **Coverage guardian** - Prevents regression
- **Release workflow** - Streamlines releases

---

## 🔗 Related Documentation

- [GitHub Issues](https://github.com/troylar/aws-inventory-manager/issues)
- [README.md](README.md) - Project overview
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development guidelines
- [CLAUDE.md](CLAUDE.md) - Development instructions

---

## 📝 Issue Index

### Phase 1: Core Gaps
- #14 - Resource Cleanup/Restoration
- #15 - Configuration Drift Details
- #16 - Multi-Account & Organizations Support
- #17 - Security Posture Scanning

### Phase 2: Cost & Automation
- #18 - Resource-Level Cost Estimation
- #19 - Baseline vs Delta Cost Attribution
- #20 - Cost Anomaly Detection & Optimization
- #21 - Scheduled Snapshots & Automation
- #22 - Tag Governance & Enforcement

### Phase 3: Service Expansion
- #23 - Add EFS Collector
- #24 - Add ElastiCache Collector
- #25 - Add Kinesis Collector
- #26 - Add Additional Services (Batch)
- #27 - AWS Config Integration
- #32 - Add Glue Collector

### Phase 4: Advanced Features
- #28 - Resource Dependencies & Relationships
- #29 - Compliance Reporting
- #30 - Well-Architected Framework Assessment
- #31 - Interactive TUI

### Quick Wins
- #33 - Quick Win Bundle (Security + Config + Services)

---

## 🤝 Contributing

We welcome contributions! To work on roadmap items:

1. Comment on the GitHub issue you're interested in
2. Fork the repository
3. Create a feature branch
4. Implement the feature
5. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## 📞 Feedback

Have ideas for the roadmap?

- Create a [GitHub Issue](https://github.com/troylar/aws-inventory-manager/issues/new)
- Comment on existing roadmap issues
- Join discussions on planned features

---

**Version:** 1.0
**Status:** Active Development
**Next Review:** End of Q1 2025
