# AWS Resource Deletion APIs and Best Practices

## Overview
This document provides comprehensive deletion guidance for 27 AWS services currently supported by aws-inventory-manager. Research covers boto3 deletion methods, prerequisites, non-deletable resources, and common error patterns.

---

## EC2 (Elastic Compute Cloud)

**Deletion Methods**:
- Instance → ec2.terminate_instances(InstanceIds=[id])
- Volume (EBS) → ec2.delete_volume(VolumeId=id)
- VPC → ec2.delete_vpc(VpcId=id)
- Security Group → ec2.delete_security_group(GroupId=id) or GroupName=name
- Subnet → ec2.delete_subnet(SubnetId=id)
- Network Interface → ec2.delete_network_interface(NetworkInterfaceId=id)
- Internet Gateway → ec2.detach_internet_gateway(InternetGatewayId=id, VpcId=vpc_id) then ec2.delete_internet_gateway(InternetGatewayId=id)
- Route Table → ec2.delete_route_table(RouteTableId=id)
- Elastic IP → ec2.release_address(AllocationId=id) or PublicIp=ip

**Prerequisites**:
- Instances must be stopped before volumes can be deleted (if attached)
- Must disable termination protection on instances first: ec2.modify_instance_attribute(InstanceId=id, DisableApiTermination={'Value': False})
- Must delete instances and ENIs before deleting VPC/subnets
- Must remove routes from route table before deletion
- VPC must have default security group, DHCP options set, and no dependencies
- Volumes must not be in-use or encrypted with restricted KMS keys
- Snapshot cleanup required before volume deletion if snapshots reference the volume

**Non-deletable Resources**:
- Default VPC (vpc-*) - AWS creates this and recommends not deleting
- VPCs with aws:cloudformation:stack-name tag (managed by CloudFormation)
- Default security groups (sg-*) within default VPC
- Reserved Instances (handled separately)
- Spot Instance Requests that are active
- Root volumes attached to running instances

**Common Errors**:
- InvalidInstanceID.InUse: Instance still running, termination protection enabled
- InvalidVolume.InUse: Volume attached to running instance
- InvalidGroup.InUse: Security group in use by EC2 instance or network interface
- InvalidVpcID.NotFound or DependencyViolation: VPC has dependencies
- InvalidParameterValue: Incorrect instance/volume/group ID format
- UnauthorizedOperation: Insufficient IAM permissions
- InvalidNetworkInterfaceID.InUse: ENI attached to instance
- AuthFailure.ServiceLinked: Service-linked role missing for some operations

---

## S3 (Simple Storage Service)

**Deletion Methods**:
- Bucket → s3.delete_bucket(Bucket=bucket_name)
- Object → s3.delete_object(Bucket=bucket_name, Key=key) or s3.delete_objects(Bucket=bucket_name, Delete={Objects: [{Key: key}]})
- Lifecycle policy → s3.delete_bucket_lifecycle(Bucket=bucket_name) [deprecated, use delete_bucket_lifecycle_configuration]
- Access control → s3.put_bucket_acl(Bucket=bucket_name, ACL='private')

**Prerequisites**:
- Bucket must be empty before deletion (all versions, all delete markers)
- Must handle versioned buckets: delete all current versions AND all delete markers
- MFA delete must be disabled if enabled: s3.put_bucket_versioning(Bucket=bucket_name, VersioningConfiguration={'Status': 'Suspended', 'MFADelete': 'Disabled'})
- Must remove bucket policies: s3.delete_bucket_policy(Bucket=bucket_name)
- Must clear object lock retention if configured (object_lock_retain_until_date)
- Must remove object lock governance mode
- Gateway VPC endpoints blocking deletion must be removed
- Object lock retention/legal hold prevents deletion

**Non-deletable Resources**:
- Buckets with object lock enabled (ObjectLockEnabled=true)
- Buckets with active cross-region replication
- Buckets with objects under legal hold
- Buckets with objects under object retention that hasn't expired
- AWS-managed buckets (created by AWS services)

**Common Errors**:
- NoSuchBucket: Bucket doesn't exist or already deleted
- BucketNotEmpty: Bucket contains objects (including delete markers in versioned buckets)
- InvalidBucketName: Bucket name invalid or reserved
- BucketAlreadyOwnedByYou: Bucket owned by requesting account
- ServiceUnavailable: S3 service issue
- Access Denied: Missing s3:DeleteBucket permission or bucket policies block access
- InvalidArgument: MFA delete enabled requiring MFA token
- NoSuchKey: Object key doesn't exist
- SlowDown: Rate limit exceeded

---

## RDS (Relational Database Service)

