# AWS Resource Deletion Implementation Guide

## Summary for Resource Cleanup Feature

This guide provides practical implementation guidance for the resource cleanup/restoration feature that deletes AWS resources created after a baseline snapshot.

---

## Quick Reference: Deletion Methods by Service

| Service | Method | Key Consideration |
|---------|--------|-------------------|
| EC2 Instance | terminate_instances | Must disable termination protection |
| EC2 Volume | delete_volume | Must not be in-use |
| EC2 VPC | delete_vpc | Must delete all dependencies first |
| EC2 Security Group | delete_security_group | Must not be in-use |
| EC2 Subnet | delete_subnet | Must not have resources |
| S3 Bucket | delete_bucket | Must empty bucket first |
| RDS Instance | delete_db_instance | Can create final snapshot |
| RDS Cluster | delete_db_cluster | Must delete instances first |
| Lambda Function | delete_function | Must delete event mappings first |
| Lambda Layer | delete_layer_version | Only versions, not layer itself |
| IAM Role | delete_role | Must remove policies first |
| IAM User | delete_user | Must remove keys, MFA, login profile |
| IAM Policy | delete_policy | Must detach from entities first |
| DynamoDB Table | delete_table | Must be active, not creating |
| SQS Queue | delete_queue | Immediate deletion, no recovery |
| SNS Topic | delete_topic | Subscriptions auto-removed |
| ECS Cluster | delete_cluster | Must delete services first |
| ECS Service | delete_service | Must scale to 0 tasks first |
| ECS Task Definition | deregister_task_definition | Can leave active revisions |
| EKS Cluster | delete_cluster | Must delete node groups first |
| CloudWatch Log Group | delete_log_group | Cannot recover deleted logs |
| Route53 Hosted Zone | delete_hosted_zone | Must delete non-NS/SOA records |
| API Gateway API | delete_rest_api | Stages auto-removed |
| KMS Key | schedule_key_deletion | 7-30 day pending window |
| EventBridge Rule | delete_rule | Must remove targets first |
| Secrets Manager Secret | delete_secret | 7-30 day recovery window (optional) |
| CloudFormation Stack | delete_stack | Respects DeletionPolicy attribute |

---

## Service Dependencies and Deletion Order

### Tier 1: Compute & Application Layer (Delete First)
These have no dependencies on other resources for deletion.

**EC2 Instances**
```python
# Must disable termination protection first
ec2.modify_instance_attribute(
    InstanceId=instance_id,
    DisableApiTermination={'Value': False}
)

# Then terminate
ec2.terminate_instances(InstanceIds=[instance_id])
```

**Lambda Functions**
```python
# Delete event source mappings first
for mapping in lambda_client.list_event_source_mappings(FunctionName=function_name)['EventSourceMappings']:
    lambda_client.delete_event_source_mapping(UUID=mapping['UUID'])

# Delete aliases
for alias in lambda_client.list_aliases(FunctionName=function_name)['Aliases']:
    lambda_client.delete_alias(FunctionName=function_name, Name=alias['Name'])

# Then delete function
lambda_client.delete_function(FunctionName=function_name)
```

**ECS Services**
```python
# Scale service to 0 first
ecs.update_service(cluster=cluster_name, service=service_name, desiredCount=0)

# Wait for scale down to complete
waiter = ecs.get_waiter('services_stable')
waiter.wait(cluster=cluster_name, services=[service_name])

# Then delete service
ecs.delete_service(cluster=cluster_name, service=service_name)
```

### Tier 2: Data Layer (Delete Second)
These typically have no dependencies but may need final snapshots.

**RDS Instances**
```python
# Disable deletion protection first
rds.modify_db_instance(
    DBInstanceIdentifier=db_id,
    DeletionProtection=False
)

# Delete with optional final snapshot
rds.delete_db_instance(
    DBInstanceIdentifier=db_id,
    SkipFinalSnapshot=False,
    FinalDBSnapshotIdentifier=f"{db_id}-final-snapshot"
)
```

