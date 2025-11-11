# AWS Resource Deletion Research - Executive Summary

## Overview

This document summarizes research on AWS resource deletion APIs and best practices for all 27 AWS services supported by aws-inventory-manager. The research is intended to support implementation of a resource cleanup/restoration feature that deletes AWS resources created after a baseline snapshot.

## Key Findings

### 1. Deletion Complexity Varies Significantly by Service

**Simple Services** (Straightforward deletion):
- SQS Queues - immediate, no recovery
- SNS Topics - immediate, auto-removes subscriptions
- Lambda Functions - straightforward if no event mappings
- S3 Objects - straightforward (buckets are complex)
- CloudWatch Logs - immediate deletion

**Complex Services** (Multiple prerequisites):
- S3 Buckets - must empty all versions/delete markers, handle object lock, MFA delete
- RDS Instances - disable deletion protection, handle final snapshots, check replicas
- EC2 Resources - cascading dependencies (instances → volumes → VPC)
- IAM Resources - must detach policies, remove from groups, delete keys/MFA
- ECS/EKS - must scale down services/node groups before deletion
- CloudFormation - respects DeletionPolicy, handles nested stacks

**AWS-Managed** (Cannot delete):
- AWS-managed policies and service-linked roles (IAM)
- Default VPCs and default security groups
- AWS-managed KMS keys
- Platform endpoints (SNS)

### 2. All Services Have Protection Mechanisms

| Service | Protection Type | How to Disable |
|---------|-----------------|----------------|
| RDS | Deletion Protection Flag | modify_db_instance(DeletionProtection=False) |
| EC2 Instance | Termination Protection | modify_instance_attribute(DisableApiTermination={'Value': False}) |
| CloudFormation | Stack Policy | update_stack_policy() |
| S3 | Object Lock, MFA Delete | put_bucket_versioning() |
| DynamoDB | Table must be active | Wait for active state |
| ECS Service | Desired task count > 0 | update_service(desiredCount=0) |

### 3. Recovery Windows Exist for Critical Services

Only **2 services** have built-in recovery periods:
- **Secrets Manager**: 7-30 day recovery window (can skip with ForceDeleteWithoutRecovery=True)
- **KMS Keys**: 7-30 day deletion schedule (minimum 7 days)

All other services either:
- Delete immediately with no recovery (SQS, S3, most services)
- Create final snapshots (RDS, ElastiCache) that persist separately
- Have CloudFormation DeletionPolicy=Retain option

### 4. Dependency Resolution is Essential

**Critical Deletion Order**:
1. **Layer 1 - Application/Compute**: EC2, Lambda, ECS services (can be deleted independently)
2. **Layer 2 - Data**: RDS, DynamoDB, S3, EFS (may need final snapshots)
3. **Layer 3 - Messaging**: SQS, SNS, EventBridge (auto-resolve dependencies)
4. **Layer 4 - Networking**: VPC, subnets, security groups (must delete in reverse order)
5. **Layer 5 - Config/Metadata**: IAM, KMS, CloudFormation (global impact, delete last)

**Key Dependency Patterns**:
- VPC → Subnets → Network Interfaces → Security Groups
- RDS Cluster → DB Instances → Parameter Groups
- ECS Cluster → Services → Task Definitions
- EKS Cluster → Node Groups → Addons
- IAM User → Access Keys, MFA Devices, Login Profiles

### 5. Error Patterns Are Consistent Across Services

**Common Error Categories**:

1. **Dependency Errors** (RecoveryStrategy: Resolve dependencies recursively)
   - InvalidGroup.InUse / InvalidVolume.InUse
   - BucketNotEmpty / ResourceInUse
   - ClusterContainsServices / ServiceNotEmpty
   - HostedZoneNotEmpty

2. **Permission Errors** (RecoveryStrategy: Check IAM policy and resource policy)
   - UnauthorizedOperation / AccessDenied
   - NotAuthorized / InvalidPermission
   - AuthFailure.ServiceLinked

3. **State Errors** (RecoveryStrategy: Wait for stable state or disable protections)
   - InvalidDBInstanceState / InvalidCacheClusterStateFault
   - InvalidVpcEndpointState / InvalidStateException
   - ServiceUnavailable (temporary)

4. **Resource Not Found** (RecoveryStrategy: Log and continue - resource already deleted)
   - ResourceNotFoundException / NoSuchBucket / InvalidInstanceID.NotFound
   - DBInstanceNotFound / ClusterNotFound

5. **Rate Limit** (RecoveryStrategy: Implement exponential backoff)
   - ThrottlingException / RequestThrottled / SlowDown

