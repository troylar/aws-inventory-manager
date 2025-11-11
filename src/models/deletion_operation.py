"""Deletion operation model.

Represents a complete restore operation with metadata, filters, and execution context.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class OperationMode(Enum):
    """Operation execution mode."""

    DRY_RUN = "dry-run"
    EXECUTE = "execute"


class OperationStatus(Enum):
    """Operation execution status with state transitions."""

    PLANNED = "planned"
    EXECUTING = "executing"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass
class DeletionOperation:
    """Deletion operation entity.

    Represents a complete restore operation with metadata, filters, and execution
    context. Tracks overall progress and status of resource deletion.

    State transitions:
        planned → executing → completed (all succeeded)
        planned → executing → partial (some failed)
        planned → executing → failed (critical error)

    Attributes:
        operation_id: Unique identifier for the operation
        baseline_snapshot: Name of baseline snapshot to compare against
        timestamp: When operation was initiated (ISO 8601 UTC)
        account_id: AWS account ID (12-digit number)
        mode: dry-run or execute
        status: Current execution status
        total_resources: Total resources identified for deletion
        succeeded_count: Number successfully deleted (default: 0)
        failed_count: Number that failed to delete (default: 0)
        skipped_count: Number skipped due to protections (default: 0)
        aws_profile: AWS profile used for credentials (optional)
        filters: Resource type and region filters (optional)
        started_at: When execution started (optional, execute mode only)
        completed_at: When execution completed (optional)
        duration_seconds: Total execution duration (optional)
    """

    operation_id: str
    baseline_snapshot: str
    timestamp: datetime
    account_id: str
    mode: OperationMode
    status: OperationStatus
    total_resources: int
    succeeded_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    aws_profile: Optional[str] = None
    filters: Optional[dict] = field(default=None)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    def validate(self) -> bool:
        """Validate operation invariants.

        Validation rules:
            - succeeded_count + failed_count + skipped_count == total_resources
            - completed_at must be after started_at
            - dry-run mode must have planned status

        Returns:
            True if validation passes

        Raises:
            ValueError: If any validation rule fails
        """
        # Count validation
        if self.succeeded_count + self.failed_count + self.skipped_count != self.total_resources:
            raise ValueError("Resource counts don't match total")

        # Timing validation
        if self.completed_at and self.started_at:
            if self.completed_at < self.started_at:
                raise ValueError("Completion time before start time")

        # Mode/status consistency
        if self.mode == OperationMode.DRY_RUN and self.status != OperationStatus.PLANNED:
            raise ValueError("Dry-run mode must have planned status")

        return True