**DynamoDB Tables**
```python
# Check if table is active
table = dynamodb.describe_table(TableName=table_name)
if table['Table']['TableStatus'] != 'ACTIVE':
    # Wait for it to become active
    waiter = dynamodb.get_waiter('table_exists')
    waiter.wait(TableName=table_name)

# Delete table
dynamodb.delete_table(TableName=table_name)
```

**S3 Buckets** (Most Complex)
```python
# List and delete all objects (including versions)
paginator = s3.get_paginator('list_object_versions')
for page in paginator.paginate(Bucket=bucket_name):
    for obj in page.get('Versions', []):
        s3.delete_object(Bucket=bucket_name, Key=obj['Key'], VersionId=obj['VersionId'])
    for obj in page.get('DeleteMarkers', []):
        s3.delete_object(Bucket=bucket_name, Key=obj['Key'], VersionId=obj['VersionId'])

# Remove bucket policy
try:
    s3.delete_bucket_policy(Bucket=bucket_name)
except s3.exceptions.NoSuchBucketPolicy:
    pass

# Disable MFA delete if enabled
try:
    s3.put_bucket_versioning(
        Bucket=bucket_name,
        VersioningConfiguration={'Status': 'Suspended', 'MFADelete': 'Disabled'}
    )
except:
    pass  # Ignore if not configured

# Delete bucket
s3.delete_bucket(Bucket=bucket_name)
```

### Tier 3: Networking & Messaging (Delete Third)

**VPC Components**
```python
# Must delete in correct order
# 1. Delete load balancers first
# 2. Delete ENIs (network interfaces)
# 3. Delete security groups (except default)
# 4. Delete subnets
# 5. Delete internet gateways
# 6. Delete route tables
# 7. Delete VPC

# Example for security group:
ec2.delete_security_group(GroupId=sg_id)  # Will fail if in-use
```

**SQS Queues**
```python
# Queue deletion is straightforward
sqs.delete_queue(QueueUrl=queue_url)
```

**SNS Topics**
```python
# Subscriptions are auto-removed
sns.delete_topic(TopicArn=topic_arn)
```

### Tier 4: Metadata & Configuration (Delete Last)

**IAM Resources** (Most Careful - Global Impact)
```python
# Delete in reverse dependency order
# 1. Delete access keys and login profiles
iam.delete_access_key(UserName=user_name, AccessKeyId=key_id)
iam.delete_login_profile(UserName=user_name)

# 2. Delete MFA devices
iam.deactivate_mfa_device(UserName=user_name, SerialNumber=device_serial)

# 3. Remove from groups
iam.remove_user_from_group(GroupName=group_name, UserName=user_name)

# 4. Detach policies
for policy in iam.list_attached_user_policies(UserName=user_name)['AttachedPolicies']:
    iam.detach_user_policy(UserName=user_name, PolicyArn=policy['PolicyArn'])

# 5. Delete inline policies
for policy in iam.list_user_policies(UserName=user_name)['PolicyNames']:
    iam.delete_user_policy(UserName=user_name, PolicyName=policy)

# 6. Delete user
iam.delete_user(UserName=user_name)
```

**KMS Keys** (Scheduled Deletion)
```python
# Schedule key deletion (not immediate)
kms.schedule_key_deletion(KeyId=key_id, PendingWindowInDays=7)  # Minimum 7 days
```

**CloudFormation Stacks**
```python
# Stack deletion respects DeletionPolicy on resources
cloudformation.delete_stack(StackName=stack_name)

# Wait for completion
waiter = cloudformation.get_waiter('stack_delete_complete')
waiter.wait(StackName=stack_name)
```

---

## Implementation Pattern: Dependency Resolution

### Recommended Function Structure

