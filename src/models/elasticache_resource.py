"""ElastiCache resource model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from ..utils.hash import compute_config_hash


@dataclass
class ElastiCacheCluster:
    """Represents an AWS ElastiCache cluster (Redis or Memcached).

    This model captures both Redis and Memcached clusters with their
    encryption settings, node configuration, and metadata.

    Attributes:
        cluster_id: Unique identifier for the cluster (max 50 chars)
        arn: Amazon Resource Name for the cluster
        engine: Cache engine type (redis or memcached)
        node_type: Cache node type (e.g., cache.t3.micro)
        num_cache_nodes: Number of cache nodes in the cluster
        engine_version: Engine version string
        encryption_at_rest: Whether data at rest is encrypted
        encryption_in_transit: Whether data in transit is encrypted
        tags: Resource tags as key-value pairs
        region: AWS region
    """

    cluster_id: str
    arn: str
    engine: str
    node_type: str
    num_cache_nodes: int
    engine_version: str
    encryption_at_rest: bool
    encryption_in_transit: bool
    tags: Dict[str, str] = field(default_factory=dict)
    region: str = "us-east-1"

    def __post_init__(self) -> None:
        """Validate ElastiCache cluster data after initialization."""
        # Validate cluster_id length (AWS limit is 50 characters)
        if len(self.cluster_id) > 50:
            raise ValueError("cluster_id must be 50 characters or less")

        # Validate engine type
        if self.engine not in ("redis", "memcached"):
            raise ValueError("engine must be 'redis' or 'memcached'")

        # Memcached does not support encryption at rest
        if self.engine == "memcached" and self.encryption_at_rest:
            raise ValueError("Memcached does not support encryption at rest")

        # Validate num_cache_nodes
        if self.num_cache_nodes < 1:
            raise ValueError("num_cache_nodes must be at least 1")

    def to_resource_dict(self) -> Dict[str, Any]:
        """Convert ElastiCache cluster to Resource dictionary.

        Returns:
            Dictionary with Resource fields suitable for creating a Resource object
        """
        # Build raw_config that matches ElastiCache API response structure
        raw_config = {
            "CacheClusterId": self.cluster_id,
            "ARN": self.arn,
            "Engine": self.engine,
            "CacheNodeType": self.node_type,
            "NumCacheNodes": self.num_cache_nodes,
            "EngineVersion": self.engine_version,
            "AtRestEncryptionEnabled": self.encryption_at_rest,
            "TransitEncryptionEnabled": self.encryption_in_transit,
            "CacheClusterStatus": "available",
        }

        # Compute config hash from raw_config
        config_hash = compute_config_hash(raw_config)

        return {
            "arn": self.arn,
            "resource_type": "elasticache:cluster",
            "name": self.cluster_id,
            "region": self.region,
            "tags": self.tags,
            "config_hash": config_hash,
            "raw_config": raw_config,
        }
