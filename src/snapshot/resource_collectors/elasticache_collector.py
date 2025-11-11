"""ElastiCache resource collector."""

from __future__ import annotations

from typing import List

from ...models.resource import Resource
from ...utils.hash import compute_config_hash
from .base import BaseResourceCollector


class ElastiCacheCollector(BaseResourceCollector):
    """Collector for AWS ElastiCache resources (Redis and Memcached clusters)."""

    @property
    def service_name(self) -> str:
        return "elasticache"

    def collect(self) -> List[Resource]:
        """Collect ElastiCache cluster resources.

        Collects both Redis and Memcached clusters using the ElastiCache API.

        Returns:
            List of ElastiCache cluster resources
        """
        resources = []
        account_id = self._get_account_id()

        # Collect cache clusters (both Redis and Memcached)
        resources.extend(self._collect_cache_clusters(account_id))

        self.logger.debug(f"Collected {len(resources)} ElastiCache clusters in {self.region}")
        return resources

    def _collect_cache_clusters(self, account_id: str) -> List[Resource]:
        """Collect ElastiCache cache clusters.

        Args:
            account_id: AWS account ID

        Returns:
            List of Resource objects representing ElastiCache clusters
        """
        resources = []
        client = self._create_client()

        try:
            paginator = client.get_paginator("describe_cache_clusters")
            # ShowCacheNodeInfo=False for performance (we don't need node-level details)
            for page in paginator.paginate(ShowCacheNodeInfo=False):
                for cluster in page.get("CacheClusters", []):
                    cluster_id = cluster["CacheClusterId"]
                    cluster_arn = cluster["ARN"]

                    # Extract tags
                    tags = {}
                    try:
                        tag_response = client.list_tags_for_resource(ResourceName=cluster_arn)
                        tags = {tag["Key"]: tag["Value"] for tag in tag_response.get("TagList", [])}
                    except Exception as e:
                        self.logger.debug(f"Could not get tags for ElastiCache cluster {cluster_id}: {e}")

                    # Create resource
                    resource = Resource(
                        arn=cluster_arn,
                        resource_type="elasticache:cluster",
                        name=cluster_id,
                        region=self.region,
                        tags=tags,
                        config_hash=compute_config_hash(cluster),
                        raw_config=cluster,
                    )
                    resources.append(resource)

        except Exception as e:
            self.logger.error(f"Error collecting ElastiCache clusters in {self.region}: {e}")

        return resources
