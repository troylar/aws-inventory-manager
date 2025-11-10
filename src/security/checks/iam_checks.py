"""IAM security checks."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from ...models.security_finding import SecurityFinding, Severity
from ...models.snapshot import Snapshot
from .base import SecurityCheck


class IAMCredentialAgeCheck(SecurityCheck):
    """Check for IAM users with access keys older than 90 days.

    CIS AWS Foundations Benchmark: 1.3 or 1.4
    Severity: MEDIUM
    """

    @property
    def check_id(self) -> str:
        """Return check identifier."""
        return "iam_credential_age"

    @property
    def severity(self) -> Severity:
        """Return check severity."""
        return Severity.MEDIUM

    def execute(self, snapshot: Snapshot) -> List[SecurityFinding]:
        """Execute IAM credential age check.

        Checks for:
        - IAM users with access keys older than 90 days

        Args:
            snapshot: Snapshot to scan

        Returns:
            List of findings for IAM users with old credentials
        """
        findings: List[SecurityFinding] = []
        threshold_days = 90

        for resource in snapshot.resources:
            # Only check IAM users
            if not resource.resource_type.startswith("iam:user"):
                continue

            if resource.raw_config is None:
                continue

            # Check access keys
            access_keys = resource.raw_config.get("AccessKeys", [])
            for key in access_keys:
                create_date_str = key.get("CreateDate")
                if not create_date_str:
                    continue

                # Parse the date string (handle ISO format)
                if isinstance(create_date_str, str):
                    # Remove trailing 'Z' if present and parse as ISO format
                    create_date_str = create_date_str.rstrip("Z")
                    if "+" in create_date_str:
                        # Has timezone
                        create_date = datetime.fromisoformat(create_date_str)
                    else:
                        # No timezone, add UTC
                        create_date = datetime.fromisoformat(create_date_str).replace(tzinfo=timezone.utc)
                else:
                    # Assume it's already a datetime object
                    create_date = create_date_str
                    if create_date.tzinfo is None:
                        create_date = create_date.replace(tzinfo=timezone.utc)

                # Calculate age in days
                days_old = (datetime.now(timezone.utc) - create_date).days

                # Check if key is older than threshold (> 90 days, not >= 90 days)
                if days_old > threshold_days:
                    finding = SecurityFinding(
                        resource_arn=resource.arn,
                        finding_type=self.check_id,
                        severity=self.severity,
                        description=f"IAM user '{resource.name}' has an access key that is {days_old} days old, "
                        f"exceeding the {threshold_days}-day threshold. Old credentials increase security risk.",
                        remediation="Rotate the access key for this IAM user. "
                        "Create a new access key, update all applications using the old key, "
                        "then deactivate and delete the old key. "
                        "Consider using IAM roles instead of long-term credentials.",
                        cis_control="1.4",
                        metadata={
                            "user_name": resource.name,
                            "key_age_days": days_old,
                            "key_id": key.get("AccessKeyId", "unknown"),
                        },
                    )
                    findings.append(finding)
                    # Only report one finding per user (for the oldest key)
                    break

        return findings