**Deletion Methods**:
- DB Instance → rds.delete_db_instance(DBInstanceIdentifier=id, SkipFinalSnapshot=False, FinalDBSnapshotIdentifier=snapshot_id)
- DB Cluster → rds.delete_db_cluster(DBClusterIdentifier=id, SkipFinalSnapshot=False, FinalDBSnapshotIdentifier=snapshot_id)
- DB Snapshot → rds.delete_db_snapshot(DBSnapshotIdentifier=id)
- DB Cluster Snapshot → rds.delete_db_cluster_snapshot(DBClusterSnapshotIdentifier=id)
- Parameter Group → rds.delete_db_parameter_group(DBParameterGroupName=name)
- Option Group → rds.delete_option_group(OptionGroupName=name)

**Prerequisites**:
- Must disable deletion protection first: rds.modify_db_instance(DBInstanceIdentifier=id, DeletionProtection=False)
- Must wait for backups to complete before deletion
- Must handle final snapshots: SkipFinalSnapshot=True will not create snapshot
- Multi-AZ instances require disabling multi-AZ first (optional but cleaner)
- Read replicas must be deleted before source instance
- Parameter groups must be removed from all instances using them
- Option groups must be removed from all instances using them
- Cannot delete if automated backups are being created (wait for completion)
- Cannot delete DB cluster if it has database instances (must delete instances first)

