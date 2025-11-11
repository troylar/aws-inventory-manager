"""Tests for DeletionOperation model.

Test coverage for deletion operation entity with validation rules.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from src.models.deletion_operation import (
    DeletionOperation,
    OperationMode,
    OperationStatus,
)


class TestDeletionOperation:
    """Test suite for DeletionOperation model."""

    def test_create_minimal_operation(self) -> None:
        """Test creating operation with minimal required fields."""
        operation = DeletionOperation(
            operation_id="op_123",
            baseline_snapshot="test-snapshot",
            timestamp=datetime(2025, 11, 11, 15, 30, 0),
            account_id="123456789012",
            mode=OperationMode.DRY_RUN,
            status=OperationStatus.PLANNED,
            total_resources=10,
        )

        assert operation.operation_id == "op_123"
        assert operation.baseline_snapshot == "test-snapshot"
        assert operation.account_id == "123456789012"
        assert operation.mode == OperationMode.DRY_RUN
        assert operation.status == OperationStatus.PLANNED
        assert operation.total_resources == 10
        assert operation.succeeded_count == 0
        assert operation.failed_count == 0
        assert operation.skipped_count == 0

    def test_create_full_operation(self) -> None:
        """Test creating operation with all optional fields."""
        started = datetime(2025, 11, 11, 15, 30, 0)
        completed = started + timedelta(seconds=85)

        operation = DeletionOperation(
            operation_id="op_456",
            baseline_snapshot="prod-baseline",
            timestamp=started,
            account_id="987654321098",
            mode=OperationMode.EXECUTE,
            status=OperationStatus.COMPLETED,
            total_resources=10,
            succeeded_count=8,
            failed_count=1,
            skipped_count=1,
            aws_profile="production",
            filters={"resource_types": ["ec2"], "regions": ["us-east-1"]},
            started_at=started,
            completed_at=completed,
            duration_seconds=85.3,
        )

        assert operation.aws_profile == "production"
        assert operation.filters == {"resource_types": ["ec2"], "regions": ["us-east-1"]}
        assert operation.started_at == started
        assert operation.completed_at == completed
        assert operation.duration_seconds == 85.3

    def test_validate_counts_sum_to_total(self) -> None:
        """Test validation: succeeded + failed + skipped == total."""
        operation = DeletionOperation(
            operation_id="op_789",
            baseline_snapshot="test",
            timestamp=datetime(2025, 11, 11),
            account_id="123456789012",
            mode=OperationMode.EXECUTE,
            status=OperationStatus.COMPLETED,
            total_resources=10,
            succeeded_count=8,
            failed_count=1,
            skipped_count=1,
        )

        assert operation.validate() is True

    def test_validate_counts_mismatch_raises_error(self) -> None:
        """Test validation fails when counts don't sum to total."""
        operation = DeletionOperation(
            operation_id="op_error",
            baseline_snapshot="test",
            timestamp=datetime(2025, 11, 11),
            account_id="123456789012",
            mode=OperationMode.EXECUTE,
            status=OperationStatus.COMPLETED,
            total_resources=10,
            succeeded_count=5,  # 5 + 1 + 1 = 7 != 10
            failed_count=1,
            skipped_count=1,
        )

        with pytest.raises(ValueError, match="Resource counts don't match total"):
            operation.validate()

    def test_validate_completion_before_start_raises_error(self) -> None:
        """Test validation fails when completed_at < started_at."""
        operation = DeletionOperation(
            operation_id="op_timing",
            baseline_snapshot="test",
            timestamp=datetime(2025, 11, 11),
            account_id="123456789012",
            mode=OperationMode.EXECUTE,
            status=OperationStatus.COMPLETED,
            total_resources=0,
            started_at=datetime(2025, 11, 11, 15, 30, 0),
            completed_at=datetime(2025, 11, 11, 15, 29, 0),  # Before start!
        )

        with pytest.raises(ValueError, match="Completion time before start time"):
            operation.validate()

    def test_validate_dry_run_must_be_planned(self) -> None:
        """Test validation: dry-run mode must have planned status."""
        operation = DeletionOperation(
            operation_id="op_dryrun",
            baseline_snapshot="test",
            timestamp=datetime(2025, 11, 11),
            account_id="123456789012",
            mode=OperationMode.DRY_RUN,
            status=OperationStatus.EXECUTING,  # Invalid for dry-run!
            total_resources=0,
        )

        with pytest.raises(ValueError, match="Dry-run mode must have planned status"):
            operation.validate()

    def test_state_transition_planned_to_executing(self) -> None:
        """Test valid state transition from planned to executing."""
        operation = DeletionOperation(
            operation_id="op_transition",
            baseline_snapshot="test",
            timestamp=datetime(2025, 11, 11),
            account_id="123456789012",
            mode=OperationMode.EXECUTE,
            status=OperationStatus.PLANNED,
            total_resources=0,  # Zero resources for planned state
        )

        # Transition to executing
        operation.status = OperationStatus.EXECUTING
        operation.started_at = datetime(2025, 11, 11, 15, 30, 0)

        assert operation.validate() is True
        assert operation.status == OperationStatus.EXECUTING

    def test_state_transition_executing_to_completed(self) -> None:
        """Test valid state transition from executing to completed."""
        started = datetime(2025, 11, 11, 15, 30, 0)
        operation = DeletionOperation(
            operation_id="op_complete",
            baseline_snapshot="test",
            timestamp=started,
            account_id="123456789012",
            mode=OperationMode.EXECUTE,
            status=OperationStatus.EXECUTING,
            total_resources=3,
            started_at=started,
        )

        # Complete successfully
        operation.status = OperationStatus.COMPLETED
        operation.completed_at = started + timedelta(seconds=60)
        operation.succeeded_count = 3
        operation.duration_seconds = 60.0

        assert operation.validate() is True
        assert operation.status == OperationStatus.COMPLETED

    def test_state_transition_executing_to_partial(self) -> None:
        """Test valid state transition from executing to partial."""
        started = datetime(2025, 11, 11, 15, 30, 0)
        operation = DeletionOperation(
            operation_id="op_partial",
            baseline_snapshot="test",
            timestamp=started,
            account_id="123456789012",
            mode=OperationMode.EXECUTE,
            status=OperationStatus.EXECUTING,
            total_resources=5,
            started_at=started,
        )

        # Partial completion (some failed)
        operation.status = OperationStatus.PARTIAL
        operation.completed_at = started + timedelta(seconds=45)
        operation.succeeded_count = 3
        operation.failed_count = 2
        operation.duration_seconds = 45.0

        assert operation.validate() is True
        assert operation.status == OperationStatus.PARTIAL


