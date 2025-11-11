"""Tests for AuditStorage class.

Test coverage for audit log storage and retrieval with YAML format.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import yaml

from src.models.deletion_operation import DeletionOperation, OperationMode, OperationStatus
from src.models.deletion_record import DeletionRecord, DeletionStatus
from src.restore.audit import AuditStorage


class TestAuditStorage:
    """Test suite for AuditStorage class."""

    @pytest.fixture
    def temp_storage_dir(self, tmp_path: Path) -> Path:
        """Create temporary storage directory for tests."""
        storage_dir = tmp_path / ".snapshots" / "audit-logs"
        storage_dir.mkdir(parents=True)
        return storage_dir

    @pytest.fixture
    def audit_storage(self, temp_storage_dir: Path) -> AuditStorage:
        """Create AuditStorage instance with temp directory."""
        return AuditStorage(storage_dir=str(temp_storage_dir))

    def test_init_creates_storage_directory(self, tmp_path: Path) -> None:
        """Test initialization creates audit-logs directory if missing."""
        storage_dir = tmp_path / ".snapshots-test" / "audit-logs"
        assert not storage_dir.exists()

        AuditStorage(storage_dir=str(storage_dir))

        assert storage_dir.exists()
        assert storage_dir.is_dir()

    def test_log_operation_creates_yaml_file(self, audit_storage: AuditStorage, temp_storage_dir: Path) -> None:
        """Test logging operation creates YAML file with correct structure."""
        operation = DeletionOperation(
            operation_id="op_123",
            baseline_snapshot="test-snapshot",
            timestamp=datetime(2025, 11, 11, 15, 30, 0),
            account_id="123456789012",
            mode=OperationMode.EXECUTE,
            status=OperationStatus.COMPLETED,
            total_resources=2,
            succeeded_count=1,
            failed_count=1,
        )

        records = [
            DeletionRecord(
                record_id="rec_001",
                operation_id="op_123",
                resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-001",
                resource_id="i-001",
                resource_type="aws:ec2:instance",
                region="us-east-1",
                timestamp=datetime(2025, 11, 11, 15, 31, 0),
                status=DeletionStatus.SUCCEEDED,
            ),
            DeletionRecord(
                record_id="rec_002",
                operation_id="op_123",
                resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-002",
                resource_id="i-002",
                resource_type="aws:ec2:instance",
                region="us-east-1",
                timestamp=datetime(2025, 11, 11, 15, 31, 5),
                status=DeletionStatus.FAILED,
                error_code="UnauthorizedOperation",
            ),
        ]

        audit_storage.log_operation(operation, records)

        # Verify file was created
        year_month_dir = temp_storage_dir / "2025" / "11"
        assert year_month_dir.exists()

        audit_file = year_month_dir / "operation-op_123.yaml"
        assert audit_file.exists()

        # Verify file contents
        with open(audit_file, "r") as f:
            data = yaml.safe_load(f)

        assert data["metadata"]["version"] == "1.0"
        assert data["metadata"]["log_type"] == "resource_deletion"
        assert data["operation"]["operation_id"] == "op_123"
        assert data["operation"]["status"] == "completed"
        assert len(data["records"]) == 2
        assert data["records"][0]["status"] == "succeeded"
        assert data["records"][1]["status"] == "failed"

    def test_log_operation_overwrites_existing_file(self, audit_storage: AuditStorage, temp_storage_dir: Path) -> None:
        """Test logging operation overwrites existing audit log."""
        operation = DeletionOperation(
            operation_id="op_456",
            baseline_snapshot="test",
            timestamp=datetime(2025, 11, 11),
            account_id="123456789012",
            mode=OperationMode.EXECUTE,
            status=OperationStatus.COMPLETED,
            total_resources=0,
        )

        # Log first time
        audit_storage.log_operation(operation, [])

        # Log again (overwrite)
        operation.succeeded_count = 5
        audit_storage.log_operation(operation, [])

        # Verify only one file exists with updated data
        year_month_dir = temp_storage_dir / "2025" / "11"
        audit_files = list(year_month_dir.glob("operation-op_456.yaml"))
        assert len(audit_files) == 1

        with open(audit_files[0], "r") as f:
            data = yaml.safe_load(f)
        assert data["operation"]["succeeded_count"] == 5

    def test_get_operation_returns_correct_data(self, audit_storage: AuditStorage) -> None:
        """Test retrieving operation by ID returns correct data."""
        operation = DeletionOperation(
            operation_id="op_789",
            baseline_snapshot="test",
            timestamp=datetime(2025, 11, 11),
            account_id="123456789012",
            mode=OperationMode.EXECUTE,
            status=OperationStatus.COMPLETED,
            total_resources=1,
            succeeded_count=1,
        )

        record = DeletionRecord(
            record_id="rec_001",
            operation_id="op_789",
            resource_arn="arn:aws:s3:::my-bucket",
            resource_id="my-bucket",
            resource_type="aws:s3:bucket",
            region="us-east-1",
            timestamp=datetime(2025, 11, 11),
            status=DeletionStatus.SUCCEEDED,
        )

        # Log operation
        audit_storage.log_operation(operation, [record])

        # Retrieve operation
        retrieved = audit_storage.get_operation("op_789")

        assert retrieved is not None
        assert retrieved["operation"]["operation_id"] == "op_789"
        assert retrieved["operation"]["baseline_snapshot"] == "test"
        assert len(retrieved["records"]) == 1
        assert retrieved["records"][0]["resource_id"] == "my-bucket"

    def test_get_operation_not_found_returns_none(self, audit_storage: AuditStorage) -> None:
        """Test retrieving non-existent operation returns None."""
        result = audit_storage.get_operation("op_nonexistent")
        assert result is None

    def test_query_operations_returns_all_in_date_range(self, audit_storage: AuditStorage) -> None:
        """Test querying operations within date range."""
        # Create operations on different dates
        op1 = DeletionOperation(
            operation_id="op_001",
            baseline_snapshot="test",
            timestamp=datetime(2025, 11, 10, 10, 0, 0),
            account_id="123456789012",
            mode=OperationMode.EXECUTE,
            status=OperationStatus.COMPLETED,
            total_resources=0,
        )

        op2 = DeletionOperation(
            operation_id="op_002",
            baseline_snapshot="test",
            timestamp=datetime(2025, 11, 11, 12, 0, 0),
            account_id="123456789012",
            mode=OperationMode.EXECUTE,
            status=OperationStatus.COMPLETED,
            total_resources=0,
        )

        op3 = DeletionOperation(
            operation_id="op_003",
            baseline_snapshot="test",
            timestamp=datetime(2025, 11, 12, 14, 0, 0),
            account_id="123456789012",
            mode=OperationMode.EXECUTE,
            status=OperationStatus.COMPLETED,
            total_resources=0,
        )

        audit_storage.log_operation(op1, [])
        audit_storage.log_operation(op2, [])
        audit_storage.log_operation(op3, [])

        # Query date range
        results = audit_storage.query_operations(
            since=datetime(2025, 11, 11, 0, 0, 0),
            until=datetime(2025, 11, 11, 23, 59, 59),
        )

        assert len(results) == 1
        assert results[0]["operation"]["operation_id"] == "op_002"

    def test_query_operations_without_filters_returns_all(self, audit_storage: AuditStorage) -> None:
        """Test querying operations without filters returns all logs."""
        op1 = DeletionOperation(
            operation_id="op_all_001",
            baseline_snapshot="test",
            timestamp=datetime(2025, 11, 10),
            account_id="123456789012",
            mode=OperationMode.EXECUTE,
            status=OperationStatus.COMPLETED,
            total_resources=0,
        )

        op2 = DeletionOperation(
            operation_id="op_all_002",
            baseline_snapshot="test",
            timestamp=datetime(2025, 11, 11),
            account_id="123456789012",
            mode=OperationMode.EXECUTE,
            status=OperationStatus.PARTIAL,
            total_resources=0,
        )

        audit_storage.log_operation(op1, [])
        audit_storage.log_operation(op2, [])

        results = audit_storage.query_operations()

        assert len(results) >= 2
        operation_ids = [r["operation"]["operation_id"] for r in results]
        assert "op_all_001" in operation_ids
        assert "op_all_002" in operation_ids

    def test_query_operations_empty_directory_returns_empty_list(self, audit_storage: AuditStorage) -> None:
        """Test querying operations in empty directory returns empty list."""
        results = audit_storage.query_operations()
        assert results == []

    def test_init_with_default_storage_dir(self) -> None:
        """Test initialization uses default storage directory."""
        audit_storage = AuditStorage()
        expected_path = Path.home() / ".snapshots" / "audit-logs"
        assert audit_storage.storage_dir == expected_path

    def test_get_operation_ignores_non_directory_files(
        self, audit_storage: AuditStorage, temp_storage_dir: Path
    ) -> None:
        """Test get_operation ignores non-directory files in year/month directories."""
        # Create year directory with a file (not a subdirectory)
        year_dir = temp_storage_dir / "2025"
        year_dir.mkdir()
        year_file = year_dir / "not_a_month_dir.txt"
        year_file.write_text("This is a file, not a directory")

        # Create month directory with an operation
        month_dir = year_dir / "11"
        month_dir.mkdir()
        operation = DeletionOperation(
            operation_id="op_test",
            baseline_snapshot="test",
            timestamp=datetime(2025, 11, 11),
            account_id="123456789012",
            mode=OperationMode.EXECUTE,
            status=OperationStatus.COMPLETED,
            total_resources=0,
        )
        audit_storage.log_operation(operation, [])

        # Should find the operation despite the non-directory file
        result = audit_storage.get_operation("op_test")
        assert result is not None
        assert result["operation"]["operation_id"] == "op_test"

    def test_get_operation_ignores_files_in_month_directory(
        self, audit_storage: AuditStorage, temp_storage_dir: Path
    ) -> None:
        """Test get_operation ignores non-directory files in month directories."""
        # Create directory structure
        year_dir = temp_storage_dir / "2025"
        year_dir.mkdir()
        month_dir = year_dir / "11"
        month_dir.mkdir()

        # Create a file (not a directory) in month directory
        month_file = month_dir / "not_a_dir.txt"
        month_file.write_text("This is a file")

        # Create an operation
        operation = DeletionOperation(
            operation_id="op_ignore",
            baseline_snapshot="test",
            timestamp=datetime(2025, 11, 11),
            account_id="123456789012",
            mode=OperationMode.EXECUTE,
            status=OperationStatus.COMPLETED,
            total_resources=0,
        )
        audit_storage.log_operation(operation, [])

        # Should find the operation despite the non-directory file
        result = audit_storage.get_operation("op_ignore")
        assert result is not None

    def test_query_operations_ignores_non_directory_files(
        self, audit_storage: AuditStorage, temp_storage_dir: Path
    ) -> None:
        """Test query_operations ignores non-directory files in year/month directories."""
        # Create year directory with a file
        year_dir = temp_storage_dir / "2025"
        year_dir.mkdir()
        year_file = year_dir / "readme.txt"
        year_file.write_text("Some documentation")

        # Create month directory with a file
        month_dir = year_dir / "11"
        month_dir.mkdir()
        month_file = month_dir / "notes.txt"
        month_file.write_text("Some notes")

        # Create operations
        op1 = DeletionOperation(
            operation_id="op_q1",
            baseline_snapshot="test",
            timestamp=datetime(2025, 11, 10),
            account_id="123456789012",
            mode=OperationMode.EXECUTE,
            status=OperationStatus.COMPLETED,
            total_resources=0,
        )
        op2 = DeletionOperation(
            operation_id="op_q2",
            baseline_snapshot="test",
            timestamp=datetime(2025, 11, 11),
            account_id="123456789012",
            mode=OperationMode.EXECUTE,
            status=OperationStatus.COMPLETED,
            total_resources=0,
        )

        audit_storage.log_operation(op1, [])
        audit_storage.log_operation(op2, [])

        # Should return all operations despite non-directory files
        results = audit_storage.query_operations()
        assert len(results) == 2
        operation_ids = [r["operation"]["operation_id"] for r in results]
        assert "op_q1" in operation_ids
        assert "op_q2" in operation_ids

    def test_get_operation_ignores_files_at_root_level(
        self, audit_storage: AuditStorage, temp_storage_dir: Path
    ) -> None:
        """Test get_operation ignores files at root level (not year directories)."""
        # Create a file at root level FIRST (before any directories)
        # Use a name that sorts before "2025" to ensure it's checked first
        root_file = temp_storage_dir / "000-readme.txt"
        root_file.write_text("This is a readme file")

        # Verify the file exists
        assert root_file.exists()
        assert root_file.is_file()

        # Now create the year/month structure and operation
        year_dir = temp_storage_dir / "2025"
        year_dir.mkdir()
        month_dir = year_dir / "11"
        month_dir.mkdir()

        operation = DeletionOperation(
            operation_id="op_root_test",
            baseline_snapshot="test",
            timestamp=datetime(2025, 11, 11),
            account_id="123456789012",
            mode=OperationMode.EXECUTE,
            status=OperationStatus.COMPLETED,
            total_resources=0,
        )
        audit_storage.log_operation(operation, [])

        # Verify storage_dir contains both file and directory
        items = list(audit_storage.storage_dir.glob("*"))
        assert len(items) >= 2  # At least the file and the 2025 directory
        has_file = any(not item.is_dir() for item in items)
        assert has_file, f"No file found in {items}"

        # get_operation will iterate through glob("*") which includes the file
        # It should skip the file (continue) and check the 2025 directory
        result = audit_storage.get_operation("op_root_test")
        assert result is not None
        assert result["operation"]["operation_id"] == "op_root_test"

    def test_query_operations_ignores_files_at_root_level(
        self, audit_storage: AuditStorage, temp_storage_dir: Path
    ) -> None:
        """Test query_operations ignores files at root level."""
        # Create a file at root level
        root_file = temp_storage_dir / "notes.md"
        root_file.write_text("Some notes")

        # Create operations
        op1 = DeletionOperation(
            operation_id="op_root_q1",
            baseline_snapshot="test",
            timestamp=datetime(2025, 11, 10),
            account_id="123456789012",
            mode=OperationMode.EXECUTE,
            status=OperationStatus.COMPLETED,
            total_resources=0,
        )

        audit_storage.log_operation(op1, [])

        # Should return operations and ignore root-level file
        results = audit_storage.query_operations()
        assert len(results) == 1
        assert results[0]["operation"]["operation_id"] == "op_root_q1"
