"""AWS resource deletion strategies.

Maps AWS resource types to their deletion methods with proper error handling
and retry logic.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from botocore.exceptions import ClientError

from src.aws.client import create_boto_client

logger = logging.getLogger(__name__)


class ResourceDeleter:
    """AWS resource deletion orchestrator.

    Handles deletion of various AWS resource types using appropriate boto3 API calls.
    Implements retry logic and error handling for safe resource cleanup.
    """

    # Deletion method mapping: resource_type -> (service, method, id_field)
    DELETION_METHODS = {
        # EC2 Resources
        "AWS::EC2::Instance": ("ec2", "terminate_instances", "InstanceIds"),
        "AWS::EC2::SecurityGroup": ("ec2", "delete_security_group", "GroupId"),
        "AWS::EC2::Volume": ("ec2", "delete_volume", "VolumeId"),
        "AWS::EC2::VPC": ("ec2", "delete_vpc", "VpcId"),
        "AWS::EC2::Subnet": ("ec2", "delete_subnet", "SubnetId"),
        "AWS::EC2::InternetGateway": ("ec2", "delete_internet_gateway", "InternetGatewayId"),
        "AWS::EC2::RouteTable": ("ec2", "delete_route_table", "RouteTableId"),
        "AWS::EC2::NetworkInterface": ("ec2", "delete_network_interface", "NetworkInterfaceId"),
        "AWS::EC2::KeyPair": ("ec2", "delete_key_pair", "KeyName"),

        # S3
        "AWS::S3::Bucket": ("s3", "delete_bucket", "Bucket"),

        # Lambda
        "AWS::Lambda::Function": ("lambda", "delete_function", "FunctionName"),

        # DynamoDB
        "AWS::DynamoDB::Table": ("dynamodb", "delete_table", "TableName"),

        # RDS
        "AWS::RDS::DBInstance": ("rds", "delete_db_instance", "DBInstanceIdentifier"),
        "AWS::RDS::DBCluster": ("rds", "delete_db_cluster", "DBClusterIdentifier"),

        # IAM
        "AWS::IAM::Role": ("iam", "delete_role", "RoleName"),
        "AWS::IAM::User": ("iam", "delete_user", "UserName"),
        "AWS::IAM::Policy": ("iam", "delete_policy", "PolicyArn"),

        # ECS
        "AWS::ECS::Service": ("ecs", "delete_service", "service"),
        "AWS::ECS::Cluster": ("ecs", "delete_cluster", "cluster"),
        "AWS::ECS::TaskDefinition": ("ecs", "deregister_task_definition", "taskDefinition"),

        # EKS
        "AWS::EKS::Cluster": ("eks", "delete_cluster", "name"),

        # SNS
        "AWS::SNS::Topic": ("sns", "delete_topic", "TopicArn"),

        # SQS
        "AWS::SQS::Queue": ("sqs", "delete_queue", "QueueUrl"),

        # CloudWatch
        "AWS::CloudWatch::Alarm": ("cloudwatch", "delete_alarms", "AlarmNames"),

        # API Gateway
        "AWS::ApiGateway::RestApi": ("apigateway", "delete_rest_api", "restApiId"),

        # KMS
        "AWS::KMS::Key": ("kms", "schedule_key_deletion", "KeyId"),

        # Secrets Manager
        "AWS::SecretsManager::Secret": ("secretsmanager", "delete_secret", "SecretId"),

        # ELB
        "AWS::ElasticLoadBalancing::LoadBalancer": ("elb", "delete_load_balancer", "LoadBalancerName"),
        "AWS::ElasticLoadBalancingV2::LoadBalancer": ("elbv2", "delete_load_balancer", "LoadBalancerArn"),

        # EFS
        "AWS::EFS::FileSystem": ("efs", "delete_file_system", "FileSystemId"),

        # ElastiCache
        "AWS::ElastiCache::CacheCluster": ("elasticache", "delete_cache_cluster", "CacheClusterId"),
    }

    def __init__(self, aws_profile: Optional[str] = None, max_retries: int = 3):
        """Initialize resource deleter.

        Args:
            aws_profile: AWS profile name (optional)
            max_retries: Maximum number of retry attempts (default: 3)
        """
        self.aws_profile = aws_profile
        self.max_retries = max_retries

    def delete_resource(
        self,
        resource_type: str,
        resource_id: str,
        region: str,
        arn: str,
    ) -> tuple[bool, Optional[str]]:
        """Delete an AWS resource.

        Args:
            resource_type: AWS resource type (e.g., "AWS::EC2::Instance")
            resource_id: Resource identifier
            region: AWS region
            arn: Resource ARN

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        # Check if we support this resource type
        if resource_type not in self.DELETION_METHODS:
            error_msg = f"Unsupported resource type: {resource_type}"
            logger.warning(error_msg)
            return (False, error_msg)

        service, method, id_field = self.DELETION_METHODS[resource_type]

        # Try deletion with retries
        for attempt in range(self.max_retries):
            try:
                success, error = self._attempt_deletion(
                    service=service,
                    method=method,
                    id_field=id_field,
                    resource_id=resource_id,
                    resource_type=resource_type,
                    region=region,
                    arn=arn,
                )

                if success:
                    logger.info(f"Successfully deleted {resource_type}: {resource_id}")
                    return (True, None)
                elif "DependencyViolation" in (error or ""):
                    # Dependency violations should be retried
                    if attempt < self.max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff
                        logger.debug(
                            f"Dependency violation for {resource_id}, "
                            f"retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        time.sleep(wait_time)
                        continue
                else:
                    # Non-retryable error
                    return (False, error)

            except Exception as e:
                error_msg = f"Unexpected error deleting {resource_type} {resource_id}: {str(e)}"
                logger.error(error_msg)
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return (False, error_msg)

        # All retries exhausted
        error_msg = f"Failed to delete {resource_type} {resource_id} after {self.max_retries} attempts"
        logger.error(error_msg)
        return (False, error_msg)

    def _attempt_deletion(
        self,
        service: str,
        method: str,
        id_field: str,
        resource_id: str,
        resource_type: str,
        region: str,
        arn: str,
    ) -> tuple[bool, Optional[str]]:
        """Attempt a single deletion operation.

        Args:
            service: AWS service name
            method: Boto3 method name
            id_field: Parameter name for resource ID
            resource_id: Resource identifier
            resource_type: AWS resource type
            region: AWS region
            arn: Resource ARN

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            # Create boto3 client for the service
            client = create_boto_client(
                service_name=service,
                region_name=region,
                profile_name=self.aws_profile,
            )

            # Build parameters based on resource type
            params = self._build_deletion_params(
                resource_type=resource_type,
                id_field=id_field,
                resource_id=resource_id,
                arn=arn,
            )

            # Call the deletion method
            deletion_method = getattr(client, method)
            deletion_method(**params)

            return (True, None)

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            # Handle specific error cases
            if error_code in ["InvalidInstanceID.NotFound", "NoSuchEntity", "ResourceNotFoundException"]:
                # Resource already deleted
                logger.info(f"Resource {resource_id} already deleted")
                return (True, None)
            elif error_code == "DependencyViolation":
                # Dependencies still exist
                logger.debug(f"Dependency violation for {resource_id}: {error_message}")
                return (False, f"DependencyViolation: {error_message}")
            else:
                # Other client errors
                logger.error(f"Failed to delete {resource_id}: {error_code} - {error_message}")
                return (False, f"{error_code}: {error_message}")

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Failed to delete {resource_id}: {error_msg}")
            return (False, error_msg)

    def _build_deletion_params(
        self,
        resource_type: str,
        id_field: str,
        resource_id: str,
        arn: str,
    ) -> dict[str, Any]:
        """Build deletion parameters for boto3 call.

        Args:
            resource_type: AWS resource type
            id_field: Parameter name for resource ID
            resource_id: Resource identifier
            arn: Resource ARN

        Returns:
            Dictionary of parameters for boto3 method call
        """
        # Handle list parameters (e.g., InstanceIds, AlarmNames)
        if id_field.endswith("s"):  # Plural form indicates list
            return {id_field: [resource_id]}

        # Handle ARN-based parameters
        if "Arn" in id_field:
            return {id_field: arn}

        # Handle special cases
        if resource_type == "AWS::RDS::DBInstance":
            # Skip final snapshot for faster deletion
            return {
                id_field: resource_id,
                "SkipFinalSnapshot": True,
                "DeleteAutomatedBackups": True,
            }
        elif resource_type == "AWS::KMS::Key":
            # Schedule deletion with minimum waiting period
            return {
                id_field: resource_id,
                "PendingWindowInDays": 7,
            }
        elif resource_type == "AWS::SecretsManager::Secret":
            # Immediate deletion (no recovery window)
            return {
                id_field: resource_id,
                "ForceDeleteWithoutRecovery": True,
            }

        # Standard parameter
        return {id_field: resource_id}
