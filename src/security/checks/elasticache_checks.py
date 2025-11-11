"""ElastiCache security checks."""

from __future__ import annotations

from typing import Any, Dict, List

from ...models.security_finding import SecurityFinding, Severity
from ...models.snapshot import Snapshot
from .base import SecurityCheck


class ElastiCacheEncryptionCheck(SecurityCheck):
    """Check for ElastiCache clusters with encryption issues.

    Checks for:
    - Redis clusters without encryption at rest (AtRestEncryptionEnabled=False)
    - Redis/Memcached clusters without encryption in transit (TransitEncryptionEnabled=False)

    Note: Memcached does not support encryption at rest, so only in-transit
    encryption is checked for Memcached clusters.

    Severity: MEDIUM
    """

    @property
    def check_id(self) -> str:
        """Return check identifier."""
        return "elasticache_unencrypted"

    @property
    def severity(self) -> Severity:
        """Return check severity."""
        return Severity.MEDIUM

    def execute(self, snapshot: Snapshot) -> List[SecurityFinding]:
        """Execute ElastiCache encryption checks.

        Checks for:
        - Redis: AtRestEncryptionEnabled=False or TransitEncryptionEnabled=False
        - Memcached: TransitEncryptionEnabled=False only (doesn't support at-rest)

        Args:
            snapshot: Snapshot to scan

        Returns:
            List of findings for ElastiCache encryption issues
        """
        findings: List[SecurityFinding] = []

        for resource in snapshot.resources:
            # Only check ElastiCache resources
            if not resource.resource_type.startswith("elasticache:"):
                continue

            if resource.raw_config is None:
                continue

            engine = resource.raw_config.get("Engine", "").lower()

            # Check encryption at rest (Redis only)
            if engine == "redis" and not self._is_encrypted_at_rest(resource.raw_config):
                finding = self._create_at_rest_finding(resource.name, resource.arn, resource.region, engine)
                findings.append(finding)

            # Check encryption in transit (both Redis and Memcached)
            if not self._is_encrypted_in_transit(resource.raw_config):
                finding = self._create_in_transit_finding(resource.name, resource.arn, resource.region, engine)
                findings.append(finding)

        return findings

    def _is_encrypted_at_rest(self, config: Dict[str, Any]) -> bool:
        """Check if cluster has encryption at rest enabled.

        Args:
            config: ElastiCache cluster raw configuration

        Returns:
            True if AtRestEncryptionEnabled is True
        """
        return config.get("AtRestEncryptionEnabled", False)

    def _is_encrypted_in_transit(self, config: Dict[str, Any]) -> bool:
        """Check if cluster has encryption in transit enabled.

        Args:
            config: ElastiCache cluster raw configuration

        Returns:
            True if TransitEncryptionEnabled is True
        """
        return config.get("TransitEncryptionEnabled", False)

    def _create_at_rest_finding(self, cluster_id: str, arn: str, region: str, engine: str) -> SecurityFinding:
        """Create a finding for cluster without encryption at rest.

        Args:
            cluster_id: Cluster identifier
            arn: Resource ARN
            region: AWS region
            engine: Engine type (redis/memcached)

        Returns:
            SecurityFinding for at-rest encryption issue
        """
        return SecurityFinding(
            resource_arn=arn,
            finding_type=self.check_id,
            severity=self.severity,
            description=f"ElastiCache {engine} cluster '{cluster_id}' does not have encryption at rest enabled. "
            f"Data stored on disk is not encrypted, which could expose sensitive cached data "
            f"if storage media is compromised.",
            remediation="Enable encryption at rest for this ElastiCache cluster. "
            "Note: Encryption at rest cannot be enabled on existing clusters. "
            "You must create a new cluster with encryption enabled and migrate your data. "
            "Create a backup of your existing cluster, then restore it to a new cluster with "
            "AtRestEncryptionEnabled=true. For Redis clusters, ensure you specify a KMS key. "
            "After verification, update your applications to point to the new encrypted cluster.",
            metadata={"cluster_id": cluster_id, "region": region, "engine": engine},
        )

    def _create_in_transit_finding(self, cluster_id: str, arn: str, region: str, engine: str) -> SecurityFinding:
        """Create a finding for cluster without encryption in transit.

        Args:
            cluster_id: Cluster identifier
            arn: Resource ARN
            region: AWS region
            engine: Engine type (redis/memcached)

        Returns:
            SecurityFinding for in-transit encryption issue
        """
        return SecurityFinding(
            resource_arn=arn,
            finding_type=self.check_id,
            severity=self.severity,
            description=f"ElastiCache {engine} cluster '{cluster_id}' does not have encryption in transit enabled. "
            f"Data transmitted between the cache and clients is not encrypted, which could expose "
            f"sensitive cached data during transmission.",
            remediation="Enable encryption in transit for this ElastiCache cluster. "
            "Note: Encryption in transit cannot be enabled on existing clusters. "
            "You must create a new cluster with encryption enabled. "
            f"For {engine}, create a new cluster with TransitEncryptionEnabled=true. "
            "After creating the encrypted cluster, update your application connection strings "
            "to use TLS/SSL connections and point to the new cluster endpoint. "
            "Verify the encrypted connection is working before decommissioning the old cluster.",
            metadata={"cluster_id": cluster_id, "region": region, "engine": engine},
        )
