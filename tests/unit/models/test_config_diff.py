"""Unit tests for ConfigDiff model."""

from __future__ import annotations

import pytest

from src.models.config_diff import ChangeCategory, ConfigDiff


class TestChangeCategory:
    """Tests for ChangeCategory enum."""

    def test_change_category_values(self) -> None:
        """Test that ChangeCategory enum has correct values."""
        assert ChangeCategory.TAGS.value == "tags"
        assert ChangeCategory.CONFIGURATION.value == "configuration"
        assert ChangeCategory.SECURITY.value == "security"
        assert ChangeCategory.PERMISSIONS.value == "permissions"


class TestConfigDiff:
    """Tests for ConfigDiff dataclass."""

    def test_create_valid_diff(self) -> None:
        """Test creating a valid configuration diff."""
        diff = ConfigDiff(
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-12345",
            field_path="Tags.Environment",
            old_value="dev",
            new_value="prod",
            category=ChangeCategory.TAGS,
        )

        assert diff.resource_arn == "arn:aws:ec2:us-east-1:123456789012:instance/i-12345"
        assert diff.field_path == "Tags.Environment"
        assert diff.old_value == "dev"
        assert diff.new_value == "prod"
        assert diff.category == ChangeCategory.TAGS

    def test_create_diff_with_none_old_value(self) -> None:
        """Test creating a diff where field was added (old_value is None)."""
        diff = ConfigDiff(
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-12345",
            field_path="Tags.NewTag",
            old_value=None,
            new_value="new-value",
            category=ChangeCategory.TAGS,
        )

        assert diff.old_value is None
        assert diff.new_value == "new-value"

    def test_create_diff_with_none_new_value(self) -> None:
        """Test creating a diff where field was removed (new_value is None)."""
        diff = ConfigDiff(
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-12345",
            field_path="Tags.OldTag",
            old_value="old-value",
            new_value=None,
            category=ChangeCategory.TAGS,
        )

        assert diff.old_value == "old-value"
        assert diff.new_value is None

    def test_invalid_arn_format(self) -> None:
        """Test that invalid ARN format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid ARN format"):
            ConfigDiff(
                resource_arn="not-an-arn",
                field_path="Tags.Environment",
                old_value="dev",
                new_value="prod",
                category=ChangeCategory.TAGS,
            )

    def test_empty_arn(self) -> None:
        """Test that empty ARN raises ValueError."""
        with pytest.raises(ValueError, match="Invalid ARN format"):
            ConfigDiff(
                resource_arn="",
                field_path="Tags.Environment",
                old_value="dev",
                new_value="prod",
                category=ChangeCategory.TAGS,
            )

    def test_empty_field_path(self) -> None:
        """Test that empty field_path raises ValueError."""
        with pytest.raises(ValueError, match="field_path cannot be empty"):
            ConfigDiff(
                resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-12345",
                field_path="",
                old_value="dev",
                new_value="prod",
                category=ChangeCategory.TAGS,
            )

    def test_invalid_category_type(self) -> None:
        """Test that invalid category type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid category type"):
            ConfigDiff(
                resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-12345",
                field_path="Tags.Environment",
                old_value="dev",
                new_value="prod",
                category="tags",  # type: ignore
            )

    def test_with_path_prefix(self) -> None:
        """Test adding a prefix to the field path."""
        diff = ConfigDiff(
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-12345",
            field_path="Environment",
            old_value="dev",
            new_value="prod",
            category=ChangeCategory.TAGS,
        )

        prefixed = diff.with_path_prefix("Tags")

        assert prefixed.field_path == "Tags.Environment"
        assert prefixed.resource_arn == diff.resource_arn
        assert prefixed.old_value == diff.old_value
        assert prefixed.new_value == diff.new_value
        assert prefixed.category == diff.category

    def test_with_path_prefix_nested(self) -> None:
        """Test adding a prefix to already nested field path."""
        diff = ConfigDiff(
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-12345",
            field_path="IpPermissions.0.FromPort",
            old_value=22,
            new_value=2222,
            category=ChangeCategory.SECURITY,
        )

        prefixed = diff.with_path_prefix("SecurityGroup")

        assert prefixed.field_path == "SecurityGroup.IpPermissions.0.FromPort"

    def test_is_security_critical_public_accessibility(self) -> None:
        """Test that PubliclyAccessible field is flagged as security critical."""
        diff = ConfigDiff(
            resource_arn="arn:aws:rds:us-east-1:123456789012:db:mydb",
            field_path="PubliclyAccessible",
            old_value=False,
            new_value=True,
            category=ChangeCategory.SECURITY,
        )

        assert diff.is_security_critical() is True

    def test_is_security_critical_encryption(self) -> None:
        """Test that encryption field is flagged as security critical."""
        diff = ConfigDiff(
            resource_arn="arn:aws:s3:::my-bucket",
            field_path="ServerSideEncryptionConfiguration.Rules.0.ApplyServerSideEncryptionByDefault.SSEAlgorithm",
            old_value="AES256",
            new_value=None,
            category=ChangeCategory.SECURITY,
        )

        assert diff.is_security_critical() is True

    def test_is_security_critical_security_groups(self) -> None:
        """Test that SecurityGroups field is flagged as security critical."""
        diff = ConfigDiff(
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-12345",
            field_path="SecurityGroups.0.GroupId",
            old_value="sg-old",
            new_value="sg-new",
            category=ChangeCategory.SECURITY,
        )

        assert diff.is_security_critical() is True

    def test_is_security_critical_case_insensitive(self) -> None:
        """Test that security critical detection is case insensitive."""
        diff = ConfigDiff(
            resource_arn="arn:aws:s3:::my-bucket",
            field_path="bucketpolicy",
            old_value={},
            new_value={"Statement": []},
            category=ChangeCategory.SECURITY,
        )

        assert diff.is_security_critical() is True

    def test_is_security_critical_metadata_options(self) -> None:
        """Test that MetadataOptions (IMDSv2) is flagged as security critical."""
        diff = ConfigDiff(
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-12345",
            field_path="MetadataOptions.HttpTokens",
            old_value="optional",
            new_value="required",
            category=ChangeCategory.SECURITY,
        )

        assert diff.is_security_critical() is True

    def test_is_not_security_critical_tags(self) -> None:
        """Test that non-security fields are not flagged as security critical."""
        diff = ConfigDiff(
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-12345",
            field_path="Tags.Environment",
            old_value="dev",
            new_value="prod",
            category=ChangeCategory.TAGS,
        )

        assert diff.is_security_critical() is False

    def test_is_not_security_critical_instance_type(self) -> None:
        """Test that instance type changes are not security critical."""
        diff = ConfigDiff(
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-12345",
            field_path="InstanceType",
            old_value="t2.micro",
            new_value="t2.small",
            category=ChangeCategory.CONFIGURATION,
        )

        assert diff.is_security_critical() is False

    def test_to_dict(self) -> None:
        """Test converting ConfigDiff to dictionary."""
        diff = ConfigDiff(
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-12345",
            field_path="InstanceType",
            old_value="t2.micro",
            new_value="t2.small",
            category=ChangeCategory.CONFIGURATION,
        )

        result = diff.to_dict()

        assert result["resource_arn"] == "arn:aws:ec2:us-east-1:123456789012:instance/i-12345"
        assert result["field_path"] == "InstanceType"
        assert result["old_value"] == "t2.micro"
        assert result["new_value"] == "t2.small"
        assert result["category"] == "configuration"
        assert result["security_critical"] is False

    def test_to_dict_with_security_critical(self) -> None:
        """Test to_dict includes security_critical flag."""
        diff = ConfigDiff(
            resource_arn="arn:aws:rds:us-east-1:123456789012:db:mydb",
            field_path="PubliclyAccessible",
            old_value=False,
            new_value=True,
            category=ChangeCategory.SECURITY,
        )

        result = diff.to_dict()
        assert result["security_critical"] is True

    def test_from_dict(self) -> None:
        """Test creating ConfigDiff from dictionary."""
        data = {
            "resource_arn": "arn:aws:ec2:us-east-1:123456789012:instance/i-12345",
            "field_path": "Tags.Environment",
            "old_value": "dev",
            "new_value": "prod",
            "category": "tags",
        }

        diff = ConfigDiff.from_dict(data)

        assert diff.resource_arn == "arn:aws:ec2:us-east-1:123456789012:instance/i-12345"
        assert diff.field_path == "Tags.Environment"
        assert diff.old_value == "dev"
        assert diff.new_value == "prod"
        assert diff.category == ChangeCategory.TAGS

    def test_from_dict_case_insensitive_category(self) -> None:
        """Test that from_dict handles uppercase category values."""
        data = {
            "resource_arn": "arn:aws:ec2:us-east-1:123456789012:instance/i-12345",
            "field_path": "Test",
            "old_value": "a",
            "new_value": "b",
            "category": "SECURITY",
        }

        diff = ConfigDiff.from_dict(data)
        assert diff.category == ChangeCategory.SECURITY

    def test_from_dict_invalid_category(self) -> None:
        """Test that from_dict raises ValueError for invalid category."""
        data = {
            "resource_arn": "arn:aws:ec2:us-east-1:123456789012:instance/i-12345",
            "field_path": "Test",
            "old_value": "a",
            "new_value": "b",
            "category": "invalid",
        }

        with pytest.raises(ValueError, match="Invalid category value: invalid"):
            ConfigDiff.from_dict(data)

    def test_from_dict_with_none_values(self) -> None:
        """Test creating ConfigDiff from dictionary with None values."""
        data = {
            "resource_arn": "arn:aws:ec2:us-east-1:123456789012:instance/i-12345",
            "field_path": "Tags.Removed",
            "old_value": "old",
            "new_value": None,
            "category": "tags",
        }

        diff = ConfigDiff.from_dict(data)
        assert diff.old_value == "old"
        assert diff.new_value is None

    def test_round_trip_to_dict_from_dict(self) -> None:
        """Test that to_dict and from_dict are symmetric."""
        original = ConfigDiff(
            resource_arn="arn:aws:rds:us-east-1:123456789012:db:mydb",
            field_path="PubliclyAccessible",
            old_value=False,
            new_value=True,
            category=ChangeCategory.SECURITY,
        )

        # Convert to dict and back
        data = original.to_dict()
        # Note: security_critical is not part of from_dict, it's computed
        del data["security_critical"]
        reconstructed = ConfigDiff.from_dict(data)

        # Compare all fields
        assert reconstructed.resource_arn == original.resource_arn
        assert reconstructed.field_path == original.field_path
        assert reconstructed.old_value == original.old_value
        assert reconstructed.new_value == original.new_value
        assert reconstructed.category == original.category