**Non-deletable Resources**:
- AWS-managed parameter groups (default.*, aws.*)
- RDS Proxy targets (remove from target group first)
- DB instances with deletion protection enabled
- Automated backups (they're deleted when instance is deleted)
- Reserved DB instances

**Common Errors**:
- DBInstanceNotFound: DB instance doesn't exist
- InvalidDBInstanceState: Instance in wrong state (creating, deleting, rebooting)
- DBInstanceAlreadyExists: When trying to delete, if snapshot with same name exists
- InvalidDBClusterStateFault: Cluster has active instances
- AuthorizationNotFound: Incorrect parameter group/option group
- DBParameterGroupNotFoundFault: Parameter group doesn't exist
- InvalidDBParameterGroupState: Parameter group still in use
- DBSecurityGroupNotFoundFault: Security group missing
- SnapshotQuotaExceeded: Too many snapshots

---

## Lambda (Serverless Computing)

**Deletion Methods**:
- Function → lambda.delete_function(FunctionName=name)
- Layer Version → lambda.delete_layer_version(LayerName=name, VersionNumber=version)
- Event Source Mapping → lambda.delete_event_source_mapping(UUID=uuid)
- Alias → lambda.delete_alias(FunctionName=name, Name=alias_name)
- Code Signing Config → lambda.delete_code_signing_config(CodeSigningConfigArn=arn)

**Prerequisites**:
- All event source mappings must be deleted before function deletion
- All aliases must be deleted before function deletion
- Cannot delete $LATEST version (function itself is $LATEST)
- Aliases referencing the function must be deleted
- Reserved concurrency must be reset (automatic on deletion)
- VPC attached ENIs must be detached (automatic on deletion)
- Function must not be in use by other AWS services
- CodeGuru reviews must be dismissed if present
- Cannot delete if CloudFormation stack still references it

**Non-deletable Resources**:
- $LATEST version (implicit, always exists)
- AWS-managed layers
- Lambda versions that are concurrency-reserved
- Functions that are part of active CloudFormation stacks
- Functions referenced by unresolved EventBridge rules

**Common Errors**:
- FunctionNotFound: Function doesn't exist
- InvalidParameterValueException: Invalid function name format
- ServiceException: Lambda service issue
- TooManyRequestsException: Rate limit exceeded
- ResourceNotFoundException: Event source mapping doesn't exist
- ResourceConflictException: Function in use or state issue
- PolicyLengthExceededException: Resource policy too large
- CodeSigningConfigNotFound: Invalid code signing config
- PreconditionFailedException: Concurrency settings block deletion

---

## IAM (Identity and Access Management)

**Deletion Methods**:
- Role → iam.delete_role(RoleName=name)
- User → iam.delete_user(UserName=name)
- Group → iam.delete_group(GroupName=name)
- Customer Policy (attached) → iam.detach_user_policy(UserName=name, PolicyArn=arn) then iam.delete_policy(PolicyArn=arn)
- Inline Policy → iam.delete_user_policy(UserName=name, PolicyName=name) or delete_role_policy, delete_group_policy
- Access Key → iam.delete_access_key(UserName=name, AccessKeyId=key_id)
- MFA Device → iam.deactivate_mfa_device(UserName=name, SerialNumber=device_arn)
- Login Profile → iam.delete_login_profile(UserName=name)
- Instance Profile → iam.delete_instance_profile(InstanceProfileName=name)

**Prerequisites**:
- Must remove all inline policies before deleting user/role/group
- Must detach all customer-managed policies
- Must remove user from all groups first
- Must delete access keys and MFA devices before deleting user
- Must delete login profile before deleting user
- Must remove from instance profiles before deletion
- Must check for service-linked roles (cannot delete, AWS manages)
- Must check for assume role policies that reference the role
- Cannot delete roles in use by EC2 instances
- Trusted relationships (assume role policy) must be examined

**Non-deletable Resources**:
- AWS-managed policies (all policies starting with arn:aws:iam::aws:)
- Service-linked roles (created by AWS for service integration)
- Root user
- Default roles/users created by AWS
- Roles with active sessions

**Common Errors**:
- NoSuchEntity: User, role, or group doesn't exist
- DeleteConflict: User still has access keys, MFA devices, or group membership
- InvalidInput: Invalid policy syntax or parameter
- LimitExceeded: Policy version limit exceeded
- ServiceFailure: IAM service issue
- EntityAlreadyExists: User/role/group already exists
- InvalidParameterValue: Invalid role or policy name
- NotAuthorizedForSourceException: Principal not authorized
- PolicyNotAttachable: Policy cannot be attached to entity type
- PolicyNotDetachable: Cannot detach AWS-managed policies from custom roles

---

## DynamoDB (NoSQL Database)

**Deletion Methods**:
- Table → dynamodb.delete_table(TableName=name)
- Global Secondary Index (GSI) → dynamodb.update_table(TableName=name, GlobalSecondaryIndexUpdates=[{Delete: {IndexName: name}}])
- Local Secondary Index (LSI) → Cannot delete; must recreate table
- Backup → dynamodb.delete_backup(BackupArn=arn)
- Item → dynamodb.delete_item(TableName=name, Key={pk_attr: value})
- Global Table → dynamodb.delete_global_table(GlobalTableName=name)

**Prerequisites**:
- Table must be active (not creating, updating, or deleting)
- Cannot delete LSI without recreating table
- GSIs can be deleted but require table update
- Backups persist independently after deletion
- Global tables require special handling (delete replicas first)
- Point-in-time recovery must be disabled if active
- TTL must be disabled if configured
- Streams must be disabled if active
- Backups must be manually deleted if not needed

**Non-deletable Resources**:
- Tables in CloudFormation stacks (must delete stack)
- Backup history (backups persist after deletion)
- Stream records (deleted with table)
- Replicas in global tables (must remove replicas individually)
- Items cannot be individually "deleted" in traditional sense (just marked/removed)

**Common Errors**:
- ResourceNotFoundException: Table doesn't exist
- ResourceInUseException: Table in wrong state or has dependencies
- ValidationException: Invalid table name or parameter
- InternalServerError: DynamoDB service issue
- ProvisionedThroughputExceededException: Rate limit exceeded
- TransactionConflictException: Concurrent modification
- ItemCollectionSizeLimitExceededException: Item too large
- ConditionalCheckFailedException: Item already deleted or condition failed
- DuplicateTransactionError: Transaction has duplicate items
- BackupNotFoundException: Backup doesn't exist

---

## VPC Endpoints

**Deletion Methods**:
- VPC Endpoint → ec2.delete_vpc_endpoints(VpcEndpointIds=[id])
- VPC Endpoint Service Config → ec2.delete_vpc_endpoint_service_configurations(ServiceConfigurationIds=[id])

**Prerequisites**:
- VPC endpoint must be in available state
- Must remove endpoint service configuration first if deleting service
- Route tables with endpoint routes must have routes removed (automatic)
- Network ACLs referencing endpoint must be updated (automatic)
- Endpoint policy must be examined for critical routes
- Interface endpoints (ENIs) automatically clean up network interfaces
- S3 endpoints do not consume capacity

**Non-deletable Resources**:
- VPC endpoints created by CloudFormation stacks (delete stack)
- Default endpoints to S3 and DynamoDB
- Endpoints with active connections (will close on deletion)

**Common Errors**:
- InvalidVpcEndpointId.NotFound: VPC endpoint doesn't exist
- InvalidVpcEndpointState: Endpoint not in deletable state
- InvalidParameterValue: Invalid endpoint ID
- UnauthorizedOperation: Insufficient permissions
- ServiceNameNotFound: Service doesn't exist
- VpcEndpointServiceNotFound: Service config doesn't exist

---

## CloudFormation (Infrastructure as Code)

**Deletion Methods**:
- Stack → cloudformation.delete_stack(StackName=name)
- Stack Set → cloudformation.delete_stack_set(StackSetName=name)
- Stack Instances → cloudformation.delete_stack_instances(StackSetName=name, Accounts=[ids], Regions=[regions], RetainStacks=False)

**Prerequisites**:
- Stack must be in stable state (CREATE_COMPLETE, UPDATE_COMPLETE, etc.)
- Must delete stack instances before stack set
- Must delete all stack instances from stack set before deleting set
- DeletionPolicy attribute controls behavior of resources
- Resources with DeletionPolicy=Retain will persist after stack deletion
- Resources with DeletionPolicy=Snapshot will create final snapshots
- Nested stacks are automatically deleted with parent
- Must resolve any pending updates first
- Cannot delete stacks in UPDATE_IN_PROGRESS state

**Non-deletable Resources**:
- Stacks protected by stack policy (must update policy first)
- Resources with DeletionPolicy=Retain
- Snapshots created during deletion (unless SkipSnapshot specified)
- Nested stacks are deleted with parent (no independent deletion)

**Common Errors**:
- ValidationError: Stack doesn't exist or invalid name
- InvalidParameterValue: Invalid parameter in delete request
- AlreadyExistsException: Resource already exists
- InsufficientCapabilities: Template requires capabilities
- TypeNotFoundException: Custom resource type doesn't exist
- StackProtectionException: Stack has deletion protection
- ConditionalCheckFailedException: Stack policy blocks operation
- OperationIdAlreadyExistsException: Operation already in progress
- StillContainsResourcesException: Stack instances still exist

---

## ECR (Elastic Container Registry)

**Deletion Methods**:
- Repository → ecr.delete_repository(repositoryName=name, force=False)
- Image → ecr.batch_delete_image(repositoryName=name, imageIds=[{imageTag=tag}])
- Lifecycle Policy → ecr.delete_lifecycle_policy(repositoryName=name)

**Prerequisites**:
- Repository must be empty or force=True (force deletes all images)
- Images must exist before deletion attempt
- Cannot delete image if it's referenced by task definition
- Cannot delete image tagged as latest if in use
- Lifecycle policies are independent of images
- Repository policy must be examined
- Image scanning results persist after image deletion

**Non-deletable Resources**:
- Images in active use by ECS/EKS
- Images with immutable tags
- Default repositories created by AWS services
- Images stored in replicated repositories (remove replication rules first)

**Common Errors**:
- RepositoryNotFound: Repository doesn't exist
- ImageNotFound: Image doesn't exist
- RepositoryNotEmptyException: Repository has images (use force=True)
- InvalidParameterException: Invalid repository name or image ID
- LayerInaccessible: Base layer deleted or inaccessible
- ImageAlreadyExists: Image tag already exists
- UnsupportedImageType: Image format not supported
- InternalFailure: ECR service issue

---

## ECS (Elastic Container Service)

**Deletion Methods**:
- Cluster → ecs.delete_cluster(cluster=name)
- Service → ecs.delete_service(cluster=cluster_name, service=service_name, force=False)
- Task Definition → ecs.deregister_task_definition(taskDefinition=family:revision)
- Task Definition Family (all revisions) → Must deregister each revision individually

**Prerequisites**:
- Service must have 0 running tasks
- Must scale service to 0 before deletion: ecs.update_service(cluster=name, service=name, desiredCount=0)
- Must delete all services before deleting cluster
- Must deregister all task definitions (or leave them)
- Cluster can contain stopped instances
- Container instances must be drained (set to DRAINING state)
- CloudWatch logs persist after deletion
- Load balancer target groups must be removed from service first

**Non-deletable Resources**:
- EC2 instances in cluster (they persist, only cluster metadata deleted)
- CloudWatch logs (must delete separately)
- Container instances that don't exist (cannot deregister)
- Default cluster if it contains resources

**Common Errors**:
- ClusterNotFoundException: Cluster doesn't exist
- ServiceNotFoundException: Service doesn't exist
- InvalidParameterException: Invalid cluster or service name
- ClusterContainsServicesFault: Cluster has active services
- ClusterContainsContainerInstancesFault: Cluster has instances
- ServiceNotEmptyFault: Service has running tasks
- UnsupportedFeatureException: Feature not supported in task
- FailedServiceNotFound: Service dependency issue
- NotUpdatedException: Service in wrong state

---

## EKS (Elastic Kubernetes Service)

**Deletion Methods**:
- Cluster → eks.delete_cluster(name=cluster_name)
- Node Group → eks.delete_nodegroup(clusterName=cluster_name, nodegroupName=nodegroup_name)
- Addon → eks.delete_addon(clusterName=cluster_name, addonName=addon_name)

**Prerequisites**:
- Must delete all node groups before cluster
- Must delete all addons before cluster
- All pods must be drained from nodes (automatic on node group deletion)
- Persistent volumes must be manually handled
- Secrets encrypted with custom KMS keys must be decrypted first
- Service control policies may block deletion
- VPC and subnets persist after deletion
- Security groups persist after deletion
- IAM roles for service accounts must be deleted separately

**Non-deletable Resources**:
- Kubernetes API server backups
- VPC and subnets (created by cluster, persist after deletion)
- IAM roles (persist, must delete manually)
- ENIs associated with pods (cleaned up automatically)
- EBS volumes provisioned by cluster (must delete manually)

**Common Errors**:
- ResourceNotFoundException: Cluster or node group doesn't exist
- InvalidParameterException: Invalid cluster name
- ResourceInUseException: Cluster or node group has dependencies
- ServiceUnavailable: EKS service issue
- UnsupportedAddonModification: Cannot modify addon in transition
- InvalidIdentityProviderConfig: OIDC provider issue
- NotFound: Cluster status unknown
- ConflictException: Cluster in transition state
- AccessDenied: Insufficient permissions or service-linked role issue

---

## Secrets Manager (Secret Management)

**Deletion Methods**:
- Secret → secretsmanager.delete_secret(SecretId=secret_name, ForceDeleteWithoutRecovery=False, RecoveryWindowInDays=30)

**Prerequisites**:
- Secret can have recovery window (default 30 days) or immediate deletion (ForceDeleteWithoutRecovery=True)
- During recovery window, secret name is reserved and cannot be recreated
- Replication regions must be handled
- Resource-based policy must be examined
- Automatic rotation must be cancelled before deletion (automatic)
- No prerequisites beyond permission check, but consider recovery window
- Applications using the secret must be updated

**Non-deletable Resources**:
- Secrets managed by other AWS services
- Secrets in rotation lambda functions (but deletion is allowed)
- Secrets deleted and in recovery period (cannot recreate with same name)

**Common Errors**:
- ResourceNotFoundException: Secret doesn't exist
- InvalidRequestException: Invalid parameter or secret in deletion window
- InvalidParameterException: Invalid secret ID format
- DecryptionFailure: KMS key issue (secret in another region with different key)
- InternalServiceError: Secrets Manager service issue
- PreconditionNotMet: Recovery window still active
- AccessDenied: Insufficient permissions
- ServiceUnavailable: Service temporarily unavailable

---

## SQS (Simple Queue Service)

**Deletion Methods**:
- Queue → sqs.delete_queue(QueueUrl=queue_url)
- Message → sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=handle)
- Message Batch → sqs.delete_message_batch(QueueUrl=queue_url, Entries=[{Id: id, ReceiptHandle: handle}])

