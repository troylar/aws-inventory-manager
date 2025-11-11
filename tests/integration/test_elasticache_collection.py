"""Integration tests for ElastiCache resource collection."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import pytest

from src.security.scanner import SecurityScanner
from src.snapshot.capturer import create_snapshot


@pytest.fixture
def mock_elasticache_clusters() -> list[dict]:
    """Create mock ElastiCache cluster responses."""
    return [
        {
            "CacheClusterId": "redis-integration",
            "ARN": "arn:aws:elasticache:us-east-1:123456789012:cluster:redis-integration",
            "Engine": "redis",
            "CacheNodeType": "cache.t3.micro",
            "NumCacheNodes": 1,
            "EngineVersion": "7.0",
            "AtRestEncryptionEnabled": True,
            "TransitEncryptionEnabled": True,
            "CacheClusterStatus": "available",
        },
        {
            "CacheClusterId": "memcached-integration",
            "ARN": "arn:aws:elasticache:us-east-1:123456789012:cluster:memcached-integration",
            "Engine": "memcached",
            "CacheNodeType": "cache.t3.micro",
            "NumCacheNodes": 2,
            "EngineVersion": "1.6.12",
            "AtRestEncryptionEnabled": False,
            "TransitEncryptionEnabled": False,
            "CacheClusterStatus": "available",
        },
    ]


@pytest.fixture
def mock_boto_clients_for_elasticache(mock_elasticache_clusters: list[dict]) -> None:
    """Mock boto3 clients to return ElastiCache clusters."""

    def mock_create_client(service_name: str, region_name: str = "us-east-1", profile_name: str = None):  # type: ignore
        """Mock client factory."""
        if service_name == "elasticache":
            client = MagicMock()
            paginator = MagicMock()
            paginator.paginate.return_value = [{"CacheClusters": mock_elasticache_clusters}]
            client.get_paginator.return_value = paginator
            client.list_tags_for_resource.return_value = {"TagList": [{"Key": "Environment", "Value": "integration"}]}
            return client
        elif service_name == "sts":
            client = MagicMock()
            client.get_caller_identity.return_value = {"Account": "123456789012"}
            return client
        else:
            # Return mock for other services
            client = MagicMock()
            client.get_paginator.side_effect = Exception("Service not mocked")
            return client

    return mock_create_client


class TestElastiCacheCollectionIntegration:
    """Integration tests for ElastiCache collection and security scanning."""

    @patch("src.aws.client.create_boto_client")
    @patch("src.snapshot.capturer.boto3.Session")
    def test_snapshot_captures_elasticache_clusters(
        self,
        mock_session: Mock,
        mock_create_boto_client: Mock,
        mock_boto_clients_for_elasticache,  # type: ignore
        mock_elasticache_clusters: list[dict],
    ) -> None:
        """Test that snapshot creation captures ElastiCache clusters."""
        # Setup mocks
        mock_create_boto_client.side_effect = mock_boto_clients_for_elasticache
        session_instance = MagicMock()
        session_instance.profile_name = "test-profile"
        mock_session.return_value = session_instance

        # Create snapshot with ElastiCache collection
        snapshot = create_snapshot(
            name="test-elasticache-snapshot",
            regions=["us-east-1"],
            account_id="123456789012",
            profile_name="test-profile",
            set_active=False,
            resource_types=["elasticache"],  # Only collect ElastiCache
        )

        # Verify ElastiCache resources were collected
        elasticache_resources = [r for r in snapshot.resources if r.resource_type == "elasticache:cluster"]
        assert len(elasticache_resources) == 2

        # Verify Redis cluster
        redis_resources = [r for r in elasticache_resources if r.raw_config["Engine"] == "redis"]
        assert len(redis_resources) == 1
        assert redis_resources[0].name == "redis-integration"
        assert redis_resources[0].raw_config["AtRestEncryptionEnabled"] is True
        assert redis_resources[0].raw_config["TransitEncryptionEnabled"] is True

        # Verify Memcached cluster
        memcached_resources = [r for r in elasticache_resources if r.raw_config["Engine"] == "memcached"]
        assert len(memcached_resources) == 1
        assert memcached_resources[0].name == "memcached-integration"
        assert memcached_resources[0].raw_config["NumCacheNodes"] == 2

    @patch("src.aws.client.create_boto_client")
    @patch("src.snapshot.capturer.boto3.Session")
    def test_elasticache_in_snapshot_report(
        self,
        mock_session: Mock,
        mock_create_boto_client: Mock,
        mock_boto_clients_for_elasticache,  # type: ignore
        mock_elasticache_clusters: list[dict],
    ) -> None:
        """Test that ElastiCache appears in snapshot report."""
        # Setup mocks
        mock_create_boto_client.side_effect = mock_boto_clients_for_elasticache
        session_instance = MagicMock()
        session_instance.profile_name = "test-profile"
        mock_session.return_value = session_instance

        snapshot = create_snapshot(
            name="report-test",
            regions=["us-east-1"],
            account_id="123456789012",
            profile_name="test-profile",
            set_active=False,
            resource_types=["elasticache"],
        )

        # Verify we can filter by resource type
        elasticache_resources = [r for r in snapshot.resources if r.resource_type.startswith("elasticache")]
        assert len(elasticache_resources) == 2

        # Verify the service name extraction works
        assert elasticache_resources[0].service == "elasticache"

    @patch("src.aws.client.create_boto_client")
    @patch("src.snapshot.capturer.boto3.Session")
    def test_security_scan_detects_unencrypted_elasticache(
        self,
        mock_session: Mock,
        mock_create_boto_client: Mock,
    ) -> None:
        """Test that security scanner detects unencrypted ElastiCache clusters."""

        def mock_create_client_unencrypted(service_name: str, region_name: str = "us-east-1", profile_name: str = None):  # type: ignore
            """Mock client factory with unencrypted cluster."""
            if service_name == "elasticache":
                client = MagicMock()
                paginator = MagicMock()
                unencrypted_cluster = {
                    "CacheClusterId": "unencrypted-redis",
                    "ARN": "arn:aws:elasticache:us-east-1:123456789012:cluster:unencrypted-redis",
                    "Engine": "redis",
                    "CacheNodeType": "cache.t3.micro",
                    "NumCacheNodes": 1,
                    "EngineVersion": "7.0",
                    "AtRestEncryptionEnabled": False,  # Not encrypted at rest
                    "TransitEncryptionEnabled": False,  # Not encrypted in transit
                    "CacheClusterStatus": "available",
                }
                paginator.paginate.return_value = [{"CacheClusters": [unencrypted_cluster]}]
                client.get_paginator.return_value = paginator
                client.list_tags_for_resource.return_value = {"TagList": []}
                return client
            elif service_name == "sts":
                client = MagicMock()
                client.get_caller_identity.return_value = {"Account": "123456789012"}
                return client
            else:
                client = MagicMock()
                client.get_paginator.side_effect = Exception("Service not mocked")
                return client

        # Setup mocks
        mock_create_boto_client.side_effect = mock_create_client_unencrypted
        session_instance = MagicMock()
        session_instance.profile_name = "test-profile"
        mock_session.return_value = session_instance

        # Create snapshot
        snapshot = create_snapshot(
            name="security-test",
            regions=["us-east-1"],
            account_id="123456789012",
            profile_name="test-profile",
            set_active=False,
            resource_types=["elasticache"],
        )

        # Run security scanner
        scanner = SecurityScanner()
        scan_results = scanner.scan(snapshot)

        # Verify security findings for unencrypted ElastiCache
        elasticache_findings = [f for f in scan_results.findings if "elasticache" in f.finding_type.lower()]

        assert len(elasticache_findings) > 0
        # Should flag both at-rest and in-transit encryption issues
        assert any("encryption" in f.description.lower() for f in elasticache_findings)
        assert any("unencrypted-redis" in f.resource_arn for f in elasticache_findings)
