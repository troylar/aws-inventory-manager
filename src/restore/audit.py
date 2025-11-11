"""Audit storage for deletion operations.

Stores and retrieves audit logs in YAML format for compliance and troubleshooting.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from src.models.deletion_operation import DeletionOperation
from src.models.deletion_record import DeletionRecord


class AuditStorage:
    """Audit log storage and retrieval.

    Stores deletion operation audit logs as YAML files organized by year/month.
    Supports querying operations by date range and retrieving detailed operation logs.

    Storage structure:
        ~/.snapshots/audit-logs/
            2025/
                11/
                    operation-op_123.yaml
                    operation-op_456.yaml

    Attributes:
        storage_dir: Base directory for audit logs
    """

    def __init__(self, storage_dir: Optional[str] = None) -> None:
        """Initialize audit storage.

        Args:
            storage_dir: Base directory for audit logs (default: ~/.snapshots/audit-logs)
        """
        if storage_dir is None:
            storage_dir = str(Path.home() / ".snapshots" / "audit-logs")

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def log_operation(self, operation: DeletionOperation, records: list[DeletionRecord]) -> None:
        """Log deletion operation to audit storage.

        Creates YAML file with operation metadata and all deletion records.
        Overwrites existing log if operation ID already exists.

        Args:
            operation: Deletion operation to log
            records: List of deletion records for this operation
        """
        # Create year/month directory structure
        year = operation.timestamp.year
        month = operation.timestamp.month
        year_month_dir = self.storage_dir / str(year) / f"{month:02d}"
        year_month_dir.mkdir(parents=True, exist_ok=True)

        # Create audit log structure
        audit_data = {
            "metadata": {
                "version": "1.0",
                "log_type": "resource_deletion",
                "created_at": datetime.utcnow().isoformat() + "Z",
            },
            "operation": {
                "operation_id": operation.operation_id,
                "baseline_snapshot": operation.baseline_snapshot,
                "timestamp": operation.timestamp.isoformat() + "Z",
                "aws_profile": operation.aws_profile,
                "account_id": operation.account_id,
                "mode": operation.mode.value,
                "status": operation.status.value,
                "filters": operation.filters,
                "total_resources": operation.total_resources,
                "succeeded_count": operation.succeeded_count,
                "failed_count": operation.failed_count,
                "skipped_count": operation.skipped_count,
                "started_at": operation.started_at.isoformat() + "Z" if operation.started_at else None,
                "completed_at": operation.completed_at.isoformat() + "Z" if operation.completed_at else None,
                "duration_seconds": operation.duration_seconds,
            },
            "records": [
                {
                    "record_id": record.record_id,
                    "operation_id": record.operation_id,
                    "resource_arn": record.resource_arn,
                    "resource_id": record.resource_id,
                    "resource_type": record.resource_type,
                    "region": record.region,
                    "timestamp": record.timestamp.isoformat() + "Z",
                    "status": record.status.value,
                    "error_code": record.error_code,
                    "error_message": record.error_message,
                    "protection_reason": record.protection_reason,
                    "deletion_tier": record.deletion_tier,
                    "tags": record.tags,
                    "estimated_monthly_cost": record.estimated_monthly_cost,
                }
                for record in records
            ],
        }

        # Write YAML file
        audit_file = year_month_dir / f"operation-{operation.operation_id}.yaml"
        with open(audit_file, "w") as f:
            yaml.dump(audit_data, f, default_flow_style=False, sort_keys=False)

    def get_operation(self, operation_id: str) -> Optional[dict]:
        """Retrieve operation audit log by ID.

        Args:
            operation_id: Operation ID to retrieve

        Returns:
            Audit log dictionary if found, None otherwise
        """
        # Search all year/month directories
        for year_dir in self.storage_dir.glob("*"):
            if not year_dir.is_dir():
                continue

            for month_dir in year_dir.glob("*"):
                if not month_dir.is_dir():
                    continue

                audit_file = month_dir / f"operation-{operation_id}.yaml"
                if audit_file.exists():
                    with open(audit_file, "r") as f:
                        return yaml.safe_load(f)

        return None

    def query_operations(self, since: Optional[datetime] = None, until: Optional[datetime] = None) -> list[dict]:
        """Query operations within date range.

        Args:
            since: Start date (inclusive), None for all
            until: End date (inclusive), None for all

        Returns:
            List of operation audit logs matching criteria
        """
        results = []

        # Search all year/month directories
        for year_dir in sorted(self.storage_dir.glob("*")):
            if not year_dir.is_dir():
                continue

            for month_dir in sorted(year_dir.glob("*")):
                if not month_dir.is_dir():
                    continue

                for audit_file in sorted(month_dir.glob("operation-*.yaml")):
                    with open(audit_file, "r") as f:
                        audit_data = yaml.safe_load(f)

                    # Parse timestamp
                    timestamp_str = audit_data["operation"]["timestamp"]
                    timestamp = datetime.fromisoformat(timestamp_str.rstrip("Z"))

                    # Filter by date range
                    if since and timestamp < since:
                        continue
                    if until and timestamp > until:
                        continue

                    results.append(audit_data)

        return results