**Prerequisites**:
- Queue is immediately deleted (no recovery period like SNS)
- Messages in queue are lost upon deletion
- Messages must have been received (have ReceiptHandle) to be deleted
- Cannot delete messages from purged queue (must wait for queue recreation)
- Dead Letter Queue associations are removed
- Lambda event source mappings must be removed first
- No prerequisites for queue deletion itself

**Non-deletable Resources**:
- Messages in transit (being processed)
- Messages without ReceiptHandle (not received by consumer)
- Messages in FIFO queues without deduplication token

**Common Errors**:
- QueueDoesNotExist: Queue doesn't exist or in deletion process
- InvalidParameterValue: Invalid queue URL or parameters
- InvalidIdForBatch: Invalid message ID in batch delete
- BatchEntryIdsNotDistinct: Duplicate entry IDs in batch
- ReceiptHandleIsInvalid: Invalid or expired receipt handle
- ServiceUnavailable: SQS service issue
- RequestThrottled: Rate limit exceeded
- UnsupportedOperation: Cannot delete message from FIFO without message deduplication ID

---

## SNS (Simple Notification Service)

**Deletion Methods**:
- Topic → sns.delete_topic(TopicArn=topic_arn)
- Subscription → sns.unsubscribe(SubscriptionArn=subscription_arn)
- Topic Policy → sns.remove_permission(TopicArn=topic_arn, Label=label)