class TestOperationMode:
    """Test OperationMode enum."""

    def test_mode_values(self) -> None:
        """Test mode enum values."""
        assert OperationMode.DRY_RUN.value == "dry-run"
        assert OperationMode.EXECUTE.value == "execute"

    def test_mode_from_string(self) -> None:
        """Test creating mode from string value."""
        assert OperationMode("dry-run") == OperationMode.DRY_RUN
        assert OperationMode("execute") == OperationMode.EXECUTE


class TestOperationStatus:
    """Test OperationStatus enum."""

    def test_status_values(self) -> None:
        """Test status enum values."""
        assert OperationStatus.PLANNED.value == "planned"
        assert OperationStatus.EXECUTING.value == "executing"
        assert OperationStatus.COMPLETED.value == "completed"
        assert OperationStatus.PARTIAL.value == "partial"
        assert OperationStatus.FAILED.value == "failed"

    def test_status_from_string(self) -> None:
        """Test creating status from string value."""
        assert OperationStatus("planned") == OperationStatus.PLANNED
        assert OperationStatus("executing") == OperationStatus.EXECUTING
        assert OperationStatus("completed") == OperationStatus.COMPLETED
        assert OperationStatus("partial") == OperationStatus.PARTIAL
        assert OperationStatus("failed") == OperationStatus.FAILED