```python
def delete_resource(resource_type: str, resource_id: str, client) -> bool:
    """
    Delete a single resource with automatic dependency resolution.

    Returns True if successful, False if failed or skipped.
    """
    try:
        # 1. Check if resource is deletable
        if not is_deletable(resource_type, resource_id, client):
            logger.info(f"Skipping non-deletable resource: {resource_type}/{resource_id}")
            return False

        # 2. Resolve dependencies
        dependencies = find_dependencies(resource_type, resource_id, client)
        for dep_type, dep_id in dependencies:
            delete_resource(dep_type, dep_id, client)

        # 3. Perform pre-deletion steps (disable protections, etc.)
        prepare_for_deletion(resource_type, resource_id, client)

        # 4. Delete the resource
        invoke_delete_method(resource_type, resource_id, client)

        # 5. Wait for async operations if needed
        wait_for_deletion(resource_type, resource_id, client)

        logger.info(f"Successfully deleted {resource_type}/{resource_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to delete {resource_type}/{resource_id}: {e}")
        return False


def is_deletable(resource_type: str, resource_id: str, client) -> bool:
    """Check if resource should be deleted (not AWS-managed, etc.)"""
    non_deletable_patterns = {
        'EC2::VPC': ['vpc-default'],
        'IAM::Policy': ['arn:aws:iam::aws:'],
        'IAM::Role': ['service-linked-role-prefix'],
        'S3::Bucket': ['aws-managed-bucket-pattern'],
    }

    for pattern in non_deletable_patterns.get(resource_type, []):
        if pattern in resource_id:
            return False

    return True


def find_dependencies(resource_type: str, resource_id: str, client) -> List[Tuple[str, str]]:
    """Return list of dependent resources that must be deleted first"""
    dependencies = []

    if resource_type == 'EC2::VPC':
        # Find and depend on subnets, security groups, etc.
        dependencies.extend([
            ('EC2::Subnet', subnet_id)
            for subnet_id in get_vpc_subnets(resource_id, client)
        ])
        dependencies.extend([
            ('EC2::SecurityGroup', sg_id)
            for sg_id in get_vpc_security_groups(resource_id, client)
        ])

    elif resource_type == 'IAM::User':
        # Depend on access keys and other attributes
        dependencies.extend([
            ('IAM::AccessKey', key_id)
            for key_id in get_user_access_keys(resource_id, client)
        ])

    # ... more service-specific dependency resolution

    return dependencies


def prepare_for_deletion(resource_type: str, resource_id: str, client) -> None:
    """Perform pre-deletion operations (disable protections, scale down, etc.)"""

    if resource_type == 'EC2::Instance':
        ec2 = client
        ec2.modify_instance_attribute(
            InstanceId=resource_id,
            DisableApiTermination={'Value': False}
        )

    elif resource_type == 'RDS::DBInstance':
        rds = client
        rds.modify_db_instance(
            DBInstanceIdentifier=resource_id,
            DeletionProtection=False
        )

    elif resource_type == 'ECS::Service':
        ecs = client
        cluster, service = resource_id.split('/')
        ecs.update_service(cluster=cluster, service=service, desiredCount=0)
        # Wait for scale down
        waiter = ecs.get_waiter('services_stable')
        waiter.wait(cluster=cluster, services=[service])

    # ... more service-specific preparations


def invoke_delete_method(resource_type: str, resource_id: str, client) -> None:
    """Call the appropriate AWS API deletion method"""

    deletion_methods = {
        'EC2::Instance': lambda rid, c: c.terminate_instances(InstanceIds=[rid]),
        'EC2::Volume': lambda rid, c: c.delete_volume(VolumeId=rid),
        'EC2::VPC': lambda rid, c: c.delete_vpc(VpcId=rid),
        'EC2::SecurityGroup': lambda rid, c: c.delete_security_group(GroupId=rid),
        'S3::Bucket': lambda rid, c: c.delete_bucket(Bucket=rid),
        'RDS::DBInstance': lambda rid, c: c.delete_db_instance(
            DBInstanceIdentifier=rid, SkipFinalSnapshot=True
        ),
        'Lambda::Function': lambda rid, c: c.delete_function(FunctionName=rid),
        'DynamoDB::Table': lambda rid, c: c.delete_table(TableName=rid),
        'SQS::Queue': lambda rid, c: c.delete_queue(QueueUrl=rid),
        'SNS::Topic': lambda rid, c: c.delete_topic(TopicArn=rid),
        'IAM::Role': lambda rid, c: c.delete_role(RoleName=rid),
        'IAM::User': lambda rid, c: c.delete_user(UserName=rid),
        # ... more services
    }

    method = deletion_methods.get(resource_type)
    if method:
        method(resource_id, client)
    else:
        raise ValueError(f"No deletion method for {resource_type}")


def wait_for_deletion(resource_type: str, resource_id: str, client) -> None:
    """Wait for async deletion operations to complete"""

    if resource_type == 'ECS::Cluster':
        # Wait for cluster to fully delete
        waiter = client.get_waiter('cluster_inactive')
        try:
            waiter.wait(clusters=[resource_id])
        except:
            pass  # Cluster might already be gone

    elif resource_type == 'CloudFormation::Stack':
        waiter = client.get_waiter('stack_delete_complete')
        waiter.wait(StackName=resource_id)

    # Most services complete deletion synchronously
```

