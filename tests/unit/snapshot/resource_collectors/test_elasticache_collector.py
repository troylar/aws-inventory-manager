"""Unit tests for ElastiCache resource collector."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock

import pytest

from src.snapshot.resource_collectors.elasticache_collector import ElastiCacheCollector


class TestElastiCacheCollector:
    """Tests for ElastiCacheCollector."""

    def test_service_name(self) -> None:
        """Test that service name is elasticache."""
        session = MagicMock()
        collector = ElastiCacheCollector(session, "us-east-1")
        assert collector.service_name == "elasticache"

    def test_collect_redis_clusters(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test collecting Redis clusters."""
        session = MagicMock()
        collector = ElastiCacheCollector(session, "us-east-1")

        # Mock the boto3 client and paginator
        mock_client = Mock()
        mock_paginator = Mock()

        # Mock Redis cluster data
        redis_cluster = {
            "CacheClusterId": "redis-001",
            "ARN": "arn:aws:elasticache:us-east-1:123456789012:cluster:redis-001",
            "Engine": "redis",
            "CacheNodeType": "cache.t3.micro",
            "NumCacheNodes": 1,
            "EngineVersion": "7.0",
            "AtRestEncryptionEnabled": True,
            "TransitEncryptionEnabled": True,
            "CacheClusterStatus": "available",
        }

        mock_paginator.paginate.return_value = [{"CacheClusters": [redis_cluster]}]
        mock_client.get_paginator.return_value = mock_paginator

        # Mock list_tags_for_resource
        mock_client.list_tags_for_resource.return_value = {"TagList": [{"Key": "Environment", "Value": "test"}]}

        # Mock STS for account ID
        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}

        def mock_create_client(service_name: str = "elasticache") -> Mock:
            if service_name == "sts":
                return mock_sts
            return mock_client

        monkeypatch.setattr(collector, "_create_client", mock_create_client)

        # Collect resources
        resources = collector.collect()

        # Assertions
        assert len(resources) == 1
        assert resources[0].name == "redis-001"
        assert resources[0].resource_type == "elasticache:cluster"
        assert resources[0].region == "us-east-1"
        assert resources[0].tags == {"Environment": "test"}
        assert resources[0].raw_config is not None
        assert resources[0].raw_config["Engine"] == "redis"
        assert resources[0].raw_config["AtRestEncryptionEnabled"] is True

    def test_collect_memcached_clusters(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test collecting Memcached clusters."""
        session = MagicMock()
        collector = ElastiCacheCollector(session, "us-east-1")

        mock_client = Mock()
        mock_paginator = Mock()

        memcached_cluster = {
            "CacheClusterId": "memcached-001",
            "ARN": "arn:aws:elasticache:us-east-1:123456789012:cluster:memcached-001",
            "Engine": "memcached",
            "CacheNodeType": "cache.t3.micro",
            "NumCacheNodes": 2,
            "EngineVersion": "1.6.12",
            "AtRestEncryptionEnabled": False,
            "TransitEncryptionEnabled": False,
            "CacheClusterStatus": "available",
        }

        mock_paginator.paginate.return_value = [{"CacheClusters": [memcached_cluster]}]
        mock_client.get_paginator.return_value = mock_paginator
        mock_client.list_tags_for_resource.return_value = {"TagList": []}

        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}

        def mock_create_client(service_name: str = "elasticache") -> Mock:
            if service_name == "sts":
                return mock_sts
            return mock_client

        monkeypatch.setattr(collector, "_create_client", mock_create_client)

        resources = collector.collect()

        assert len(resources) == 1
        assert resources[0].name == "memcached-001"
        assert resources[0].raw_config["Engine"] == "memcached"
        assert resources[0].raw_config["NumCacheNodes"] == 2

    def test_collect_mixed_engines(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test collecting both Redis and Memcached clusters."""
        session = MagicMock()
        collector = ElastiCacheCollector(session, "us-east-1")

        mock_client = Mock()
        mock_paginator = Mock()

        redis_cluster = {
            "CacheClusterId": "redis-001",
            "ARN": "arn:aws:elasticache:us-east-1:123456789012:cluster:redis-001",
            "Engine": "redis",
            "CacheNodeType": "cache.t3.micro",
            "NumCacheNodes": 1,
            "EngineVersion": "7.0",
            "AtRestEncryptionEnabled": True,
            "TransitEncryptionEnabled": True,
            "CacheClusterStatus": "available",
        }

        memcached_cluster = {
            "CacheClusterId": "memcached-001",
            "ARN": "arn:aws:elasticache:us-east-1:123456789012:cluster:memcached-001",
            "Engine": "memcached",
            "CacheNodeType": "cache.t3.micro",
            "NumCacheNodes": 2,
            "EngineVersion": "1.6.12",
            "AtRestEncryptionEnabled": False,
            "TransitEncryptionEnabled": False,
            "CacheClusterStatus": "available",
        }

        mock_paginator.paginate.return_value = [{"CacheClusters": [redis_cluster, memcached_cluster]}]
        mock_client.get_paginator.return_value = mock_paginator
        mock_client.list_tags_for_resource.return_value = {"TagList": []}

        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}

        def mock_create_client(service_name: str = "elasticache") -> Mock:
            if service_name == "sts":
                return mock_sts
            return mock_client

        monkeypatch.setattr(collector, "_create_client", mock_create_client)

        resources = collector.collect()

        assert len(resources) == 2
        engines = [r.raw_config["Engine"] for r in resources]
        assert "redis" in engines
        assert "memcached" in engines

    def test_collect_with_pagination(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test collecting clusters with multiple pages."""
        session = MagicMock()
        collector = ElastiCacheCollector(session, "us-east-1")

        mock_client = Mock()
        mock_paginator = Mock()

        # First page
        page1_cluster = {
            "CacheClusterId": "cluster-001",
            "ARN": "arn:aws:elasticache:us-east-1:123456789012:cluster:cluster-001",
            "Engine": "redis",
            "CacheNodeType": "cache.t3.micro",
            "NumCacheNodes": 1,
            "EngineVersion": "7.0",
            "AtRestEncryptionEnabled": True,
            "TransitEncryptionEnabled": True,
            "CacheClusterStatus": "available",
        }

        # Second page
        page2_cluster = {
            "CacheClusterId": "cluster-002",
            "ARN": "arn:aws:elasticache:us-east-1:123456789012:cluster:cluster-002",
            "Engine": "redis",
            "CacheNodeType": "cache.t3.small",
            "NumCacheNodes": 1,
            "EngineVersion": "7.0",
            "AtRestEncryptionEnabled": False,
            "TransitEncryptionEnabled": False,
            "CacheClusterStatus": "available",
        }

        mock_paginator.paginate.return_value = [
            {"CacheClusters": [page1_cluster]},
            {"CacheClusters": [page2_cluster]},
        ]
        mock_client.get_paginator.return_value = mock_paginator
        mock_client.list_tags_for_resource.return_value = {"TagList": []}

        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}

        def mock_create_client(service_name: str = "elasticache") -> Mock:
            if service_name == "sts":
                return mock_sts
            return mock_client

        monkeypatch.setattr(collector, "_create_client", mock_create_client)

        resources = collector.collect()

        assert len(resources) == 2
        cluster_ids = [r.name for r in resources]
        assert "cluster-001" in cluster_ids
        assert "cluster-002" in cluster_ids

    def test_collect_empty_result(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test collecting when no clusters exist."""
        session = MagicMock()
        collector = ElastiCacheCollector(session, "us-east-1")

        mock_client = Mock()
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [{"CacheClusters": []}]
        mock_client.get_paginator.return_value = mock_paginator

        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}

        def mock_create_client(service_name: str = "elasticache") -> Mock:
            if service_name == "sts":
                return mock_sts
            return mock_client

        monkeypatch.setattr(collector, "_create_client", mock_create_client)

        resources = collector.collect()

        assert len(resources) == 0

    def test_collect_handles_tag_errors(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that tag fetching errors don't crash collection."""
        session = MagicMock()
        collector = ElastiCacheCollector(session, "us-east-1")

        mock_client = Mock()
        mock_paginator = Mock()

        cluster = {
            "CacheClusterId": "redis-001",
            "ARN": "arn:aws:elasticache:us-east-1:123456789012:cluster:redis-001",
            "Engine": "redis",
            "CacheNodeType": "cache.t3.micro",
            "NumCacheNodes": 1,
            "EngineVersion": "7.0",
            "AtRestEncryptionEnabled": True,
            "TransitEncryptionEnabled": True,
            "CacheClusterStatus": "available",
        }

        mock_paginator.paginate.return_value = [{"CacheClusters": [cluster]}]
        mock_client.get_paginator.return_value = mock_paginator
        # Simulate tag fetching error
        mock_client.list_tags_for_resource.side_effect = Exception("Access denied")

        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}

        def mock_create_client(service_name: str = "elasticache") -> Mock:
            if service_name == "sts":
                return mock_sts
            return mock_client

        monkeypatch.setattr(collector, "_create_client", mock_create_client)

        resources = collector.collect()

        # Should still collect the cluster, just without tags
        assert len(resources) == 1
        assert resources[0].tags == {}

    def test_collect_handles_api_errors(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test graceful error handling when API call fails."""
        session = MagicMock()
        collector = ElastiCacheCollector(session, "us-east-1")

        mock_client = Mock()
        mock_client.get_paginator.side_effect = Exception("API error")

        mock_sts = Mock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}

        def mock_create_client(service_name: str = "elasticache") -> Mock:
            if service_name == "sts":
                return mock_sts
            return mock_client

        monkeypatch.setattr(collector, "_create_client", mock_create_client)

        resources = collector.collect()

        # Should return empty list on error
        assert len(resources) == 0
