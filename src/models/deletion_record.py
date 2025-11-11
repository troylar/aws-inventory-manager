"""Deletion record model.

Individual resource deletion attempt with result and metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class DeletionStatus(Enum):
    """Individual resource deletion status."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class DeletionRecord:
    """Deletion record entity.

    Represents an individual resource deletion attempt with result and metadata.
    Each record belongs to a DeletionOperation and tracks the outcome for a single
    resource.

    Validation rules:
        - status=succeeded: no error_code or protection_reason
        - status=failed: requires error_code
        - status=skipped: requires protection_reason
        - resource_arn must start with "arn:aws:"
        - estimated_monthly_cost must be >= 0 if provided

    Attributes:
        record_id: Unique identifier for this record
        operation_id: Parent operation identifier
        resource_arn: AWS Resource Name (ARN format)
        resource_id: Resource identifier (ID, name)
        resource_type: AWS resource type (format: aws:service:type)
        region: AWS region
        timestamp: When deletion was attempted (ISO 8601 UTC)
        status: Deletion outcome (succeeded, failed, skipped)
        error_code: AWS error code if failed (optional)
        error_message: Human-readable error if failed (optional)
        protection_reason: Why resource was skipped (optional)
        deletion_tier: Tier (1-5) for deletion ordering (optional)
        tags: Resource tags at deletion time (optional)
        estimated_monthly_cost: Estimated cost in USD (optional)
    """

    record_id: str
    operation_id: str
    resource_arn: str
    resource_id: str
    resource_type: str
    region: str
    timestamp: datetime
    status: DeletionStatus
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    protection_reason: Optional[str] = None
    deletion_tier: Optional[int] = None
    tags: Optional[dict] = field(default=None)
    estimated_monthly_cost: Optional[float] = None

    def validate(self) -> bool:
        """Validate record invariants.

        Returns:
            True if validation passes

        Raises:
            ValueError: If any validation rule fails
        """
        # Status-specific validation
        if self.status == DeletionStatus.FAILED:
            if not self.error_code:
                raise ValueError("Failed status requires error_code")
        elif self.status == DeletionStatus.SKIPPED:
            if not self.protection_reason:
                raise ValueError("Skipped status requires protection_reason")
        elif self.status == DeletionStatus.SUCCEEDED:
            if self.error_code or self.protection_reason:
                raise ValueError("Succeeded status cannot have error or protection reason")

        # ARN format validation
        if not self.resource_arn.startswith("arn:aws:"):
            raise ValueError("Invalid ARN format")

        # Cost validation
        if self.estimated_monthly_cost is not None and self.estimated_monthly_cost < 0:
            raise ValueError("Cost cannot be negative")

        return True