**Prerequisites**:
- Topic subscriptions are automatically removed when topic is deleted
- Messages in flight are lost (SNS is not a message queue)
- Topic name can be reused after deletion (unlike Secrets Manager)
- SMS attributes persist for account (delete SMS attributes separately)
- Platform endpoints must be removed before platform application deletion
- Cross-account topics must handle permissions first

**Non-deletable Resources**:
- Platform applications (must delete separately)
- Platform endpoints (must delete separately)
- FIFO topics with in-progress message deduplication

**Common Errors**:
- NotFound: Topic doesn't exist
- InvalidParameterValue: Invalid topic ARN
- AuthorizationError: Insufficient permissions
- InternalError: SNS service issue
- ServiceUnavailable: SNS service temporarily unavailable
- InvalidStateForOperation: Topic in wrong state
- TooManyEntries: Too many subscriptions in delete request
- InvalidSubscription: Subscription doesn't exist

---

## CloudWatch (Monitoring and Logging)

**Deletion Methods**:
- Log Group → logs.delete_log_group(logGroupName=name)
- Log Stream → logs.delete_log_stream(logGroupName=name, logStreamName=stream_name)
- Alarm → cloudwatch.delete_alarms(AlarmNames=[names])
- Dashboard → cloudwatch.delete_dashboards(DashboardNames=[names])
- Event Rule → events.delete_rule(Name=rule_name)

