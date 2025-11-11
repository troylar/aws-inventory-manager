"""RDS security checks."""

from __future__ import annotations

from typing import Any, Dict, List

from ...models.security_finding import SecurityFinding, Severity
from ...models.snapshot import Snapshot
from .base import SecurityCheck


class RDSPublicCheck(SecurityCheck):
    """Check for RDS instances with security issues.

    Checks for:
    - Publicly accessible RDS instances (PubliclyAccessible=True)
    - Unencrypted RDS storage (StorageEncrypted=False)

    Severity: HIGH
    """

    @property
    def check_id(self) -> str:
        """Return check identifier."""
        return "rds_publicly_accessible"

    @property
    def severity(self) -> Severity:
        """Return check severity."""
        return Severity.HIGH

    def execute(self, snapshot: Snapshot) -> List[SecurityFinding]:
        """Execute RDS security checks.

        Checks for:
        - PubliclyAccessible set to True
        - StorageEncrypted set to False

        Args:
            snapshot: Snapshot to scan

        Returns:
            List of findings for RDS security issues
        """
        findings: List[SecurityFinding] = []

        for resource in snapshot.resources:
            # Only check RDS resources
            if not resource.resource_type.startswith("rds:"):
                continue

            if resource.raw_config is None:
                continue

            # Check for public accessibility
            if self._is_publicly_accessible(resource.raw_config):
                finding = self._create_public_finding(resource.name, resource.arn, resource.region)
                findings.append(finding)

            # Check for unencrypted storage
            if not self._is_encrypted(resource.raw_config):
                finding = self._create_encryption_finding(resource.name, resource.arn, resource.region)
                findings.append(finding)

        return findings

    def _is_publicly_accessible(self, config: Dict[str, Any]) -> bool:
        """Check if RDS instance is publicly accessible.

        Args:
            config: RDS instance raw configuration

        Returns:
            True if PubliclyAccessible is True
        """
        return config.get("PubliclyAccessible", False)

    def _is_encrypted(self, config: Dict[str, Any]) -> bool:
        """Check if RDS instance storage is encrypted.

        Args:
            config: RDS instance raw configuration

        Returns:
            True if StorageEncrypted is True
        """
        return config.get("StorageEncrypted", False)

    def _create_public_finding(self, db_identifier: str, arn: str, region: str) -> SecurityFinding:
        """Create a finding for publicly accessible RDS instance.

        Args:
            db_identifier: Database instance identifier
            arn: Resource ARN
            region: AWS region

        Returns:
            SecurityFinding for public accessibility issue
        """
        return SecurityFinding(
            resource_arn=arn,
            finding_type=self.check_id,
            severity=self.severity,
            description=f"RDS instance '{db_identifier}' is publicly accessible. "
            f"The database is configured with PubliclyAccessible=True, which allows "
            f"connections from the internet if security groups permit.",
            remediation="Disable public accessibility for this RDS instance. "
            "Use AWS CLI: 'aws rds modify-db-instance --db-instance-identifier "
            f"{db_identifier} --no-publicly-accessible' or modify the instance "
            "in the RDS console by setting 'Publicly accessible' to 'No' under "
            "Connectivity & security settings.",
            metadata={"db_identifier": db_identifier, "region": region},
        )

    def _create_encryption_finding(self, db_identifier: str, arn: str, region: str) -> SecurityFinding:
        """Create a finding for unencrypted RDS instance.

        Args:
            db_identifier: Database instance identifier
            arn: Resource ARN
            region: AWS region

        Returns:
            SecurityFinding for encryption issue
        """
        return SecurityFinding(
            resource_arn=arn,
            finding_type=self.check_id,
            severity=self.severity,
            description=f"RDS instance '{db_identifier}' does not have storage encryption enabled. "
            f"The database is configured with StorageEncrypted=False, which means data at rest "
            f"is not encrypted.",
            remediation="Enable encryption for this RDS instance. Note: Encryption cannot be "
            "enabled on existing instances. You must create a snapshot, copy it with encryption "
            "enabled, and restore a new instance from the encrypted snapshot. "
            "Use AWS CLI: 'aws rds copy-db-snapshot --source-db-snapshot-identifier <snapshot-id> "
            "--target-db-snapshot-identifier <encrypted-snapshot-id> --kms-key-id <kms-key>' "
            "then restore from the encrypted snapshot.",
            metadata={"db_identifier": db_identifier, "region": region},
        )
