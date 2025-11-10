"""Test fixtures for creating mock snapshots and resources."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.models.resource import Resource
from src.models.snapshot import Snapshot


def create_s3_bucket(
    bucket_name: str = "test-bucket",
    region: str = "us-east-1",
    public: bool = False,
    encrypted: bool = True,
    tags: Optional[Dict[str, str]] = None,
) -> Resource:
    """Create a mock S3 bucket resource for testing.

    Args:
        bucket_name: Name of the bucket
        region: AWS region
        public: Whether bucket is publicly accessible
        encrypted: Whether bucket encryption is enabled
        tags: Resource tags

    Returns:
        Resource representing an S3 bucket
    """
    raw_config: Dict[str, Any] = {
        "Name": bucket_name,
        "CreationDate": "2025-01-01T00:00:00Z",
    }

    if public:
        raw_config["PublicAccessBlockConfiguration"] = {
            "BlockPublicAcls": False,
            "IgnorePublicAcls": False,
            "BlockPublicPolicy": False,
            "RestrictPublicBuckets": False,
        }
    else:
        raw_config["PublicAccessBlockConfiguration"] = {
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        }

    if encrypted:
        raw_config["ServerSideEncryptionConfiguration"] = {
            "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
        }

    return Resource(
        arn=f"arn:aws:s3:::{bucket_name}",
        resource_type="s3:bucket",
        name=bucket_name,
        region=region,
        config_hash="a" * 64,
        raw_config=raw_config,
        tags=tags or {},
    )


def create_security_group(
    group_id: str = "sg-12345",
    region: str = "us-east-1",
    open_ports: Optional[List[int]] = None,
    tags: Optional[Dict[str, str]] = None,
) -> Resource:
    """Create a mock security group resource for testing.

    Args:
        group_id: Security group ID
        region: AWS region
        open_ports: List of ports open to 0.0.0.0/0 (if any)
        tags: Resource tags

    Returns:
        Resource representing a security group
    """
    ip_permissions: List[Dict[str, Any]] = []

    if open_ports:
        for port in open_ports:
            ip_permissions.append(
                {
                    "IpProtocol": "tcp",
                    "FromPort": port,
                    "ToPort": port,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                    "Ipv6Ranges": [],
                    "PrefixListIds": [],
                    "UserIdGroupPairs": [],
                }
            )

    raw_config = {
        "GroupId": group_id,
        "GroupName": f"test-sg-{group_id}",
        "Description": "Test security group",
        "IpPermissions": ip_permissions,
        "IpPermissionsEgress": [],
        "VpcId": "vpc-12345",
    }

    return Resource(
        arn=f"arn:aws:ec2:{region}:123456789012:security-group/{group_id}",
        resource_type="ec2:security-group",
        name=f"test-sg-{group_id}",
        region=region,
        config_hash="b" * 64,
        raw_config=raw_config,
        tags=tags or {},
    )


def create_ec2_instance(
    instance_id: str = "i-12345",
    region: str = "us-east-1",
    instance_type: str = "t2.micro",
    imdsv2_required: bool = True,
    tags: Optional[Dict[str, str]] = None,
) -> Resource:
    """Create a mock EC2 instance resource for testing.

    Args:
        instance_id: Instance ID
        region: AWS region
        instance_type: Instance type (e.g., t2.micro)
        imdsv2_required: Whether IMDSv2 is required
        tags: Resource tags

    Returns:
        Resource representing an EC2 instance
    """
    raw_config = {
        "InstanceId": instance_id,
        "InstanceType": instance_type,
        "State": {"Name": "running"},
        "MetadataOptions": {
            "HttpTokens": "required" if imdsv2_required else "optional",
            "HttpPutResponseHopLimit": 1,
        },
        "SecurityGroups": [{"GroupId": "sg-default", "GroupName": "default"}],
    }

    return Resource(
        arn=f"arn:aws:ec2:{region}:123456789012:instance/{instance_id}",
        resource_type="ec2:instance",
        name=f"test-instance-{instance_id}",
        region=region,
        config_hash="c" * 64,
        raw_config=raw_config,
        tags=tags or {},
    )


def create_rds_instance(
    db_instance_id: str = "test-db",
    region: str = "us-east-1",
    publicly_accessible: bool = False,
    encrypted: bool = True,
    tags: Optional[Dict[str, str]] = None,
) -> Resource:
    """Create a mock RDS instance resource for testing.

    Args:
        db_instance_id: Database instance identifier
        region: AWS region
        publicly_accessible: Whether database is publicly accessible
        encrypted: Whether storage is encrypted
        tags: Resource tags

    Returns:
        Resource representing an RDS instance
    """
    raw_config = {
        "DBInstanceIdentifier": db_instance_id,
        "DBInstanceClass": "db.t3.micro",
        "Engine": "postgres",
        "EngineVersion": "13.7",
        "PubliclyAccessible": publicly_accessible,
        "StorageEncrypted": encrypted,
        "DBInstanceStatus": "available",
    }

    return Resource(
        arn=f"arn:aws:rds:{region}:123456789012:db:{db_instance_id}",
        resource_type="rds:db-instance",
        name=db_instance_id,
        region=region,
        config_hash="d" * 64,
        raw_config=raw_config,
        tags=tags or {},
    )


def create_iam_user(
    user_name: str = "test-user",
    access_key_age_days: int = 30,
    tags: Optional[Dict[str, str]] = None,
) -> Resource:
    """Create a mock IAM user resource for testing.

    Args:
        user_name: IAM user name
        access_key_age_days: Age of access key in days
        tags: Resource tags

    Returns:
        Resource representing an IAM user
    """
    from datetime import timedelta

    key_created = datetime.now(timezone.utc) - timedelta(days=access_key_age_days)

    raw_config = {
        "UserName": user_name,
        "UserId": "AIDAI" + "X" * 16,
        "Arn": f"arn:aws:iam::123456789012:user/{user_name}",
        "CreateDate": "2024-01-01T00:00:00Z",
        "AccessKeys": [{"AccessKeyId": "AKIAI" + "X" * 16, "CreateDate": key_created.isoformat(), "Status": "Active"}],
    }

    return Resource(
        arn=f"arn:aws:iam::123456789012:user/{user_name}",
        resource_type="iam:user",
        name=user_name,
        region="global",
        config_hash="e" * 64,
        raw_config=raw_config,
        tags=tags or {},
    )


def create_secrets_manager_secret(
    secret_name: str = "test-secret",
    region: str = "us-east-1",
    last_rotated_days_ago: int = 30,
    tags: Optional[Dict[str, str]] = None,
) -> Resource:
    """Create a mock Secrets Manager secret resource for testing.

    Args:
        secret_name: Secret name
        region: AWS region
        last_rotated_days_ago: Days since last rotation
        tags: Resource tags

    Returns:
        Resource representing a Secrets Manager secret
    """
    from datetime import timedelta

    last_rotated = datetime.now(timezone.utc) - timedelta(days=last_rotated_days_ago)

    raw_config = {
        "Name": secret_name,
        "ARN": f"arn:aws:secretsmanager:{region}:123456789012:secret:{secret_name}",
        "LastRotatedDate": last_rotated.isoformat(),
        "LastChangedDate": last_rotated.isoformat(),
        "RotationEnabled": True,
    }

    return Resource(
        arn=f"arn:aws:secretsmanager:{region}:123456789012:secret:{secret_name}",
        resource_type="secretsmanager:secret",
        name=secret_name,
        region=region,
        config_hash="f" * 64,
        raw_config=raw_config,
        tags=tags or {},
    )


def create_mock_snapshot(
    name: str = "test-snapshot",
    resources: Optional[List[Resource]] = None,
    regions: Optional[List[str]] = None,
    account_id: str = "123456789012",
    created_at: Optional[datetime] = None,
) -> Snapshot:
    """Create a mock snapshot for testing.

    Args:
        name: Snapshot name
        resources: List of resources (if None, creates a default set)
        regions: List of regions (default: ["us-east-1"])
        account_id: AWS account ID
        created_at: Creation timestamp (default: now)

    Returns:
        Snapshot with mock resources
    """
    if resources is None:
        # Create a default set of resources for testing
        resources = [
            create_s3_bucket("default-bucket"),
            create_security_group("sg-default"),
            create_ec2_instance("i-default"),
            create_rds_instance("default-db"),
        ]

    if regions is None:
        regions = ["us-east-1"]

    if created_at is None:
        created_at = datetime.now(timezone.utc)

    return Snapshot(
        name=name,
        created_at=created_at,
        account_id=account_id,
        regions=regions,
        resources=resources,
        schema_version="1.1",
    )
