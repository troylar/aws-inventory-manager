"""Tests for DeletionRecord model.

Test coverage for individual deletion record entity with status-specific validation.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.models.deletion_record import DeletionRecord, DeletionStatus


class TestDeletionRecord:
    """Test suite for DeletionRecord model."""

    def test_create_succeeded_record(self) -> None:
        """Test creating successful deletion record."""
        record = DeletionRecord(
            record_id="rec_001",
            operation_id="op_123",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-001",
            resource_id="i-001",
            resource_type="aws:ec2:instance",
            region="us-east-1",
            timestamp=datetime(2025, 11, 11, 15, 31, 0),
            status=DeletionStatus.SUCCEEDED,
        )

        assert record.record_id == "rec_001"
        assert record.operation_id == "op_123"
        assert record.resource_arn == "arn:aws:ec2:us-east-1:123456789012:instance/i-001"
        assert record.resource_id == "i-001"
        assert record.resource_type == "aws:ec2:instance"
        assert record.region == "us-east-1"
        assert record.status == DeletionStatus.SUCCEEDED
        assert record.error_code is None
        assert record.error_message is None
        assert record.protection_reason is None

    def test_create_failed_record(self) -> None:
        """Test creating failed deletion record with error details."""
        record = DeletionRecord(
            record_id="rec_002",
            operation_id="op_123",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-002",
            resource_id="i-002",
            resource_type="aws:ec2:instance",
            region="us-east-1",
            timestamp=datetime(2025, 11, 11, 15, 31, 5),
            status=DeletionStatus.FAILED,
            error_code="UnauthorizedOperation",
            error_message="You are not authorized to perform this operation",
        )

        assert record.status == DeletionStatus.FAILED
        assert record.error_code == "UnauthorizedOperation"
        assert record.error_message == "You are not authorized to perform this operation"
        assert record.protection_reason is None

    def test_create_skipped_record(self) -> None:
        """Test creating skipped deletion record with protection reason."""
        record = DeletionRecord(
            record_id="rec_003",
            operation_id="op_123",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-003",
            resource_id="i-003",
            resource_type="aws:ec2:instance",
            region="us-east-1",
            timestamp=datetime(2025, 11, 11, 15, 31, 10),
            status=DeletionStatus.SKIPPED,
            protection_reason="Tag Protection=true",
        )

        assert record.status == DeletionStatus.SKIPPED
        assert record.protection_reason == "Tag Protection=true"
        assert record.error_code is None
        assert record.error_message is None

    def test_create_with_optional_fields(self) -> None:
        """Test creating record with all optional fields."""
        record = DeletionRecord(
            record_id="rec_004",
            operation_id="op_123",
            resource_arn="arn:aws:rds:us-west-2:123456789012:db:mydb",
            resource_id="mydb",
            resource_type="aws:rds:dbinstance",
            region="us-west-2",
            timestamp=datetime(2025, 11, 11, 15, 31, 15),
            status=DeletionStatus.SUCCEEDED,
            deletion_tier=3,
            tags={"Environment": "development", "Project": "test"},
            estimated_monthly_cost=150.50,
        )

        assert record.deletion_tier == 3
        assert record.tags == {"Environment": "development", "Project": "test"}
        assert record.estimated_monthly_cost == 150.50

    def test_validate_succeeded_record(self) -> None:
        """Test validation passes for succeeded record without errors."""
        record = DeletionRecord(
            record_id="rec_valid",
            operation_id="op_123",
            resource_arn="arn:aws:s3:::my-bucket",
            resource_id="my-bucket",
            resource_type="aws:s3:bucket",
            region="us-east-1",
            timestamp=datetime(2025, 11, 11),
            status=DeletionStatus.SUCCEEDED,
        )

        assert record.validate() is True

    def test_validate_failed_record_requires_error_code(self) -> None:
        """Test validation fails for failed record without error_code."""
        record = DeletionRecord(
            record_id="rec_invalid",
            operation_id="op_123",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-999",
            resource_id="i-999",
            resource_type="aws:ec2:instance",
            region="us-east-1",
            timestamp=datetime(2025, 11, 11),
            status=DeletionStatus.FAILED,
            # Missing error_code!
        )

        with pytest.raises(ValueError, match="Failed status requires error_code"):
            record.validate()

    def test_validate_skipped_record_requires_protection_reason(self) -> None:
        """Test validation fails for skipped record without protection_reason."""
        record = DeletionRecord(
            record_id="rec_invalid",
            operation_id="op_123",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-888",
            resource_id="i-888",
            resource_type="aws:ec2:instance",
            region="us-east-1",
            timestamp=datetime(2025, 11, 11),
            status=DeletionStatus.SKIPPED,
            # Missing protection_reason!
        )

        with pytest.raises(ValueError, match="Skipped status requires protection_reason"):
            record.validate()

    def test_validate_succeeded_cannot_have_error(self) -> None:
        """Test validation fails for succeeded record with error_code."""
        record = DeletionRecord(
            record_id="rec_conflict",
            operation_id="op_123",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-777",
            resource_id="i-777",
            resource_type="aws:ec2:instance",
            region="us-east-1",
            timestamp=datetime(2025, 11, 11),
            status=DeletionStatus.SUCCEEDED,
            error_code="SomeError",  # Conflicting!
        )

        with pytest.raises(ValueError, match="Succeeded status cannot have error or protection reason"):
            record.validate()

    def test_validate_succeeded_cannot_have_protection_reason(self) -> None:
        """Test validation fails for succeeded record with protection_reason."""
        record = DeletionRecord(
            record_id="rec_conflict2",
            operation_id="op_123",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-666",
            resource_id="i-666",
            resource_type="aws:ec2:instance",
            region="us-east-1",
            timestamp=datetime(2025, 11, 11),
            status=DeletionStatus.SUCCEEDED,
            protection_reason="Protected",  # Conflicting!
        )

        with pytest.raises(ValueError, match="Succeeded status cannot have error or protection reason"):
            record.validate()

    def test_validate_arn_format(self) -> None:
        """Test validation checks ARN format."""
        record = DeletionRecord(
            record_id="rec_arn",
            operation_id="op_123",
            resource_arn="invalid-arn-format",  # Invalid!
            resource_id="resource",
            resource_type="aws:service:type",
            region="us-east-1",
            timestamp=datetime(2025, 11, 11),
            status=DeletionStatus.SUCCEEDED,
        )

        with pytest.raises(ValueError, match="Invalid ARN format"):
            record.validate()

    def test_validate_negative_cost_raises_error(self) -> None:
        """Test validation fails for negative cost."""
        record = DeletionRecord(
            record_id="rec_cost",
            operation_id="op_123",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-555",
            resource_id="i-555",
            resource_type="aws:ec2:instance",
            region="us-east-1",
            timestamp=datetime(2025, 11, 11),
            status=DeletionStatus.SUCCEEDED,
            estimated_monthly_cost=-10.0,  # Invalid!
        )

        with pytest.raises(ValueError, match="Cost cannot be negative"):
            record.validate()

    def test_validate_zero_cost_allowed(self) -> None:
        """Test validation allows zero cost."""
        record = DeletionRecord(
            record_id="rec_free",
            operation_id="op_123",
            resource_arn="arn:aws:s3:::free-bucket",
            resource_id="free-bucket",
            resource_type="aws:s3:bucket",
            region="us-east-1",
            timestamp=datetime(2025, 11, 11),
            status=DeletionStatus.SUCCEEDED,
            estimated_monthly_cost=0.0,
        )

        assert record.validate() is True


class TestDeletionStatus:
    """Test DeletionStatus enum."""

    def test_status_values(self) -> None:
        """Test status enum values."""
        assert DeletionStatus.SUCCEEDED.value == "succeeded"
        assert DeletionStatus.FAILED.value == "failed"
        assert DeletionStatus.SKIPPED.value == "skipped"

    def test_status_from_string(self) -> None:
        """Test creating status from string value."""
        assert DeletionStatus("succeeded") == DeletionStatus.SUCCEEDED
        assert DeletionStatus("failed") == DeletionStatus.FAILED
        assert DeletionStatus("skipped") == DeletionStatus.SKIPPED
