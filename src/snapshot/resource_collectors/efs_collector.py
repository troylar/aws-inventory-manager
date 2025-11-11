"""EFS resource collector."""

from __future__ import annotations

from typing import List

from botocore.exceptions import ClientError

from ...models.efs_resource import EFSFileSystem
from ...models.resource import Resource
from .base import BaseResourceCollector


class EFSCollector(BaseResourceCollector):
    """Collector for AWS EFS (Elastic File System) resources."""

    @property
    def service_name(self) -> str:
        return "efs"

    @property
    def is_global_service(self) -> bool:
        return False

    def collect(self) -> List[Resource]:
        """Collect EFS file systems.

        Returns:
            List of EFS file system resources
        """
        resources = []

        try:
            client = self._create_client()

            # Use paginator for describe_file_systems
            paginator = client.get_paginator("describe_file_systems")

            for page in paginator.paginate():
                for fs in page.get("FileSystems", []):
                    try:
                        # Extract basic file system information
                        file_system_id = fs["FileSystemId"]
                        arn = fs["FileSystemArn"]
                        created_at = fs.get("CreationTime")
                        lifecycle_state = fs.get("LifeCycleState", "unknown")
                        performance_mode = fs.get("PerformanceMode", "generalPurpose")
                        encrypted = fs.get("Encrypted", False)
                        kms_key_id = fs.get("KmsKeyId")

                        # Extract tags
                        tags = {}
                        for tag in fs.get("Tags", []):
                            tags[tag["Key"]] = tag["Value"]

                        # Create EFSFileSystem model
                        efs_fs = EFSFileSystem(
                            file_system_id=file_system_id,
                            arn=arn,
                            encryption_enabled=encrypted,
                            kms_key_id=kms_key_id,
                            performance_mode=performance_mode,
                            lifecycle_state=lifecycle_state,
                            tags=tags,
                            region=self.region,
                            created_at=created_at,
                        )

                        # Convert to Resource
                        resource_dict = efs_fs.to_resource_dict()
                        resource = Resource(
                            arn=resource_dict["arn"],
                            resource_type=resource_dict["resource_type"],
                            name=resource_dict["name"],
                            region=resource_dict["region"],
                            tags=resource_dict["tags"],
                            config_hash=resource_dict["config_hash"],
                            created_at=resource_dict["created_at"],
                            raw_config=resource_dict["raw_config"],
                        )

                        resources.append(resource)

                    except Exception as e:
                        self.logger.debug(f"Error processing EFS file system {fs.get('FileSystemId', 'unknown')}: {e}")
                        continue

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            # Handle regions where EFS is not available or access denied
            if error_code in ["OptInRequired", "AccessDenied", "InvalidAction"]:
                self.logger.debug(f"EFS not available or access denied in {self.region}: {error_code}")
            else:
                self.logger.error(f"Error collecting EFS file systems in {self.region}: {e}")
            return []

        except Exception as e:
            self.logger.error(f"Error collecting EFS file systems in {self.region}: {e}")
            return []

        self.logger.debug(f"Collected {len(resources)} EFS file systems in {self.region}")
        return resources