### 6. Batch Operations Improve Efficiency

Services with native batch deletion support:
- **S3**: delete_objects (batch up to 1000 objects)
- **SQS**: delete_message_batch (batch up to 10 messages)
- **DynamoDB**: batch_write_item (batch up to 25 items)
- **EC2**: terminate_instances, delete_snapshots (accept multiple IDs)
- **IAM**: No batch, must delete individually
- **RDS**: No batch, must delete individually

### 7. AWS-Specific Constraints

**Never Delete Without Verification**:
- Default VPCs (aws:cloudformation:stack-name tag or default VPC indicator)
- AWS-managed policies (arn:aws:iam::aws:policy/*)
- Service-linked roles (created by AWS services)
- System metrics (CloudWatch)
- Default security groups

**Special Handling Required**:
- **S3 Versioned Buckets**: Must delete both current versions AND delete markers
- **RDS Read Replicas**: Must delete replicas before source instance
- **Lambda Event Mappings**: Must delete before function
- **ECS Task Definitions**: Don't need to delete, only deregister if needed
- **KMS Keys**: Deletion is scheduled, not immediate
- **Secrets Manager**: Recovery window delays actual deletion

### 8. Implementation Checklist

```
Pre-Deletion:
- [ ] Create baseline snapshot of current state
- [ ] Filter resources created after baseline by timestamp
- [ ] Validate all resources are safe to delete (not AWS-managed)
- [ ] Run dry-run to show what will be deleted
- [ ] Get user confirmation before proceeding
- [ ] Log all deletion attempts for audit trail

Deletion Phase:
- [ ] Process Tier 1 resources (Compute/Application)
  - [ ] Disable EC2 termination protection
  - [ ] Delete Lambda event mappings before functions
  - [ ] Scale ECS services to 0 before deletion
- [ ] Process Tier 2 resources (Data)
  - [ ] Disable RDS deletion protection
  - [ ] Create final RDS snapshots if needed
  - [ ] Empty S3 buckets completely
- [ ] Process Tier 3 resources (Messaging/Networking)
  - [ ] Remove EventBridge targets before deleting rules
  - [ ] Delete VPC resources in reverse dependency order
- [ ] Process Tier 4 resources (Configuration/Metadata)
  - [ ] Detach IAM policies before deleting
  - [ ] Schedule KMS key deletion (not immediate)
  - [ ] Handle CloudFormation stacks by policy

Post-Deletion:
- [ ] Wait for async operations to complete (waiters)
- [ ] Verify resources are gone (list and check)
- [ ] Check for any orphaned resources
- [ ] Review logs for failed deletions
- [ ] Report results to user
```

---

## Service-Specific Implementation Notes

### High Priority Services (Most Used)

**EC2 - Multiple Resource Types**
- Instances: terminate, check termination protection
- Volumes: delete after instances (if not auto-managed)
- VPCs: delete last, after all network resources
- Security Groups: verify no in-use instances
- Subnets: must be empty (no ENIs)
- Action: Implement dependency resolver for EC2 resources

**S3 - Most Complex**
- List all object versions and delete markers separately
- Handle versioned buckets (current + delete markers)
- Check for object lock, legal hold, MFA delete
- Delete bucket policies first
- Action: Implement comprehensive S3 bucket cleanup utility

**RDS - Database Critical**
- Disable deletion protection before delete
- Handle final snapshot creation
- Delete read replicas before source
- Use SkipFinalSnapshot=True to skip snapshots
- Action: Implement pre-check for deletion protection

**Lambda - Dependency Chain**
- Delete event source mappings first
- Delete aliases first
- Cannot delete $LATEST version
- Action: Implement event mapping auto-detection

**IAM - Global and Permanent**
- Detach all policies before deletion
- Remove user from groups
- Delete access keys and MFA
- Never delete AWS-managed resources
- Action: Add AWS-managed policy detection

### Medium Priority Services

**DynamoDB**: Monitor table state (must be ACTIVE), delete backups separately
**ECS**: Scale services to 0 first, then delete
**EKS**: Delete node groups and addons before cluster
**VPC Endpoints**: Verify no critical routes
**CloudFormation**: Respect DeletionPolicy attribute
**CloudWatch**: Logs deleted with group, rules need target removal

### Lower Priority Services

**SNS/SQS**: Straightforward, minimal prerequisites
**Route53**: Delete records before zone, except NS/SOA
**API Gateway**: Straightforward deletion
**Secrets Manager**: Consider recovery window
**KMS**: Schedule deletion, don't expect immediate deletion
**EventBridge**: Remove targets before rule deletion

---

## Error Handling Strategy

### Recommended Retry Logic

```
1st Attempt: Delete resource
   ├─ Success: Log and continue
   ├─ Dependency Error: Find deps → Delete deps recursively → Retry
   ├─ Permission Error: Log error, fail, don't retry
   ├─ State Error: Wait 5-10 seconds → Retry (max 3 attempts)
   ├─ Not Found: Log as already deleted, continue
   └─ Rate Limit: Exponential backoff (1s, 2s, 4s, max 5 attempts)
```

### Exception Handling by Category

**Dependency Errors**: Recursive deletion
- InvalidGroup.InUse → Find instance using group → Delete instance first
- BucketNotEmpty → List and delete all objects → Retry
- ResourceInUse → Find dependent resource → Delete dependent first

**Permission Errors**: Fail immediately
- UnauthorizedOperation → Check IAM policy
- AccessDenied → Check resource policy
- Cannot auto-recover

**State Errors**: Wait and retry
- InvalidDBInstanceState → Wait for state to become AVAILABLE → Retry
- InvalidCacheClusterStateFault → Wait for state stability → Retry

**Not Found**: Log and continue
- ResourceNotFoundException → Already deleted, not an error
- No retry needed

**Rate Limit**: Backoff and retry
- ThrottlingException → Exponential backoff → Retry
- RequestThrottled → Wait and retry

---

## Security & Compliance Considerations

1. **Audit Trail**: Log ALL deletion operations with timestamp, user, resource, result
2. **Confirmation**: Require explicit user confirmation before actual deletion
3. **Dry-Run Mode**: Always support --dry-run to preview deletions
4. **Rollback Option**: Consider creating snapshots before deleting critical data
5. **Protected Resources**: Implement override mechanism for protected resources (with extra confirmation)
6. **Baseline Validation**: Verify timestamp comparison to avoid deleting baseline resources
7. **Final Snapshots**: Always create final snapshots for stateful resources (RDS, ElastiCache)

---

## Recommended Implementation Phases

### Phase 1: MVP (Core Services)
- EC2 (instances, volumes)
- S3 (buckets, objects)
- RDS (instances, clusters)
- Lambda (functions)
- IAM (roles, users, policies)

### Phase 2: Extended Coverage
- DynamoDB
- ECS (clusters, services)
- EKS (clusters, node groups)
- SQS/SNS
- CloudFormation

### Phase 3: Advanced Features
- VPC Components (detailed networking)
- Route53
- KMS
- Secrets Manager
- EventBridge
- All remaining services

---

## Tools and Resources

### AWS CLI Equivalents
Each boto3 method has AWS CLI equivalent:
```bash
# EC2 example
aws ec2 terminate-instances --instance-ids i-xxxxx

# RDS example
aws rds delete-db-instance --db-instance-identifier mydb

# S3 example
aws s3 rm s3://mybucket --recursive
```

### Boto3 Waiters Available
Services with built-in waiters for deletion:
- EC2: instance_terminated, volume_deleted
- RDS: db_instance_deleted
- CloudFormation: stack_delete_complete
- ECS: services_stable, clusters_inactive
- EKS: cluster_deleted

### Testing Resources
- Always test in development/staging first
- Use test resources with consistent naming (e.g., "test-delete-*")
- Create snapshots before testing on production data
- Verify deletion logs for audit trail

---

## Files Generated

1. **AWS_DELETION_RESEARCH.md** - Comprehensive reference for all 27 services
   - Deletion methods, prerequisites, non-deletable resources, common errors
   - Use as implementation reference when coding each service

2. **AWS_DELETION_IMPLEMENTATION_GUIDE.md** - Practical implementation patterns
   - Code examples, dependency resolution, error handling
   - Use as coding guide for feature implementation

3. **DELETION_RESEARCH_SUMMARY.md** (this file) - Executive summary
   - High-level overview, key findings, recommendations
   - Use for planning and decision-making

---

## Conclusion

AWS resource deletion is a complex but well-defined process. The key to successful implementation is:

1. **Understand dependencies**: Know which resources must be deleted first
2. **Handle errors gracefully**: Implement proper error handling for each error type
3. **Verify before deleting**: Always validate that resources are safe to delete
4. **Log everything**: Maintain audit trail for compliance
5. **Test thoroughly**: Test in non-production environments first
6. **Implement dry-run**: Always show what would be deleted before doing it
7. **Plan deletion order**: Process resources in correct layers to avoid dependencies

The research provided covers all 27 supported AWS services with specific guidance for deletion methods, prerequisites, common errors, and implementation patterns. Use this as the foundation for the resource cleanup feature implementation.
