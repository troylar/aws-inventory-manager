"""Security finding model for representing detected security issues in AWS resources."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class Severity(Enum):
    """Security finding severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class SecurityFinding:
    """Represents a detected security misconfiguration in an AWS resource.

    Attributes:
        resource_arn: AWS ARN of the resource with the security issue
        finding_type: Type of security issue (e.g., "public_s3_bucket", "open_security_group")
        severity: Severity level of the finding
        description: Human-readable description of the issue
        remediation: Guidance on how to fix the issue
        cis_control: Optional CIS AWS Foundations Benchmark control ID (e.g., "2.1.5")
        metadata: Additional context-specific metadata
    """

    resource_arn: str
    finding_type: str
    severity: Severity
    description: str
    remediation: str
    cis_control: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        """Validate SecurityFinding fields after initialization."""
        # Validate ARN format (basic check)
        if not self.resource_arn or not self.resource_arn.startswith("arn:"):
            raise ValueError(f"Invalid ARN format: {self.resource_arn}")

        # Validate severity is Severity enum
        if not isinstance(self.severity, Severity):
            raise ValueError(f"Invalid severity type: {type(self.severity)}. Must be Severity enum.")

        # Validate required string fields are not empty
        if not self.finding_type:
            raise ValueError("finding_type cannot be empty")
        if not self.description:
            raise ValueError("description cannot be empty")
        if not self.remediation:
            raise ValueError("remediation cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        """Convert SecurityFinding to dictionary representation.

        Returns:
            Dictionary with all finding attributes
        """
        return {
            "resource_arn": self.resource_arn,
            "finding_type": self.finding_type,
            "severity": self.severity.value,
            "description": self.description,
            "remediation": self.remediation,
            "cis_control": self.cis_control,
            "metadata": self.metadata or {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SecurityFinding:
        """Create SecurityFinding from dictionary representation.

        Args:
            data: Dictionary with finding attributes

        Returns:
            SecurityFinding instance

        Raises:
            ValueError: If severity value is invalid
        """
        severity_str = data.get("severity", "").lower()
        try:
            severity = Severity(severity_str)
        except ValueError:
            raise ValueError(f"Invalid severity value: {severity_str}")

        return cls(
            resource_arn=data["resource_arn"],
            finding_type=data["finding_type"],
            severity=severity,
            description=data["description"],
            remediation=data["remediation"],
            cis_control=data.get("cis_control"),
            metadata=data.get("metadata"),
        )
