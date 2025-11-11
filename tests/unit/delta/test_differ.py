"""Unit tests for ConfigDiffer - recursive configuration comparison."""

from __future__ import annotations

from src.delta.differ import ConfigDiffer
from src.models.config_diff import ChangeCategory


class TestConfigDiffer:
    """Tests for ConfigDiffer class."""

    def test_compare_simple_string_change(self) -> None:
        """Test comparison of simple string field change."""
        old_config = {"InstanceType": "t2.micro"}
        new_config = {"InstanceType": "t2.small"}
        arn = "arn:aws:ec2:us-east-1:123456789012:instance/i-12345"

        differ = ConfigDiffer()
        diffs = differ.compare(arn, old_config, new_config)

        assert len(diffs) == 1
        assert diffs[0].resource_arn == arn
        assert diffs[0].field_path == "InstanceType"
        assert diffs[0].old_value == "t2.micro"
        assert diffs[0].new_value == "t2.small"
        assert diffs[0].category == ChangeCategory.CONFIGURATION

    def test_compare_no_changes(self) -> None:
        """Test comparison when configs are identical."""
        config = {"InstanceType": "t2.micro", "State": "running"}
        arn = "arn:aws:ec2:us-east-1:123456789012:instance/i-12345"

        differ = ConfigDiffer()
        diffs = differ.compare(arn, config, config)

        assert len(diffs) == 0

    def test_compare_added_field(self) -> None:
        """Test detection of newly added field."""
        old_config = {"InstanceType": "t2.micro"}
        new_config = {"InstanceType": "t2.micro", "State": "running"}
        arn = "arn:aws:ec2:us-east-1:123456789012:instance/i-12345"

        differ = ConfigDiffer()
        diffs = differ.compare(arn, old_config, new_config)

        assert len(diffs) == 1
        assert diffs[0].field_path == "State"
        assert diffs[0].old_value is None
        assert diffs[0].new_value == "running"

    def test_compare_removed_field(self) -> None:
        """Test detection of removed field."""
        old_config = {"InstanceType": "t2.micro", "State": "running"}
        new_config = {"InstanceType": "t2.micro"}
        arn = "arn:aws:ec2:us-east-1:123456789012:instance/i-12345"

        differ = ConfigDiffer()
        diffs = differ.compare(arn, old_config, new_config)

        assert len(diffs) == 1
        assert diffs[0].field_path == "State"
        assert diffs[0].old_value == "running"
        assert diffs[0].new_value is None

    def test_compare_nested_dict_change(self) -> None:
        """Test recursive comparison of nested dictionaries."""
        old_config = {"Tags": {"Environment": "dev", "Owner": "alice"}}
        new_config = {"Tags": {"Environment": "prod", "Owner": "alice"}}
        arn = "arn:aws:ec2:us-east-1:123456789012:instance/i-12345"

        differ = ConfigDiffer()
        diffs = differ.compare(arn, old_config, new_config)

        assert len(diffs) == 1
        assert diffs[0].field_path == "Tags.Environment"
        assert diffs[0].old_value == "dev"
        assert diffs[0].new_value == "prod"
        assert diffs[0].category == ChangeCategory.TAGS

    def test_compare_deeply_nested_change(self) -> None:
        """Test comparison of deeply nested structures."""
        old_config = {"NetworkInterfaces": [{"Association": {"PublicIp": "1.2.3.4"}}]}
        new_config = {"NetworkInterfaces": [{"Association": {"PublicIp": "5.6.7.8"}}]}
        arn = "arn:aws:ec2:us-east-1:123456789012:instance/i-12345"

        differ = ConfigDiffer()
        diffs = differ.compare(arn, old_config, new_config)

        assert len(diffs) == 1
        assert diffs[0].field_path == "NetworkInterfaces.0.Association.PublicIp"
        assert diffs[0].old_value == "1.2.3.4"
        assert diffs[0].new_value == "5.6.7.8"

    def test_compare_list_with_different_lengths(self) -> None:
        """Test comparison when list lengths differ."""
        old_config = {"SecurityGroups": ["sg-123", "sg-456"]}
        new_config = {"SecurityGroups": ["sg-123"]}
        arn = "arn:aws:ec2:us-east-1:123456789012:instance/i-12345"

        differ = ConfigDiffer()
        diffs = differ.compare(arn, old_config, new_config)

        # Should detect that sg-456 was removed
        assert len(diffs) >= 1
        # One of the diffs should indicate the list length changed or item was removed

    def test_categorize_tags_change(self) -> None:
        """Test that tag changes are categorized as TAGS."""
        old_config = {"Tags": {"Name": "old-name"}}
        new_config = {"Tags": {"Name": "new-name"}}
        arn = "arn:aws:ec2:us-east-1:123456789012:instance/i-12345"

        differ = ConfigDiffer()
        diffs = differ.compare(arn, old_config, new_config)

        assert diffs[0].category == ChangeCategory.TAGS

    def test_categorize_security_change(self) -> None:
        """Test that security-related changes are categorized as SECURITY."""
        old_config = {"PubliclyAccessible": False}
        new_config = {"PubliclyAccessible": True}
        arn = "arn:aws:rds:us-east-1:123456789012:db:mydb"

        differ = ConfigDiffer()
        diffs = differ.compare(arn, old_config, new_config)

        assert diffs[0].category == ChangeCategory.SECURITY

    def test_categorize_security_group_change(self) -> None:
        """Test that SecurityGroups changes are categorized as SECURITY."""
        old_config = {"SecurityGroups": ["sg-123"]}
        new_config = {"SecurityGroups": ["sg-456"]}
        arn = "arn:aws:ec2:us-east-1:123456789012:instance/i-12345"

        differ = ConfigDiffer()
        diffs = differ.compare(arn, old_config, new_config)

        # At least one diff should be SECURITY category
        security_diffs = [d for d in diffs if d.category == ChangeCategory.SECURITY]
        assert len(security_diffs) >= 1

    def test_categorize_iam_permissions_change(self) -> None:
        """Test that IAM permission changes are categorized as PERMISSIONS."""
        old_config = {"AssumeRolePolicyDocument": {"Version": "2012-10-17", "Statement": []}}
        new_config = {"AssumeRolePolicyDocument": {"Version": "2012-10-17", "Statement": [{"Effect": "Allow"}]}}
        arn = "arn:aws:iam::123456789012:role/MyRole"

        differ = ConfigDiffer()
        diffs = differ.compare(arn, old_config, new_config)

        # IAM policy changes should be PERMISSIONS category
        permissions_diffs = [d for d in diffs if d.category == ChangeCategory.PERMISSIONS]
        assert len(permissions_diffs) >= 1

    def test_compare_empty_dicts(self) -> None:
        """Test comparison of empty dictionaries."""
        differ = ConfigDiffer()
        diffs = differ.compare("arn:aws:ec2:us-east-1:123456789012:instance/i-12345", {}, {})

        assert len(diffs) == 0

    def test_compare_none_values(self) -> None:
        """Test handling of None values in configuration."""
        old_config = {"Field": None}
        new_config = {"Field": "value"}
        arn = "arn:aws:ec2:us-east-1:123456789012:instance/i-12345"

        differ = ConfigDiffer()
        diffs = differ.compare(arn, old_config, new_config)

        assert len(diffs) == 1
        assert diffs[0].old_value is None
        assert diffs[0].new_value == "value"

    def test_compare_multiple_changes(self) -> None:
        """Test detection of multiple simultaneous changes."""
        old_config = {"InstanceType": "t2.micro", "Tags": {"Environment": "dev"}, "PubliclyAccessible": False}
        new_config = {"InstanceType": "t2.small", "Tags": {"Environment": "prod"}, "PubliclyAccessible": True}
        arn = "arn:aws:ec2:us-east-1:123456789012:instance/i-12345"

        differ = ConfigDiffer()
        diffs = differ.compare(arn, old_config, new_config)

        assert len(diffs) == 3
        # Should have TAGS, CONFIGURATION, and SECURITY changes
        categories = {d.category for d in diffs}
        assert ChangeCategory.TAGS in categories
        assert ChangeCategory.CONFIGURATION in categories
        assert ChangeCategory.SECURITY in categories

    def test_compare_encryption_change(self) -> None:
        """Test that encryption changes are categorized as SECURITY."""
        old_config = {"Encrypted": True, "KmsKeyId": "key-123"}
        new_config = {"Encrypted": False, "KmsKeyId": None}
        arn = "arn:aws:rds:us-east-1:123456789012:db:mydb"

        differ = ConfigDiffer()
        diffs = differ.compare(arn, old_config, new_config)

        # Encryption changes should be SECURITY
        security_diffs = [d for d in diffs if d.category == ChangeCategory.SECURITY]
        assert len(security_diffs) >= 1

    def test_compare_imdsv2_metadata_options(self) -> None:
        """Test that IMDSv2 MetadataOptions changes are categorized as SECURITY."""
        old_config = {"MetadataOptions": {"HttpTokens": "optional"}}
        new_config = {"MetadataOptions": {"HttpTokens": "required"}}
        arn = "arn:aws:ec2:us-east-1:123456789012:instance/i-12345"

        differ = ConfigDiffer()
        diffs = differ.compare(arn, old_config, new_config)

        assert len(diffs) == 1
        assert diffs[0].category == ChangeCategory.SECURITY
        assert "MetadataOptions" in diffs[0].field_path