**Prerequisites**:
- Log streams are deleted with log group (no need to delete individually)
- Alarms must be disabled before deletion (automatic)
- Alarms in INSUFFICIENT_DATA state can be deleted
- Dashboards are immediately deleted (no recovery)
- Event rules must have targets removed first: events.remove_targets(Rule=name, Ids=[ids])
- Log groups with retention policies will expire logs on schedule
- Metric filters persist until log group is deleted
- Anomaly detectors must be deleted separately

**Non-deletable Resources**:
- Log groups created by AWS services (can be deleted but they may be recreated)
- System metrics (cannot be deleted, only disabled)
- Alarms created by other services (but can be deleted, service recreates if needed)
- Default event bus (cannot be deleted)

**Common Errors**:
- ResourceNotFoundException: Log group, stream, alarm, or rule doesn't exist
- InvalidParameterException: Invalid name or parameter
- InvalidParameterValue: Invalid parameter value
- InvalidArgumentException: Invalid argument
- ServiceUnavailable: CloudWatch service issue
- LimitExceededFault: Too many requests or resources
- OperationAbortedException: Operation conflicts with other operation
- InvalidStateException: Resource not in correct state

---

## Route53 (DNS Service)

**Deletion Methods**:
- Hosted Zone → route53.delete_hosted_zone(Id=zone_id)
- Record Set → route53.change_resource_record_sets(HostedZoneId=zone_id, ChangeBatch={Changes: [{Action: DELETE, ResourceRecordSet: {...}}]})
- Health Check → route53.delete_health_check(HealthCheckId=id)
- Query Logging Config → route53.delete_query_logging_config(Id=config_id)

**Prerequisites**:
- Hosted zone must have all non-NS/SOA records deleted before deletion
- NS records pointing to zone must be updated at parent zone first
- Health checks can be deleted independently
- CloudWatch alarms on health checks must be deleted separately
- Route53 Resolver rules must be deleted separately
- Query logging config must be removed from zone first
- DNSSEC must be disabled before deletion
- VPC associations must be removed for private zones

**Non-deletable Resources**:
- NS records for zone root (must delete record set, not individual value)
- SOA record (automatic, managed by AWS)
- Zones in other accounts (delete via owner account)
- Health checks in use by records (can delete, but records will fail)

**Common Errors**:
- InvalidInput: Invalid hosted zone ID or parameter
- HostedZoneNotEmpty: Hosted zone has records (other than NS/SOA)
- NoSuchHostedZone: Hosted zone doesn't exist
- NoSuchHealthCheck: Health check doesn't exist
- ResourceInUse: Resource has dependencies
- InvalidChangeBatch: Invalid change request
- ConflictingTypes: Conflicting record types
- InvalidDomainName: Invalid domain name format
- PriorRequestNotComplete: Previous operation still in progress

---

## API Gateway (API Management)

**Deletion Methods**:
- REST API → apigateway.delete_rest_api(restApiId=api_id)
- HTTP API → apigatewayv2.delete_api(ApiId=api_id)
- WebSocket API → apigatewayv2.delete_api(ApiId=api_id)
- Stage → apigateway.delete_stage(restApiId=api_id, stageName=stage)
- Resource → apigateway.delete_resource(restApiId=api_id, resourceId=resource_id)
- Method → apigateway.delete_method(restApiId=api_id, resourceId=resource_id, httpMethod=method)

**Prerequisites**:
- All stages can be deleted independently
- Resources and methods are deleted with API
- VPC links must be removed from integration first (resource-level)
- Authorizers can be deleted independently
- Models can be deleted independently
- Request validators can be deleted independently
- Custom domain names must be updated to point to different API
- CloudFront distributions referencing API must be updated
- WAF ACL associations must be removed

