"""Tests for ResourceDeleter class.

Test coverage for AWS resource deletion with boto3 integration.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError

from src.restore.deleter import ResourceDeleter


class TestResourceDeleter:
    """Test suite for ResourceDeleter class."""

    def test_init_creates_deleter_with_defaults(self) -> None:
        """Test initialization with default parameters."""
        deleter = ResourceDeleter()

        assert deleter.aws_profile is None
        assert deleter.max_retries == 3

    def test_init_with_custom_parameters(self) -> None:
        """Test initialization with custom parameters."""
        deleter = ResourceDeleter(aws_profile="prod", max_retries=5)

        assert deleter.aws_profile == "prod"
        assert deleter.max_retries == 5

    @patch("src.restore.deleter.create_boto_client")
    def test_delete_ec2_instance_success(self, mock_create_client: Mock) -> None:
        """Test successful EC2 instance deletion."""
        # Setup mock client
        mock_client = Mock()
        mock_client.terminate_instances.return_value = {}
        mock_create_client.return_value = mock_client

        deleter = ResourceDeleter()
        success, error = deleter.delete_resource(
            resource_type="AWS::EC2::Instance",
            resource_id="i-123456",
            region="us-east-1",
            arn="arn:aws:ec2:us-east-1:123456789012:instance/i-123456",
        )

        assert success is True
        assert error is None
        mock_create_client.assert_called_once_with(
            service_name="ec2",
            region_name="us-east-1",
            profile_name=None,
        )
        mock_client.terminate_instances.assert_called_once_with(InstanceIds=["i-123456"])

    @patch("src.restore.deleter.create_boto_client")
    def test_delete_lambda_function_success(self, mock_create_client: Mock) -> None:
        """Test successful Lambda function deletion."""
        mock_client = Mock()
        mock_client.delete_function.return_value = {}
        mock_create_client.return_value = mock_client

        deleter = ResourceDeleter()
        success, error = deleter.delete_resource(
            resource_type="AWS::Lambda::Function",
            resource_id="my-function",
            region="us-west-2",
            arn="arn:aws:lambda:us-west-2:123456789012:function:my-function",
        )

        assert success is True
        assert error is None
        mock_client.delete_function.assert_called_once_with(FunctionName="my-function")

    @patch("src.restore.deleter.create_boto_client")
    def test_delete_rds_instance_with_skip_snapshot(self, mock_create_client: Mock) -> None:
        """Test RDS instance deletion skips final snapshot."""
        mock_client = Mock()
        mock_client.delete_db_instance.return_value = {}
        mock_create_client.return_value = mock_client

        deleter = ResourceDeleter()
        success, error = deleter.delete_resource(
            resource_type="AWS::RDS::DBInstance",
            resource_id="my-database",
            region="us-east-1",
            arn="arn:aws:rds:us-east-1:123456789012:db:my-database",
        )

        assert success is True
        assert error is None
        mock_client.delete_db_instance.assert_called_once_with(
            DBInstanceIdentifier="my-database",
            SkipFinalSnapshot=True,
            DeleteAutomatedBackups=True,
        )

    @patch("src.restore.deleter.create_boto_client")
    def test_delete_handles_already_deleted_resource(self, mock_create_client: Mock) -> None:
        """Test deletion handles already-deleted resources gracefully."""
        mock_client = Mock()
        error_response = {
            "Error": {
                "Code": "InvalidInstanceID.NotFound",
                "Message": "The instance ID 'i-123456' does not exist",
            }
        }
        mock_client.terminate_instances.side_effect = ClientError(error_response, "TerminateInstances")
        mock_create_client.return_value = mock_client

        deleter = ResourceDeleter()
        success, error = deleter.delete_resource(
            resource_type="AWS::EC2::Instance",
            resource_id="i-123456",
            region="us-east-1",
            arn="arn:aws:ec2:us-east-1:123456789012:instance/i-123456",
        )

        # Should succeed because resource is already gone
        assert success is True
        assert error is None

    @patch("src.restore.deleter.create_boto_client")
    @patch("src.restore.deleter.time.sleep")
    def test_delete_retries_on_dependency_violation(self, mock_sleep: Mock, mock_create_client: Mock) -> None:
        """Test deletion retries on dependency violations."""
        mock_client = Mock()
        error_response = {
            "Error": {
                "Code": "DependencyViolation",
                "Message": "The resource has a dependent object",
            }
        }
        # Fail twice, succeed on third attempt
        mock_client.terminate_instances.side_effect = [
            ClientError(error_response, "TerminateInstances"),
            ClientError(error_response, "TerminateInstances"),
            {},  # Success
        ]
        mock_create_client.return_value = mock_client

        deleter = ResourceDeleter(max_retries=3)
        success, error = deleter.delete_resource(
            resource_type="AWS::EC2::Instance",
            resource_id="i-123456",
            region="us-east-1",
            arn="arn:aws:ec2:us-east-1:123456789012:instance/i-123456",
        )

        assert success is True
        assert error is None
        # Should have been called 3 times
        assert mock_client.terminate_instances.call_count == 3
        # Should have slept twice (exponential backoff: 1s, 2s)
        assert mock_sleep.call_count == 2

    @patch("src.restore.deleter.create_boto_client")
    @patch("src.restore.deleter.time.sleep")
    def test_delete_fails_after_max_retries(self, mock_sleep: Mock, mock_create_client: Mock) -> None:
        """Test deletion fails after exhausting retries."""
        mock_client = Mock()
        error_response = {
            "Error": {
                "Code": "DependencyViolation",
                "Message": "The resource has a dependent object",
            }
        }
        mock_client.terminate_instances.side_effect = ClientError(error_response, "TerminateInstances")
        mock_create_client.return_value = mock_client

        deleter = ResourceDeleter(max_retries=3)
        success, error = deleter.delete_resource(
            resource_type="AWS::EC2::Instance",
            resource_id="i-123456",
            region="us-east-1",
            arn="arn:aws:ec2:us-east-1:123456789012:instance/i-123456",
        )

        assert success is False
        assert "after 3 attempts" in error
        assert mock_client.terminate_instances.call_count == 3

    @patch("src.restore.deleter.create_boto_client")
    def test_delete_handles_client_error(self, mock_create_client: Mock) -> None:
        """Test deletion handles general client errors."""
        mock_client = Mock()
        error_response = {
            "Error": {
                "Code": "AccessDenied",
                "Message": "You are not authorized",
            }
        }
        mock_client.terminate_instances.side_effect = ClientError(error_response, "TerminateInstances")
        mock_create_client.return_value = mock_client

        deleter = ResourceDeleter()
        success, error = deleter.delete_resource(
            resource_type="AWS::EC2::Instance",
            resource_id="i-123456",
            region="us-east-1",
            arn="arn:aws:ec2:us-east-1:123456789012:instance/i-123456",
        )

        assert success is False
        assert "AccessDenied" in error
        assert "not authorized" in error

    def test_delete_unsupported_resource_type(self) -> None:
        """Test deletion of unsupported resource type."""
        deleter = ResourceDeleter()
        success, error = deleter.delete_resource(
            resource_type="AWS::UnsupportedService::Resource",
            resource_id="resource-123",
            region="us-east-1",
            arn="arn:aws:unsupported:us-east-1:123456789012:resource/resource-123",
        )

        assert success is False
        assert "Unsupported resource type" in error

    @patch("src.restore.deleter.create_boto_client")
    def test_delete_with_aws_profile(self, mock_create_client: Mock) -> None:
        """Test deletion uses specified AWS profile."""
        mock_client = Mock()
        mock_client.terminate_instances.return_value = {}
        mock_create_client.return_value = mock_client

        deleter = ResourceDeleter(aws_profile="production")
        success, error = deleter.delete_resource(
            resource_type="AWS::EC2::Instance",
            resource_id="i-123456",
            region="us-east-1",
            arn="arn:aws:ec2:us-east-1:123456789012:instance/i-123456",
        )

        assert success is True
        mock_create_client.assert_called_once_with(
            service_name="ec2",
            region_name="us-east-1",
            profile_name="production",
        )

    @patch("src.restore.deleter.create_boto_client")
    def test_delete_s3_bucket(self, mock_create_client: Mock) -> None:
        """Test S3 bucket deletion."""
        mock_client = Mock()
        mock_client.delete_bucket.return_value = {}
        mock_create_client.return_value = mock_client

        deleter = ResourceDeleter()
        success, error = deleter.delete_resource(
            resource_type="AWS::S3::Bucket",
            resource_id="my-bucket",
            region="us-east-1",
            arn="arn:aws:s3:::my-bucket",
        )

        assert success is True
        assert error is None
        mock_client.delete_bucket.assert_called_once_with(Bucket="my-bucket")

    @patch("src.restore.deleter.create_boto_client")
    def test_delete_dynamodb_table(self, mock_create_client: Mock) -> None:
        """Test DynamoDB table deletion."""
        mock_client = Mock()
        mock_client.delete_table.return_value = {}
        mock_create_client.return_value = mock_client

        deleter = ResourceDeleter()
        success, error = deleter.delete_resource(
            resource_type="AWS::DynamoDB::Table",
            resource_id="my-table",
            region="us-east-1",
            arn="arn:aws:dynamodb:us-east-1:123456789012:table/my-table",
        )

        assert success is True
        assert error is None
        mock_client.delete_table.assert_called_once_with(TableName="my-table")

    @patch("src.restore.deleter.create_boto_client")
    def test_delete_iam_role(self, mock_create_client: Mock) -> None:
        """Test IAM role deletion."""
        mock_client = Mock()
        mock_client.delete_role.return_value = {}
        mock_create_client.return_value = mock_client

        deleter = ResourceDeleter()
        success, error = deleter.delete_resource(
            resource_type="AWS::IAM::Role",
            resource_id="MyRole",
            region="us-east-1",
            arn="arn:aws:iam::123456789012:role/MyRole",
        )

        assert success is True
        assert error is None
        mock_client.delete_role.assert_called_once_with(RoleName="MyRole")

    @patch("src.restore.deleter.create_boto_client")
    def test_delete_kms_key_schedules_deletion(self, mock_create_client: Mock) -> None:
        """Test KMS key schedules deletion with minimum waiting period."""
        mock_client = Mock()
        mock_client.schedule_key_deletion.return_value = {}
        mock_create_client.return_value = mock_client

        deleter = ResourceDeleter()
        success, error = deleter.delete_resource(
            resource_type="AWS::KMS::Key",
            resource_id="key-123",
            region="us-east-1",
            arn="arn:aws:kms:us-east-1:123456789012:key/key-123",
        )

        assert success is True
        assert error is None
        mock_client.schedule_key_deletion.assert_called_once_with(
            KeyId="key-123",
            PendingWindowInDays=7,
        )

    @patch("src.restore.deleter.create_boto_client")
    def test_delete_secret_forces_deletion(self, mock_create_client: Mock) -> None:
        """Test Secrets Manager secret forces immediate deletion."""
        mock_client = Mock()
        mock_client.delete_secret.return_value = {}
        mock_create_client.return_value = mock_client

        deleter = ResourceDeleter()
        success, error = deleter.delete_resource(
            resource_type="AWS::SecretsManager::Secret",
            resource_id="my-secret",
            region="us-east-1",
            arn="arn:aws:secretsmanager:us-east-1:123456789012:secret:my-secret",
        )

        assert success is True
        assert error is None
        mock_client.delete_secret.assert_called_once_with(
            SecretId="my-secret",
            ForceDeleteWithoutRecovery=True,
        )

    @patch("src.restore.deleter.create_boto_client")
    def test_delete_handles_unexpected_exception_in_deletion_loop(self, mock_create_client: Mock) -> None:
        """Test deletion handles unexpected exception in main loop."""
        mock_client = Mock()
        # Raise unexpected exception (not ClientError)
        mock_client.terminate_instances.side_effect = RuntimeError("Unexpected boto3 error")
        mock_create_client.return_value = mock_client

        deleter = ResourceDeleter(max_retries=2)
        success, error = deleter.delete_resource(
            resource_type="AWS::EC2::Instance",
            resource_id="i-exception",
            region="us-east-1",
            arn="arn:aws:ec2:us-east-1:123456789012:instance/i-exception",
        )

        assert success is False
        assert "Unexpected error" in error
        assert "Unexpected boto3 error" in error
        # Exception in _attempt_deletion gets caught and returned, no retry
        assert mock_client.terminate_instances.call_count == 1

    @patch("src.restore.deleter.create_boto_client")
    def test_delete_handles_unexpected_exception_in_attempt(self, mock_create_client: Mock) -> None:
        """Test _attempt_deletion handles unexpected non-ClientError exception."""
        mock_client = Mock()
        # Raise unexpected exception during deletion attempt
        mock_client.delete_function.side_effect = ValueError("Unexpected internal error")
        mock_create_client.return_value = mock_client

        deleter = ResourceDeleter()
        success, error = deleter.delete_resource(
            resource_type="AWS::Lambda::Function",
            resource_id="my-function",
            region="us-west-2",
            arn="arn:aws:lambda:us-west-2:123456789012:function:my-function",
        )

        assert success is False
        assert "Unexpected error" in error
        assert "ValueError" in error or "Unexpected internal error" in error

    @patch("src.restore.deleter.create_boto_client")
    def test_delete_iam_policy_uses_arn_parameter(self, mock_create_client: Mock) -> None:
        """Test IAM policy deletion uses ARN in parameter."""
        mock_client = Mock()
        mock_client.delete_policy.return_value = {}
        mock_create_client.return_value = mock_client

        deleter = ResourceDeleter()
        policy_arn = "arn:aws:iam::123456789012:policy/MyCustomPolicy"
        success, error = deleter.delete_resource(
            resource_type="AWS::IAM::Policy",
            resource_id="MyCustomPolicy",
            region="us-east-1",
            arn=policy_arn,
        )

        assert success is True
        # Should use ARN parameter (PolicyArn contains "Arn")
        mock_client.delete_policy.assert_called_once_with(PolicyArn=policy_arn)

    def test_delete_handles_exception_from_attempt_deletion_with_retry(self) -> None:
        """Test deletion retries when _attempt_deletion itself raises an exception."""
        deleter = ResourceDeleter(max_retries=3)

        # Mock _attempt_deletion to raise exception twice, then succeed
        with patch.object(
            deleter,
            "_attempt_deletion",
            side_effect=[
                RuntimeError("Attempt failed"),
                RuntimeError("Attempt failed again"),
                (True, None),  # Success on third attempt
            ],
        ):
            success, error = deleter.delete_resource(
                resource_type="AWS::EC2::Instance",
                resource_id="i-retry",
                region="us-east-1",
                arn="arn:aws:ec2:us-east-1:123456789012:instance/i-retry",
            )

        # Should eventually succeed after retries
        assert success is True
        assert error is None

    def test_delete_handles_exception_from_attempt_deletion_exhausts_retries(self) -> None:
        """Test deletion fails after exhausting retries when _attempt_deletion raises exceptions."""
        deleter = ResourceDeleter(max_retries=2)

        # Mock _attempt_deletion to always raise exception
        with patch.object(deleter, "_attempt_deletion", side_effect=RuntimeError("Always fails")):
            success, error = deleter.delete_resource(
                resource_type="AWS::EC2::Instance",
                resource_id="i-always-fail",
                region="us-east-1",
                arn="arn:aws:ec2:us-east-1:123456789012:instance/i-always-fail",
            )

        # Should fail after exhausting retries
        assert success is False
        assert "Unexpected error deleting" in error
        assert "AWS::EC2::Instance" in error
        assert "i-always-fail" in error
        assert "Always fails" in error
