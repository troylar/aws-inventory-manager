"""Secrets Manager security checks."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from ...models.security_finding import SecurityFinding, Severity
from ...models.snapshot import Snapshot
from .base import SecurityCheck


class SecretsRotationCheck(SecurityCheck):
    """Check for Secrets Manager secrets not rotated in 90+ days.

    Severity: MEDIUM
    """

    @property
    def check_id(self) -> str:
        """Return check identifier."""
        return "secrets_rotation_age"

    @property
    def severity(self) -> Severity:
        """Return check severity."""
        return Severity.MEDIUM

    def execute(self, snapshot: Snapshot) -> List[SecurityFinding]:
        """Execute secrets rotation check.

        Checks for:
        - Secrets Manager secrets not rotated in 90+ days

        Args:
            snapshot: Snapshot to scan

        Returns:
            List of findings for secrets not rotated recently
        """
        findings: List[SecurityFinding] = []
        threshold_days = 90

        for resource in snapshot.resources:
            # Only check Secrets Manager secrets
            if not resource.resource_type.startswith("secretsmanager:"):
                continue

            if resource.raw_config is None:
                continue

            # Check last rotated date
            last_rotated_str = resource.raw_config.get("LastRotatedDate")
            if not last_rotated_str:
                continue

            # Parse the date string (handle ISO format)
            if isinstance(last_rotated_str, str):
                # Remove trailing 'Z' if present and parse as ISO format
                last_rotated_str = last_rotated_str.rstrip("Z")
                if "+" in last_rotated_str:
                    # Has timezone
                    last_rotated = datetime.fromisoformat(last_rotated_str)
                else:
                    # No timezone, add UTC
                    last_rotated = datetime.fromisoformat(last_rotated_str).replace(tzinfo=timezone.utc)
            else:
                # Assume it's already a datetime object
                last_rotated = last_rotated_str
                if last_rotated.tzinfo is None:
                    last_rotated = last_rotated.replace(tzinfo=timezone.utc)

            # Calculate days since rotation
            days_since_rotation = (datetime.now(timezone.utc) - last_rotated).days

            # Check if secret hasn't been rotated recently (> 90 days, not >= 90 days)
            if days_since_rotation > threshold_days:
                finding = SecurityFinding(
                    resource_arn=resource.arn,
                    finding_type=self.check_id,
                    severity=self.severity,
                    description=f"Secret '{resource.name}' has not been rotated in {days_since_rotation} days, "
                    f"exceeding the {threshold_days}-day threshold. "
                    f"Regular rotation reduces risk of credential compromise.",
                    remediation="Rotate the secret in AWS Secrets Manager. "
                    "You can manually rotate the secret or enable automatic rotation. "
                    "Go to the Secrets Manager console, select the secret, and choose 'Rotate secret immediately'.",
                    metadata={
                        "secret_name": resource.name,
                        "days_since_rotation": days_since_rotation,
                        "region": resource.region,
                    },
                )
                findings.append(finding)

        return findings