---

## Error Handling Strategy

### Exception Mapping by Error Type

```python
DEPENDENCY_ERRORS = {
    'InvalidGroup.InUse',
    'InvalidVolume.InUse',
    'BucketNotEmpty',
    'ClusterContainsServices',
    'ResourceInUse',
    'InvalidDBClusterStateFault',
}

PERMISSION_ERRORS = {
    'UnauthorizedOperation',
    'AccessDenied',
    'NotAuthorized',
    'InvalidPermission',
}

STATE_ERRORS = {
    'InvalidDBInstanceState',
    'InvalidCacheClusterStateFault',
    'InvalidVpcEndpointState',
    'InvalidStateException',
}

RESOURCE_NOT_FOUND = {
    'InvalidInstanceID.NotFound',
    'DBInstanceNotFound',
    'NoSuchBucket',
    'ResourceNotFoundException',
}


def handle_deletion_error(resource_type: str, resource_id: str, error: Exception) -> bool:
    """
    Handle deletion errors appropriately.
    Returns True if error is recoverable, False if should skip/fail.
    """
    error_code = get_error_code(error)

    if error_code in RESOURCE_NOT_FOUND:
        logger.info(f"Resource {resource_type}/{resource_id} already deleted")
        return True  # Already gone, not an error

    elif error_code in DEPENDENCY_ERRORS:
        logger.error(f"Dependency error for {resource_type}/{resource_id}: {error}")
        return False  # Retry with dependency resolution

    elif error_code in PERMISSION_ERRORS:
        logger.error(f"Permission error for {resource_type}/{resource_id}: {error}")
        return False  # Cannot proceed without permissions

    elif error_code in STATE_ERRORS:
        logger.warning(f"State error for {resource_type}/{resource_id}, retrying...")
        return False  # Retry after waiting

    else:
        logger.error(f"Unexpected error for {resource_type}/{resource_id}: {error}")
        return False  # Unknown error, fail


def get_error_code(error: Exception) -> str:
    """Extract error code from boto3 exception"""
    if hasattr(error, 'response'):
        return error.response.get('Error', {}).get('Code', str(error))
    return str(error)
```

---

## Batch Deletion Pattern

For efficiency, process multiple resources of the same type together:

