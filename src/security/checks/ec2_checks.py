"""EC2 security checks."""

from __future__ import annotations

from typing import Any, Dict, List

from ...models.security_finding import SecurityFinding, Severity
from ...models.snapshot import Snapshot
from .base import SecurityCheck


class EC2IMDSv1Check(SecurityCheck):
    """Check for EC2 instances with IMDSv1 enabled.

    EC2 instances should require IMDSv2 (Instance Metadata Service Version 2)
    for better security. IMDSv1 is vulnerable to SSRF attacks.

    Severity: MEDIUM
    """

    @property
    def check_id(self) -> str:
        """Return check identifier."""
        return "ec2_imdsv1_enabled"

    @property
    def severity(self) -> Severity:
        """Return check severity."""
        return Severity.MEDIUM

    def execute(self, snapshot: Snapshot) -> List[SecurityFinding]:
        """Execute EC2 IMDSv1 check.

        Checks for:
        - EC2 instances with MetadataOptions.HttpTokens = "optional" (IMDSv1 enabled)

        Args:
            snapshot: Snapshot to scan

        Returns:
            List of findings for EC2 instances with IMDSv1 enabled
        """
        findings: List[SecurityFinding] = []

        for resource in snapshot.resources:
            # Only check EC2 instances
            if not resource.resource_type.startswith("ec2:instance"):
                continue

            if resource.raw_config is None:
                continue

            # Check if IMDSv1 is enabled
            if self._is_imdsv1_enabled(resource.raw_config):
                instance_id = resource.raw_config.get("InstanceId", "unknown")
                finding = SecurityFinding(
                    resource_arn=resource.arn,
                    finding_type=self.check_id,
                    severity=self.severity,
                    description=f"EC2 instance '{instance_id}' has IMDSv1 enabled. "
                    f"The instance allows optional use of session tokens for metadata access, "
                    f"making it vulnerable to SSRF attacks.",
                    remediation="Require IMDSv2 for this EC2 instance. "
                    "Use the AWS CLI command: "
                    f"'aws ec2 modify-instance-metadata-options --instance-id {instance_id} "
                    "--http-tokens required --http-endpoint enabled' "
                    "or update the instance's metadata options in the EC2 console to require IMDSv2.",
                    metadata={"instance_id": instance_id, "region": resource.region},
                )
                findings.append(finding)

        return findings

    def _is_imdsv1_enabled(self, config: Dict[str, Any]) -> bool:
        """Check if instance has IMDSv1 enabled.

        Args:
            config: Instance raw configuration

        Returns:
            True if IMDSv1 is enabled (HttpTokens is "optional")
        """
        metadata_options = config.get("MetadataOptions", {})
        http_tokens = metadata_options.get("HttpTokens", "optional")

        # "optional" means IMDSv1 is enabled (BAD)
        # "required" means IMDSv2 is required (GOOD)
        return http_tokens == "optional"