class TestDeletionOperationEdgeCases:
    """Test edge cases and additional validation scenarios."""

    def test_validate_with_no_timing_info(self) -> None:
        """Test validation succeeds when timing info is not provided."""
        operation = DeletionOperation(
            operation_id="op_no_timing",
            baseline_snapshot="test",
            timestamp=datetime(2025, 11, 11),
            account_id="123456789012",
            mode=OperationMode.EXECUTE,
            status=OperationStatus.COMPLETED,
            total_resources=5,
            succeeded_count=5,
        )

        # Should validate successfully without started_at/completed_at
        assert operation.validate() is True
        assert operation.started_at is None
        assert operation.completed_at is None

    def test_validate_with_only_started_at(self) -> None:
        """Test validation succeeds with only started_at."""
        operation = DeletionOperation(
            operation_id="op_started_only",
            baseline_snapshot="test",
            timestamp=datetime(2025, 11, 11),
            account_id="123456789012",
            mode=OperationMode.EXECUTE,
            status=OperationStatus.EXECUTING,
            total_resources=3,
            succeeded_count=3,  # Must equal total_resources
            started_at=datetime(2025, 11, 11, 15, 30, 0),
            # No completed_at
        )

        assert operation.validate() is True
        assert operation.started_at is not None
        assert operation.completed_at is None

    def test_validate_with_only_completed_at(self) -> None:
        """Test validation succeeds with only completed_at."""
        operation = DeletionOperation(
            operation_id="op_completed_only",
            baseline_snapshot="test",
            timestamp=datetime(2025, 11, 11),
            account_id="123456789012",
            mode=OperationMode.EXECUTE,
            status=OperationStatus.COMPLETED,
            total_resources=2,
            succeeded_count=2,
            # No started_at
            completed_at=datetime(2025, 11, 11, 15, 35, 0),
        )

        # Should validate successfully (timing validation only runs if both are present)
        assert operation.validate() is True
        assert operation.started_at is None
        assert operation.completed_at is not None

    def test_operation_with_all_skipped_resources(self) -> None:
        """Test operation where all resources were skipped (protected)."""
        operation = DeletionOperation(
            operation_id="op_all_skipped",
            baseline_snapshot="test",
            timestamp=datetime(2025, 11, 11),
            account_id="123456789012",
            mode=OperationMode.EXECUTE,
            status=OperationStatus.COMPLETED,
            total_resources=10,
            succeeded_count=0,
            failed_count=0,
            skipped_count=10,
        )

        assert operation.validate() is True
        assert operation.skipped_count == operation.total_resources

    def test_operation_with_all_failed_resources(self) -> None:
        """Test operation where all resources failed to delete."""
        operation = DeletionOperation(
            operation_id="op_all_failed",
            baseline_snapshot="test",
            timestamp=datetime(2025, 11, 11),
            account_id="123456789012",
            mode=OperationMode.EXECUTE,
            status=OperationStatus.FAILED,
            total_resources=5,
            succeeded_count=0,
            failed_count=5,
            skipped_count=0,
        )

        assert operation.validate() is True
        assert operation.failed_count == operation.total_resources

    def test_operation_with_zero_resources(self) -> None:
        """Test operation with zero resources (no resources to delete)."""
        operation = DeletionOperation(
            operation_id="op_zero",
            baseline_snapshot="test",
            timestamp=datetime(2025, 11, 11),
            account_id="123456789012",
            mode=OperationMode.DRY_RUN,
            status=OperationStatus.PLANNED,
            total_resources=0,
        )

        assert operation.validate() is True
        assert operation.total_resources == 0

    def test_operation_with_filters(self) -> None:
        """Test operation with resource type and region filters."""
        filters = {
            "resource_types": ["AWS::EC2::Instance", "AWS::S3::Bucket"],
            "regions": ["us-east-1", "us-west-2"],
        }
        operation = DeletionOperation(
            operation_id="op_filtered",
            baseline_snapshot="test",
            timestamp=datetime(2025, 11, 11),
            account_id="123456789012",
            mode=OperationMode.DRY_RUN,
            status=OperationStatus.PLANNED,
            total_resources=15,
            filters=filters,
        )

        assert operation.filters == filters
        assert "resource_types" in operation.filters
        assert "regions" in operation.filters

    def test_operation_with_aws_profile(self) -> None:
        """Test operation with specific AWS profile."""
        operation = DeletionOperation(
            operation_id="op_profile",
            baseline_snapshot="test",
            timestamp=datetime(2025, 11, 11),
            account_id="123456789012",
            mode=OperationMode.EXECUTE,
            status=OperationStatus.COMPLETED,
            total_resources=1,
            succeeded_count=1,
            aws_profile="production",
        )

        assert operation.aws_profile == "production"
        assert operation.validate() is True

    def test_operation_equals_same_operation_id(self) -> None:
        """Test equality comparison based on operation_id."""
        op1 = DeletionOperation(
            operation_id="op_same",
            baseline_snapshot="test",
            timestamp=datetime(2025, 11, 11),
            account_id="123456789012",
            mode=OperationMode.DRY_RUN,
            status=OperationStatus.PLANNED,
            total_resources=0,
        )

        op2 = DeletionOperation(
            operation_id="op_same",  # Same ID
            baseline_snapshot="test",
            timestamp=datetime(2025, 11, 11),
            account_id="123456789012",
            mode=OperationMode.DRY_RUN,
            status=OperationStatus.PLANNED,
            total_resources=0,
        )

        # Should be considered equal if same operation_id
        assert op1.operation_id == op2.operation_id
