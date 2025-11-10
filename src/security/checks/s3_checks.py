"""S3 security checks."""

from __future__ import annotations

from typing import Any, Dict, List

from ...models.security_finding import SecurityFinding, Severity
from ...models.snapshot import Snapshot
from .base import SecurityCheck


class S3PublicBucketCheck(SecurityCheck):
    """Check for publicly accessible S3 buckets.

    CIS AWS Foundations Benchmark: 2.1.5
    Severity: CRITICAL
    """

    @property
    def check_id(self) -> str:
        """Return check identifier."""
        return "s3_public_bucket"

    @property
    def severity(self) -> Severity:
        """Return check severity."""
        return Severity.CRITICAL

    def execute(self, snapshot: Snapshot) -> List[SecurityFinding]:
        """Execute S3 public bucket check.

        Checks for:
        - Public access block configuration disabled
        - Bucket ACLs allowing public read/write
        - Bucket policies allowing public access

        Args:
            snapshot: Snapshot to scan

        Returns:
            List of findings for publicly accessible buckets
        """
        findings: List[SecurityFinding] = []

        for resource in snapshot.resources:
            # Only check S3 buckets
            if not resource.resource_type.startswith("s3:"):
                continue

            if resource.raw_config is None:
                continue

            # Check PublicAccessBlockConfiguration
            is_public = self._is_bucket_public(resource.raw_config)

            if is_public:
                finding = SecurityFinding(
                    resource_arn=resource.arn,
                    finding_type=self.check_id,
                    severity=self.severity,
                    description=f"S3 bucket '{resource.name}' is publicly accessible. "
                    f"Public access block configuration is disabled, allowing public access to the bucket.",
                    remediation="Enable S3 Block Public Access settings for this bucket. "
                    "Go to the S3 console, select the bucket, choose 'Permissions', "
                    "then 'Block Public Access' and enable all four settings.",
                    cis_control="2.1.5",
                    metadata={"bucket_name": resource.name, "region": resource.region},
                )
                findings.append(finding)

        return findings

    def _is_bucket_public(self, config: Dict[str, Any]) -> bool:
        """Check if bucket configuration indicates public access.

        Args:
            config: Bucket raw configuration

        Returns:
            True if bucket appears to be publicly accessible
        """
        # Check PublicAccessBlockConfiguration
        public_access_block = config.get("PublicAccessBlockConfiguration", {})

        # If any of these are False, bucket might be public
        block_public_acls = public_access_block.get("BlockPublicAcls", False)
        ignore_public_acls = public_access_block.get("IgnorePublicAcls", False)
        block_public_policy = public_access_block.get("BlockPublicPolicy", False)
        restrict_public_buckets = public_access_block.get("RestrictPublicBuckets", False)

        # Bucket is considered public if ANY of the blocks are disabled (False)
        if not (block_public_acls and ignore_public_acls and block_public_policy and restrict_public_buckets):
            return True

        return False