**Non-deletable Resources**:
- APIs in use by CloudFront distributions
- Stages in use by custom domain names
- Default stages cannot be deleted (must delete API)
- Lambda functions invoked by API (persist after API deletion)

**Common Errors**:
- NotFoundException: API, stage, resource, or method doesn't exist
- BadRequestException: Invalid API ID or parameter
- ConflictException: Cannot delete resource (dependencies exist)
- TooManyRequestsException: Rate limit exceeded
- UnauthorizedOperationException: Insufficient permissions
- ServiceUnavailable: API Gateway service issue
- LimitExceeded: Too many resources
- InvalidIntegration: Integration configuration issue
- RequestIdAlreadyExists: Duplicate request ID

---

## KMS (Key Management Service)

**Deletion Methods**:
- Key (Schedule) → kms.schedule_key_deletion(KeyId=key_id, PendingWindowInDays=7)
- Key (Cancel Deletion) → kms.cancel_key_deletion(KeyId=key_id)
- Alias → kms.delete_alias(AliasName=alias)
- Grant → kms.retire_grant(GrantId=grant_id) or kms.revoke_grant(KeyId=key_id, GrantId=grant_id)

**Prerequisites**:
- Key deletion is scheduled (minimum 7 days, default 30 days)
- Key cannot be used during deletion schedule
- Aliases must be deleted before key deletion
- Grants must be retired or revoked before key deletion
- CloudWatch alarms on key metrics must be deleted separately
- Replicated keys must be scheduled for deletion in each region
- AWS-managed keys cannot be scheduled for deletion
- Resources encrypted with key must be migrated or re-encrypted first

