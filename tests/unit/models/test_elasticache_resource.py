"""Unit tests for ElastiCache resource model."""

from __future__ import annotations

import pytest

from src.models.elasticache_resource import ElastiCacheCluster


class TestElastiCacheCluster:
    """Tests for ElastiCacheCluster model."""

    def test_create_redis_cluster(self) -> None:
        """Test creating a Redis cluster resource."""
        cluster = ElastiCacheCluster(
            cluster_id="redis-001",
            arn="arn:aws:elasticache:us-east-1:123456789012:cluster:redis-001",
            engine="redis",
            node_type="cache.t3.micro",
            num_cache_nodes=1,
            engine_version="7.0",
            encryption_at_rest=True,
            encryption_in_transit=True,
            tags={"Environment": "test"},
            region="us-east-1",
        )

        assert cluster.cluster_id == "redis-001"
        assert cluster.engine == "redis"
        assert cluster.encryption_at_rest is True
        assert cluster.encryption_in_transit is True

    def test_create_memcached_cluster(self) -> None:
        """Test creating a Memcached cluster resource."""
        cluster = ElastiCacheCluster(
            cluster_id="memcached-001",
            arn="arn:aws:elasticache:us-east-1:123456789012:cluster:memcached-001",
            engine="memcached",
            node_type="cache.t3.micro",
            num_cache_nodes=2,
            engine_version="1.6.12",
            encryption_at_rest=False,  # Memcached doesn't support at-rest encryption
            encryption_in_transit=True,
            tags={},
            region="us-east-1",
        )

        assert cluster.cluster_id == "memcached-001"
        assert cluster.engine == "memcached"
        assert cluster.encryption_at_rest is False
        assert cluster.num_cache_nodes == 2

    def test_cluster_id_max_length_validation(self) -> None:
        """Test that cluster_id validates max length (50 chars per AWS)."""
        long_id = "a" * 51  # 51 characters, exceeds max

        with pytest.raises(ValueError, match="cluster_id must be 50 characters or less"):
            ElastiCacheCluster(
                cluster_id=long_id,
                arn="arn:aws:elasticache:us-east-1:123456789012:cluster:test",
                engine="redis",
                node_type="cache.t3.micro",
                num_cache_nodes=1,
                engine_version="7.0",
                encryption_at_rest=True,
                encryption_in_transit=True,
                tags={},
                region="us-east-1",
            )

    def test_engine_validation(self) -> None:
        """Test that engine must be redis or memcached."""
        with pytest.raises(ValueError, match="engine must be 'redis' or 'memcached'"):
            ElastiCacheCluster(
                cluster_id="test-cluster",
                arn="arn:aws:elasticache:us-east-1:123456789012:cluster:test",
                engine="dynamodb",  # Invalid engine
                node_type="cache.t3.micro",
                num_cache_nodes=1,
                engine_version="1.0",
                encryption_at_rest=True,
                encryption_in_transit=True,
                tags={},
                region="us-east-1",
            )

    def test_memcached_at_rest_encryption_validation(self) -> None:
        """Test that memcached clusters cannot have at-rest encryption."""
        with pytest.raises(ValueError, match="Memcached does not support encryption at rest"):
            ElastiCacheCluster(
                cluster_id="memcached-bad",
                arn="arn:aws:elasticache:us-east-1:123456789012:cluster:memcached-bad",
                engine="memcached",
                node_type="cache.t3.micro",
                num_cache_nodes=1,
                engine_version="1.6.12",
                encryption_at_rest=True,  # Invalid for memcached
                encryption_in_transit=False,
                tags={},
                region="us-east-1",
            )

    def test_num_cache_nodes_validation(self) -> None:
        """Test that num_cache_nodes must be >= 1."""
        with pytest.raises(ValueError, match="num_cache_nodes must be at least 1"):
            ElastiCacheCluster(
                cluster_id="test-cluster",
                arn="arn:aws:elasticache:us-east-1:123456789012:cluster:test",
                engine="redis",
                node_type="cache.t3.micro",
                num_cache_nodes=0,  # Invalid count
                engine_version="7.0",
                encryption_at_rest=True,
                encryption_in_transit=True,
                tags={},
                region="us-east-1",
            )

    def test_to_resource_dict_redis(self) -> None:
        """Test conversion to Resource dict for Redis cluster."""
        cluster = ElastiCacheCluster(
            cluster_id="redis-001",
            arn="arn:aws:elasticache:us-east-1:123456789012:cluster:redis-001",
            engine="redis",
            node_type="cache.t3.micro",
            num_cache_nodes=1,
            engine_version="7.0",
            encryption_at_rest=True,
            encryption_in_transit=True,
            tags={"Environment": "prod"},
            region="us-east-1",
        )

        resource_dict = cluster.to_resource_dict()

        assert resource_dict["arn"] == cluster.arn
        assert resource_dict["resource_type"] == "elasticache:cluster"
        assert resource_dict["name"] == cluster.cluster_id
        assert resource_dict["region"] == cluster.region
        assert resource_dict["tags"] == cluster.tags
        assert "raw_config" in resource_dict
        assert resource_dict["raw_config"]["CacheClusterId"] == cluster.cluster_id
        assert resource_dict["raw_config"]["Engine"] == "redis"
        assert resource_dict["raw_config"]["AtRestEncryptionEnabled"] is True
        assert resource_dict["raw_config"]["TransitEncryptionEnabled"] is True

    def test_to_resource_dict_memcached(self) -> None:
        """Test conversion to Resource dict for Memcached cluster."""
        cluster = ElastiCacheCluster(
            cluster_id="memcached-001",
            arn="arn:aws:elasticache:us-east-1:123456789012:cluster:memcached-001",
            engine="memcached",
            node_type="cache.t3.micro",
            num_cache_nodes=3,
            engine_version="1.6.12",
            encryption_at_rest=False,
            encryption_in_transit=False,
            tags={},
            region="us-east-1",
        )

        resource_dict = cluster.to_resource_dict()

        assert resource_dict["resource_type"] == "elasticache:cluster"
        assert resource_dict["raw_config"]["Engine"] == "memcached"
        assert resource_dict["raw_config"]["NumCacheNodes"] == 3
        assert resource_dict["raw_config"]["AtRestEncryptionEnabled"] is False

    def test_to_resource_dict_includes_config_hash(self) -> None:
        """Test that to_resource_dict includes a valid config_hash."""
        cluster = ElastiCacheCluster(
            cluster_id="test-cluster",
            arn="arn:aws:elasticache:us-east-1:123456789012:cluster:test",
            engine="redis",
            node_type="cache.t3.micro",
            num_cache_nodes=1,
            engine_version="7.0",
            encryption_at_rest=True,
            encryption_in_transit=True,
            tags={},
            region="us-east-1",
        )

        resource_dict = cluster.to_resource_dict()

        assert "config_hash" in resource_dict
        # Should be 64-character hex string (SHA256)
        assert len(resource_dict["config_hash"]) == 64
        assert all(c in "0123456789abcdef" for c in resource_dict["config_hash"])

    def test_empty_tags(self) -> None:
        """Test cluster with empty tags."""
        cluster = ElastiCacheCluster(
            cluster_id="no-tags",
            arn="arn:aws:elasticache:us-east-1:123456789012:cluster:no-tags",
            engine="redis",
            node_type="cache.t3.micro",
            num_cache_nodes=1,
            engine_version="7.0",
            encryption_at_rest=False,
            encryption_in_transit=False,
            tags={},
            region="us-east-1",
        )

        assert cluster.tags == {}
        resource_dict = cluster.to_resource_dict()
        assert resource_dict["tags"] == {}
