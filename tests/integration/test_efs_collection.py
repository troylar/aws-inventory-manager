"""Integration tests for EFS collection."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.snapshot.capturer import create_snapshot
from src.snapshot.storage import SnapshotStorage


@pytest.fixture
def mock_efs_file_systems() -> list[dict]:
    """Create mock EFS file system responses."""
    return [
        {
            "FileSystemId": "fs-test-001",
            "FileSystemArn": "arn:aws:elasticfilesystem:us-east-1:123456789012:file-system/fs-test-001",
            "CreationTime": datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            "LifeCycleState": "available",
            "PerformanceMode": "generalPurpose",
            "Encrypted": True,
            "KmsKeyId": "arn:aws:kms:us-east-1:123456789012:key/abcd1234",
            "Tags": [
                {"Key": "Environment", "Value": "prod"},
                {"Key": "Owner", "Value": "team-a"},
            ],
        },
        {
            "FileSystemId": "fs-test-002",
            "FileSystemArn": "arn:aws:elasticfilesystem:us-east-1:123456789012:file-system/fs-test-002",
            "CreationTime": datetime(2024, 2, 10, 14, 30, 0, tzinfo=timezone.utc),
            "LifeCycleState": "available",
            "PerformanceMode": "maxIO",
            "Encrypted": False,
            "Tags": [{"Key": "Environment", "Value": "dev"}],
        },
    ]


@pytest.fixture
def mock_boto_clients_for_efs(mock_efs_file_systems: list[dict]) -> None:
    """Mock boto3 clients to return EFS file systems."""

    def mock_create_client(service_name: str, region_name: str = "us-east-1", profile_name: str = None):  # type: ignore
        """Mock client factory."""
        if service_name == "efs":
            client = MagicMock()
            paginator = MagicMock()
            paginator.paginate.return_value = [{"FileSystems": mock_efs_file_systems}]
            client.get_paginator.return_value = paginator
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


class TestEFSIntegration:
    """Integration tests for EFS collection."""

    @patch("src.aws.client.create_boto_client")
    @patch("src.snapshot.capturer.boto3.Session")
    def test_snapshot_create_captures_efs(
        self,
        mock_session: Mock,
        mock_create_boto_client: Mock,
        mock_boto_clients_for_efs,  # type: ignore
        mock_efs_file_systems: list[dict],
    ) -> None:
        """Test that snapshot creation captures EFS file systems."""
        # Setup mocks
        mock_create_boto_client.side_effect = mock_boto_clients_for_efs
        session_instance = MagicMock()
        session_instance.profile_name = "test-profile"
        mock_session.return_value = session_instance

        # Create snapshot with EFS collection
        snapshot = create_snapshot(
            name="test-efs-snapshot",
            regions=["us-east-1"],
            account_id="123456789012",
            profile_name="test-profile",
            set_active=False,
            resource_types=["efs"],  # Only collect EFS
        )

        # Verify EFS resources were collected
        efs_resources = [r for r in snapshot.resources if r.resource_type == "efs:file-system"]
        assert len(efs_resources) == 2

        # Verify first EFS file system
        fs1 = next((r for r in efs_resources if r.name == "fs-test-001"), None)
        assert fs1 is not None
        assert fs1.arn == "arn:aws:elasticfilesystem:us-east-1:123456789012:file-system/fs-test-001"
        assert fs1.tags == {"Environment": "prod", "Owner": "team-a"}
        assert fs1.raw_config is not None
        assert fs1.raw_config["encryption_enabled"] is True
        assert fs1.raw_config["performance_mode"] == "generalPurpose"

        # Verify second EFS file system
        fs2 = next((r for r in efs_resources if r.name == "fs-test-002"), None)
        assert fs2 is not None
        assert fs2.raw_config["encryption_enabled"] is False
        assert fs2.raw_config["performance_mode"] == "maxIO"

    @patch("src.aws.client.create_boto_client")
    @patch("src.snapshot.capturer.boto3.Session")
    def test_efs_in_snapshot_report(
        self,
        mock_session: Mock,
        mock_create_boto_client: Mock,
        mock_boto_clients_for_efs,  # type: ignore
    ) -> None:
        """Test that EFS appears in snapshot report with correct counts."""
        mock_create_boto_client.side_effect = mock_boto_clients_for_efs
        session_instance = MagicMock()
        session_instance.profile_name = "test-profile"
        mock_session.return_value = session_instance

        snapshot = create_snapshot(
            name="test-efs-report",
            regions=["us-east-1"],
            account_id="123456789012",
            profile_name="test-profile",
            set_active=False,
            resource_types=["efs"],
        )

        # Check service counts
        efs_count = snapshot.service_counts.get("efs:file-system", 0)
        assert efs_count == 2

    @patch("src.aws.client.create_boto_client")
    @patch("src.snapshot.capturer.boto3.Session")
    def test_efs_with_tag_filtering(
        self,
        mock_session: Mock,
        mock_create_boto_client: Mock,
        mock_boto_clients_for_efs,  # type: ignore
    ) -> None:
        """Test that EFS file systems can be filtered by tags."""
        from src.snapshot.filter import ResourceFilter

        mock_create_boto_client.side_effect = mock_boto_clients_for_efs
        session_instance = MagicMock()
        session_instance.profile_name = "test-profile"
        mock_session.return_value = session_instance

        # Create filter for prod environment
        resource_filter = ResourceFilter(required_tags={"Environment": "prod"})

        snapshot = create_snapshot(
            name="test-efs-filtered",
            regions=["us-east-1"],
            account_id="123456789012",
            profile_name="test-profile",
            set_active=False,
            resource_types=["efs"],
            resource_filter=resource_filter,
        )

        # Should only have 1 EFS (the prod one)
        efs_resources = [r for r in snapshot.resources if r.resource_type == "efs:file-system"]
        assert len(efs_resources) == 1
        assert efs_resources[0].tags["Environment"] == "prod"

    @patch("src.aws.client.create_boto_client")
    @patch("src.snapshot.capturer.boto3.Session")
    def test_delta_tracking_with_new_efs(
        self,
        mock_session: Mock,
        mock_create_boto_client: Mock,
        tmp_path: Path,
    ) -> None:
        """Test that delta tracking identifies new EFS file systems."""
        from src.delta.calculator import DeltaCalculator

        # Mock for baseline snapshot (no EFS)
        def mock_client_no_efs(service_name: str, region_name: str = "us-east-1", profile_name: str = None):  # type: ignore
            if service_name == "efs":
                client = MagicMock()
                paginator = MagicMock()
                paginator.paginate.return_value = [{"FileSystems": []}]
                client.get_paginator.return_value = paginator
                return client
            elif service_name == "sts":
                client = MagicMock()
                client.get_caller_identity.return_value = {"Account": "123456789012"}
                return client
            else:
                client = MagicMock()
                client.get_paginator.side_effect = Exception("Service not mocked")
                return client

        # Mock for new snapshot (with EFS)
        def mock_client_with_efs(service_name: str, region_name: str = "us-east-1", profile_name: str = None):  # type: ignore
            if service_name == "efs":
                client = MagicMock()
                paginator = MagicMock()
                paginator.paginate.return_value = [
                    {
                        "FileSystems": [
                            {
                                "FileSystemId": "fs-new-001",
                                "FileSystemArn": (
                                    "arn:aws:elasticfilesystem:us-east-1:123456789012:file-system/fs-new-001"
                                ),
                                "CreationTime": datetime.now(timezone.utc),
                                "LifeCycleState": "available",
                                "PerformanceMode": "generalPurpose",
                                "Encrypted": True,
                                "Tags": [],
                            }
                        ]
                    }
                ]
                client.get_paginator.return_value = paginator
                return client
            elif service_name == "sts":
                client = MagicMock()
                client.get_caller_identity.return_value = {"Account": "123456789012"}
                return client
            else:
                client = MagicMock()
                client.get_paginator.side_effect = Exception("Service not mocked")
                return client

        session_instance = MagicMock()
        session_instance.profile_name = "test-profile"
        mock_session.return_value = session_instance

        # Create baseline snapshot (no EFS)
        mock_create_boto_client.side_effect = mock_client_no_efs
        baseline = create_snapshot(
            name="baseline",
            regions=["us-east-1"],
            account_id="123456789012",
            profile_name="test-profile",
            set_active=True,
            resource_types=["efs"],
        )

        # Save baseline
        storage = SnapshotStorage(tmp_path)
        storage.save_snapshot(baseline)

        # Create new snapshot (with EFS)
        mock_create_boto_client.side_effect = mock_client_with_efs
        current = create_snapshot(
            name="current",
            regions=["us-east-1"],
            account_id="123456789012",
            profile_name="test-profile",
            set_active=False,
            resource_types=["efs"],
        )

        # Calculate delta
        calculator = DeltaCalculator(baseline, current)
        delta = calculator.calculate()

        # Verify new EFS file system detected
        added_efs = [r for r in delta.added_resources if r.resource_type == "efs:file-system"]
        assert len(added_efs) == 1
        assert added_efs[0].name == "fs-new-001"

    @patch("src.aws.client.create_boto_client")
    @patch("src.snapshot.capturer.boto3.Session")
    def test_snapshot_report_filtering_by_efs_type(
        self,
        mock_session: Mock,
        mock_create_boto_client: Mock,
        mock_boto_clients_for_efs,  # type: ignore
    ) -> None:
        """Test filtering snapshot report by EFS resource type."""
        from src.models.report import FilterCriteria
        from src.snapshot.reporter import SnapshotReporter

        mock_create_boto_client.side_effect = mock_boto_clients_for_efs
        session_instance = MagicMock()
        session_instance.profile_name = "test-profile"
        mock_session.return_value = session_instance

        snapshot = create_snapshot(
            name="test-efs-filter",
            regions=["us-east-1"],
            account_id="123456789012",
            profile_name="test-profile",
            set_active=False,
            resource_types=["efs"],
        )

        # Create reporter and filter by EFS type
        reporter = SnapshotReporter(snapshot)
        criteria = FilterCriteria(resource_types=["efs:file-system"])
        filtered_resources = list(reporter.get_filtered_resources(criteria))

        # Should only return EFS resources
        assert len(filtered_resources) == 2
        assert all(r.resource_type == "efs:file-system" for r in filtered_resources)

    @patch("src.aws.client.create_boto_client")
    @patch("src.snapshot.capturer.boto3.Session")
    def test_efs_collection_persists_to_yaml(
        self,
        mock_session: Mock,
        mock_create_boto_client: Mock,
        mock_boto_clients_for_efs,  # type: ignore
        tmp_path: Path,
    ) -> None:
        """Test that EFS resources are properly saved and loaded from YAML."""
        mock_create_boto_client.side_effect = mock_boto_clients_for_efs
        session_instance = MagicMock()
        session_instance.profile_name = "test-profile"
        mock_session.return_value = session_instance

        # Create snapshot with EFS
        snapshot = create_snapshot(
            name="test-efs-persist",
            regions=["us-east-1"],
            account_id="123456789012",
            profile_name="test-profile",
            set_active=False,
            resource_types=["efs"],
        )

        # Save to YAML
        storage = SnapshotStorage(tmp_path)
        storage.save_snapshot(snapshot)

        # Load from YAML
        loaded_snapshot = storage.load_snapshot("test-efs-persist")

        # Verify EFS resources persisted correctly
        efs_resources = [r for r in loaded_snapshot.resources if r.resource_type == "efs:file-system"]
        assert len(efs_resources) == 2

        # Verify raw_config persisted
        fs1 = next((r for r in efs_resources if r.name == "fs-test-001"), None)
        assert fs1 is not None
        assert fs1.raw_config is not None
        assert fs1.raw_config["encryption_enabled"] is True
        assert fs1.raw_config["file_system_id"] == "fs-test-001"