```python
def batch_delete_resources(
    resource_type: str,
    resource_ids: List[str],
    client,
    parallel: bool = False
) -> Dict[str, bool]:
    """
    Delete multiple resources of the same type.

    Returns dict mapping resource_id -> success boolean.
    """
    results = {}

    # Some services support batch operations
    if resource_type == 'SQS::Message':
        results.update(batch_delete_sqs_messages(resource_ids, client))

    elif resource_type == 'S3::Object':
        results.update(batch_delete_s3_objects(resource_ids, client))

    elif resource_type == 'IAM::AccessKey':
        results.update(batch_delete_access_keys(resource_ids, client))

    else:
        # Fall back to sequential deletion
        for resource_id in resource_ids:
            try:
                delete_resource(resource_type, resource_id, client)
                results[resource_id] = True
            except Exception as e:
                logger.error(f"Failed to delete {resource_type}/{resource_id}: {e}")
                results[resource_id] = False

    return results


def batch_delete_s3_objects(bucket_name: str, keys: List[str], s3_client) -> Dict[str, bool]:
    """S3 batch delete is much faster than individual deletes"""
    results = {key: True for key in keys}

    try:
        # Batch delete up to 1000 objects
        for i in range(0, len(keys), 1000):
            batch = keys[i:i+1000]
            s3_client.delete_objects(
                Bucket=bucket_name,
                Delete={'Objects': [{'Key': key} for key in batch]}
            )
    except Exception as e:
        logger.error(f"Batch delete failed: {e}")
        # Mark all as failed
        results = {key: False for key in keys}

    return results
```

---

## Testing Deletion Logic

### Pre-Deletion Validation Checklist

```python
def validate_deletion_plan(
    resources: List[Dict[str, str]],  # [{type, id}, ...]
    baseline_timestamp: datetime,
    client
) -> List[str]:
    """
    Validate resources created after baseline before deletion.
    Returns list of validation errors.
    """
    errors = []

    for resource in resources:
        # 1. Verify created_at is after baseline
        created_at = get_resource_creation_time(resource['type'], resource['id'], client)
        if created_at < baseline_timestamp:
            errors.append(
                f"Resource {resource['type']}/{resource['id']} "
                f"created before baseline ({created_at})"
            )

        # 2. Check for non-deletable resources
        if is_deletable(resource['type'], resource['id'], client):
            errors.append(
                f"Resource {resource['type']}/{resource['id']} is non-deletable"
            )

        # 3. Warn about critical resources
        if is_critical_resource(resource['type'], resource['id']):
            logger.warning(
                f"Critical resource marked for deletion: "
                f"{resource['type']}/{resource['id']}"
            )

    return errors


def dry_run_deletion(
    resources: List[Dict[str, str]],
    client
) -> Dict[str, List[str]]:
    """
    Perform dry-run deletion (list resources that would be deleted).
    Returns categorized results for review.
    """
    results = {
        'would_delete': [],
        'dependencies_found': [],
        'non_deletable': [],
        'errors': [],
    }

    for resource in resources:
        if not is_deletable(resource['type'], resource['id'], client):
            results['non_deletable'].append(f"{resource['type']}/{resource['id']}")
        else:
            deps = find_dependencies(resource['type'], resource['id'], client)
            if deps:
                results['dependencies_found'].append({
                    'resource': f"{resource['type']}/{resource['id']}",
                    'dependencies': deps,
                })
            else:
                results['would_delete'].append(f"{resource['type']}/{resource['id']}")

    return results
```

---

## Key Implementation Notes

1. **Always Validate Before Deleting**: Check creation timestamp against baseline
2. **Disable Protections First**: RDS deletion protection, EC2 termination protection
3. **Handle Dependencies Recursively**: Automatically resolve and delete dependent resources
4. **Use Batch Operations**: S3, SQS, and other services support batch deletes for efficiency
5. **Implement Async Waiting**: Use boto3 waiters for resources with asynchronous deletion
6. **Log Everything**: Maintain audit trail of all deletions for compliance
7. **Provide Dry-Run Mode**: Always show what would be deleted before actual deletion
8. **Handle Rate Limiting**: Implement exponential backoff for API throttling
9. **Skip AWS-Managed Resources**: Never delete AWS-managed policies, service-linked roles
10. **Safe Global Services**: Be extra careful with global services (IAM, S3, KMS)
11. **Consider Recovery Windows**: Secrets Manager and KMS have recovery periods
12. **Test Thoroughly**: Test in non-production with known safe resources first
