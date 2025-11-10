"""Unit tests for EFSFileSystem model."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.models.efs_resource import EFSFileSystem


class TestEFSFileSystem:
    """Tests for EFSFileSystem dataclass."""

    def test_create_valid_efs_file_system(self) -> None:
        """Test creating a valid EFS file system."""
        created_at = datetime.now(timezone.utc)
        efs = EFSFileSystem(
            file_system_id="fs-12345678",
            arn="arn:aws:elasticfilesystem:us-east-1:123456789012:file-system/fs-12345678",
            encryption_enabled=True,
            kms_key_id="arn:aws:kms:us-east-1:123456789012:key/abcd1234-5678-90ab-cdef-1234567890ab",
            performance_mode="generalPurpose",
            lifecycle_state="available",
            tags={"Environment": "prod", "Owner": "team-a"},
            region="us-east-1",
            created_at=created_at,
        )

        assert efs.file_system_id == "fs-12345678"
        assert efs.arn == "arn:aws:elasticfilesystem:us-east-1:123456789012:file-system/fs-12345678"
        assert efs.encryption_enabled is True
        assert efs.kms_key_id == "arn:aws:kms:us-east-1:123456789012:key/abcd1234-5678-90ab-cdef-1234567890ab"
        assert efs.performance_mode == "generalPurpose"
        assert efs.lifecycle_state == "available"
        assert efs.tags == {"Environment": "prod", "Owner": "team-a"}
        assert efs.region == "us-east-1"
        assert efs.created_at == created_at

    def test_create_unencrypted_efs(self) -> None:
        """Test creating an unencrypted EFS file system (no KMS key)."""
        efs = EFSFileSystem(
            file_system_id="fs-87654321",
            arn="arn:aws:elasticfilesystem:us-west-2:123456789012:file-system/fs-87654321",
            encryption_enabled=False,
            kms_key_id=None,
            performance_mode="maxIO",
            lifecycle_state="available",
            tags={},
            region="us-west-2",
            created_at=datetime.now(timezone.utc),
        )

        assert efs.encryption_enabled is False
        assert efs.kms_key_id is None
        assert efs.performance_mode == "maxIO"

    def test_validate_file_system_id_format(self) -> None:
        """Test that file system ID validation enforces fs-* format."""
        efs = EFSFileSystem(
            file_system_id="invalid-id",
            arn="arn:aws:elasticfilesystem:us-east-1:123456789012:file-system/fs-12345678",
            encryption_enabled=True,
            kms_key_id=None,
            performance_mode="generalPurpose",
            lifecycle_state="available",
            tags={},
            region="us-east-1",
            created_at=datetime.now(timezone.utc),
        )

        with pytest.raises(ValueError, match="Invalid file_system_id format"):
            efs.validate()

    def test_validate_valid_file_system_id(self) -> None:
        """Test validation passes for valid fs-* format."""
        efs = EFSFileSystem(
            file_system_id="fs-abcdef123456",
            arn="arn:aws:elasticfilesystem:us-east-1:123456789012:file-system/fs-abcdef123456",
            encryption_enabled=True,
            kms_key_id=None,
            performance_mode="generalPurpose",
            lifecycle_state="available",
            tags={},
            region="us-east-1",
            created_at=datetime.now(timezone.utc),
        )

        assert efs.validate() is True

    def test_validate_performance_mode(self) -> None:
        """Test that performance_mode must be generalPurpose or maxIO."""
        efs = EFSFileSystem(
            file_system_id="fs-12345678",
            arn="arn:aws:elasticfilesystem:us-east-1:123456789012:file-system/fs-12345678",
            encryption_enabled=True,
            kms_key_id=None,
            performance_mode="invalid-mode",
            lifecycle_state="available",
            tags={},
            region="us-east-1",
            created_at=datetime.now(timezone.utc),
        )

        with pytest.raises(ValueError, match="Invalid performance_mode"):
            efs.validate()

    def test_validate_lifecycle_state(self) -> None:
        """Test that lifecycle_state validation works."""
        valid_states = ["available", "creating", "deleting", "deleted"]

        for state in valid_states:
            efs = EFSFileSystem(
                file_system_id="fs-12345678",
                arn="arn:aws:elasticfilesystem:us-east-1:123456789012:file-system/fs-12345678",
                encryption_enabled=True,
                kms_key_id=None,
                performance_mode="generalPurpose",
                lifecycle_state=state,
                tags={},
                region="us-east-1",
                created_at=datetime.now(timezone.utc),
            )
            assert efs.validate() is True

    def test_validate_invalid_lifecycle_state(self) -> None:
        """Test that invalid lifecycle_state raises error."""
        efs = EFSFileSystem(
            file_system_id="fs-12345678",
            arn="arn:aws:elasticfilesystem:us-east-1:123456789012:file-system/fs-12345678",
            encryption_enabled=True,
            kms_key_id=None,
            performance_mode="generalPurpose",
            lifecycle_state="invalid-state",
            tags={},
            region="us-east-1",
            created_at=datetime.now(timezone.utc),
        )

        with pytest.raises(ValueError, match="Invalid lifecycle_state"):
            efs.validate()

    def test_encryption_with_kms_key(self) -> None:
        """Test validation passes when encryption enabled with KMS key."""
        efs = EFSFileSystem(
            file_system_id="fs-12345678",
            arn="arn:aws:elasticfilesystem:us-east-1:123456789012:file-system/fs-12345678",
            encryption_enabled=True,
            kms_key_id="arn:aws:kms:us-east-1:123456789012:key/abcd1234",
            performance_mode="generalPurpose",
            lifecycle_state="available",
            tags={},
            region="us-east-1",
            created_at=datetime.now(timezone.utc),
        )

        assert efs.validate() is True

    def test_to_resource_dict(self) -> None:
        """Test conversion to Resource-compatible dictionary."""
        created_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        efs = EFSFileSystem(
            file_system_id="fs-12345678",
            arn="arn:aws:elasticfilesystem:us-east-1:123456789012:file-system/fs-12345678",
            encryption_enabled=True,
            kms_key_id="arn:aws:kms:us-east-1:123456789012:key/abcd1234",
            performance_mode="generalPurpose",
            lifecycle_state="available",
            tags={"Environment": "prod"},
            region="us-east-1",
            created_at=created_at,
        )

        resource_dict = efs.to_resource_dict()

        assert resource_dict["arn"] == "arn:aws:elasticfilesystem:us-east-1:123456789012:file-system/fs-12345678"
        assert resource_dict["resource_type"] == "efs:file-system"
        assert resource_dict["name"] == "fs-12345678"
        assert resource_dict["region"] == "us-east-1"
        assert resource_dict["tags"] == {"Environment": "prod"}
        assert resource_dict["created_at"] == created_at
        assert "raw_config" in resource_dict
        assert resource_dict["raw_config"]["file_system_id"] == "fs-12345678"
        assert resource_dict["raw_config"]["encryption_enabled"] is True
        assert resource_dict["raw_config"]["performance_mode"] == "generalPurpose"

    def test_to_resource_dict_with_empty_tags(self) -> None:
        """Test to_resource_dict with no tags."""
        efs = EFSFileSystem(
            file_system_id="fs-12345678",
            arn="arn:aws:elasticfilesystem:us-east-1:123456789012:file-system/fs-12345678",
            encryption_enabled=False,
            kms_key_id=None,
            performance_mode="generalPurpose",
            lifecycle_state="available",
            tags={},
            region="us-east-1",
            created_at=datetime.now(timezone.utc),
        )

        resource_dict = efs.to_resource_dict()
        assert resource_dict["tags"] == {}