**Non-deletable Resources**:
- AWS-managed keys (arn:aws:kms:region:account:key/*)
- Keys during deletion window
- Keys with key material not imported
- Keys in other accounts
- Keys with grants that must retire

**Common Errors**:
- NotFoundException: Key or alias doesn't exist
- InvalidKeyId: Invalid key ID format
- InvalidAliasNameException: Invalid alias name
- AlreadyExistsException: Alias already exists
- InvalidStateException: Key in wrong state (pending deletion, disabled)
- DependencyTimeoutException: Request timeout
- InternalException: KMS service error
- LimitExceededException: Too many aliases or key policies
- UnsupportedOperationException: Operation not supported (e.g., deleting AWS-managed key)

---

## Additional Services (Brief Reference)

### EventBridge (Event Routing)
- Rule → events.delete_rule(Name=rule_name)
- Target → events.remove_targets(Rule=rule_name, Ids=[ids])
- Event Bus → events.delete_event_bus(Name=bus_name)
- Prerequisite: Targets must be removed before rule deletion
- Error: ResourceNotFoundException if rule doesn't exist

### CodeBuild (Build Service)
- Project → codebuild.delete_project(name=project_name)
- Source credential → codebuild.invalidate_project_cache(projectName=project_name)
- Prerequisite: Project not in use by pipeline
- Error: ProjectNotFoundException if project doesn't exist

### CodePipeline (CI/CD Pipeline)
- Pipeline → codepipeline.delete_pipeline(name=pipeline_name)
- Prerequisite: Pipeline can be deleted regardless of state
- Error: PipelineNotFoundException if pipeline doesn't exist

### Step Functions (Workflow Orchestration)
- State Machine → stepfunctions.delete_state_machine(stateMachineArn=arn)
- Prerequisite: Executions must complete first (can delete machine with running executions)
- Error: InvalidArn if state machine ARN invalid

### Backup (Backup Service)
- Backup Plan → backup.delete_backup_plan(BackupPlanId=id)
- Backup Vault → backup.delete_backup_vault(BackupVaultName=name)
- Prerequisite: Backup vault must be empty (remove recovery points first)
- Error: ResourceNotFoundException if resource doesn't exist

### WAF (Web Application Firewall)
- Web ACL → wafv2.delete_web_acl(Name=name, Scope=scope, Id=id, LockToken=lock_token)
- IP Set → wafv2.delete_ip_set(Name=name, Scope=scope, Id=id, LockToken=lock_token)
- Rule Group → wafv2.delete_rule_group(Name=name, Scope=scope, Id=id, LockToken=lock_token)
- Prerequisite: Must obtain lock token before deletion (optimistic locking)
- Error: InvalidOperationException if WAF is in use

### EFS (Elastic File System)
- File System → efs.delete_file_system(FileSystemId=id)
- Mount Target → efs.delete_mount_target(MountTargetId=id)
- Access Point → efs.delete_access_point(AccessPointId=id)
- Prerequisite: All mount targets must be deleted before file system
- Error: FileSystemInUse if file system has mount targets

### ElastiCache (In-Memory Cache)
- Cluster → elasticache.delete_cache_cluster(CacheClusterId=id, SkipFinalSnapshot=False)
- Replication Group → elasticache.delete_replication_group(ReplicationGroupId=id, SkipFinalSnapshot=False)
- Parameter Group → elasticache.delete_cache_parameter_group(CacheParameterGroupName=name)
- Prerequisite: Final snapshot optional, parameter group must not be in use
- Error: InvalidCacheClusterStateFault if cluster in wrong state

### SSM (Systems Manager)
- Parameter → ssm.delete_parameter(Name=name)
- Document → ssm.delete_document(Name=name)
- Prerequisite: Parameters can be deleted independently, documents in use by automation cannot be deleted
- Error: ParameterNotFound if parameter doesn't exist

---

## Cross-Service Deletion Patterns

### Services with Deletion Queues/Recovery Windows:
- Secrets Manager: 7-30 day recovery window (default 30)
- KMS Keys: 7-30 day deletion schedule (default 30)
- S3 Buckets: Immediate deletion, no recovery

### Services with Protection/Termination Guards:
- RDS: Deletion protection flag (enable/disable)
- EC2 Instances: Termination protection (disable in attributes)
- CloudFormation: Stack deletion policy (attached to stack)

### Services with Cascading Dependencies:
- CloudFormation: Stacks delete resources (based on DeletionPolicy)
- ECS: Clusters require service deletion; services require task deletion
- EKS: Clusters require node group deletion; node groups delete nodes

### Services with Async Operations:
- EC2: Termination is asynchronous (instance stays around briefly)
- EBS: Volume deletion may take time if snapshots pending
- RDS: Deletion is synchronous but creates final snapshot asynchronously
- CloudFormation: Stack deletion is asynchronous

### Services with Global/Regional Considerations:
- S3: Global service (single bucket list, regional endpoints)
- IAM: Global service (not region-specific)
- CloudFront: Global service (requires OAI/distribution cleanup)
- Route53: Global service (zones not region-specific)

---

## Recommended Deletion Order

When deleting a complete environment:

1. **Stateful Data** (Highest Risk):
   - Backup any critical data
   - Create final snapshots of RDS instances
   - Export DynamoDB tables if needed
   - Download S3 bucket contents

2. **Compute Layer** (Mid-High Risk):
   - Delete EC2 instances (creates EBS volume snapshots)
   - Delete ECS/EKS resources
   - Delete Lambda functions and layers
   - Delete API Gateway endpoints

3. **Data Layer** (Mid Risk):
   - Delete RDS instances (creates final snapshot if requested)
   - Delete DynamoDB tables
   - Delete EFS file systems
   - Delete ElastiCache clusters

4. **Messaging/Streaming** (Mid Risk):
   - Delete SQS queues
   - Delete SNS topics
   - Delete Kinesis streams (if applicable)

5. **Network** (Mid-Low Risk):
   - Delete API Gateway APIs
   - Delete VPC endpoints
   - Delete Route53 records
   - Delete security groups
   - Delete subnets

6. **Storage** (Low Risk):
   - Delete S3 buckets (after all objects removed)
   - Delete EBS volumes (if not auto-deleted)
   - Delete snapshots if not needed

7. **Metadata/Config** (Lowest Risk):
   - Delete IAM roles/policies
   - Delete KMS keys (schedule deletion)
   - Delete CloudFormation stacks
   - Delete CloudWatch log groups

---

## Error Handling Strategy

Recommended approach for deletion:

```
1. Check resource dependencies first
2. Attempt deletion
3. If dependency error:
   a. Identify dependent resources
   b. Delete dependents first (recursively)
   c. Retry original deletion
4. If permission error:
   a. Check IAM policy
   b. Check resource policy
   c. Check service-linked role permissions
5. If state error:
   a. Wait for resource to reach stable state
   b. Disable protections if needed
   c. Retry deletion
```

---

## Testing Deletion Operations

Best practices:

- Always test in non-production environment first
- Create test resources with unique identifiers (e.g., test-delete-* prefix)
- Verify prerequisites manually before automation
- Log all deletion attempts for audit trail
- Use try-except blocks with specific exception handling
- Implement dry-run mode (list resources without deleting)
- Consider creating final snapshots/backups even if auto-created
- Track deletion progress and failed operations
- Implement rollback mechanism if needed
- Monitor for side effects in dependent services
