"""Unit tests for DriftReport model - container for configuration diffs."""

from __future__ import annotations

import pytest

from src.delta.models import DriftReport
from src.models.config_diff import ChangeCategory, ConfigDiff


class TestDriftReport:
    """Tests for DriftReport container class."""

    @pytest.fixture
    def sample_diffs(self) -> list[ConfigDiff]:
        """Create sample configuration diffs for testing."""
        return [
            ConfigDiff(
                resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-12345",
                field_path="Tags.Environment",
                old_value="dev",
                new_value="prod",
                category=ChangeCategory.TAGS,
            ),
            ConfigDiff(
                resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-12345",
                field_path="InstanceType",
                old_value="t2.micro",
                new_value="t2.small",
                category=ChangeCategory.CONFIGURATION,
            ),
            ConfigDiff(
                resource_arn="arn:aws:rds:us-east-1:123456789012:db:mydb",
                field_path="PubliclyAccessible",
                old_value=False,
                new_value=True,
                category=ChangeCategory.SECURITY,
            ),
            ConfigDiff(
                resource_arn="arn:aws:iam::123456789012:role/MyRole",
                field_path="AssumeRolePolicyDocument.Statement.0.Effect",
                old_value="Deny",
                new_value="Allow",
                category=ChangeCategory.PERMISSIONS,
            ),
        ]

    def test_create_empty_report(self) -> None:
        """Test creating an empty drift report."""
        report = DriftReport()

        assert report.total_changes == 0
        assert len(report.get_all_diffs()) == 0

    def test_add_single_diff(self) -> None:
        """Test adding a single diff to the report."""
        report = DriftReport()
        diff = ConfigDiff(
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-12345",
            field_path="InstanceType",
            old_value="t2.micro",
            new_value="t2.small",
            category=ChangeCategory.CONFIGURATION,
        )

        report.add_diff(diff)

        assert report.total_changes == 1
        assert len(report.get_all_diffs()) == 1

    def test_add_multiple_diffs(self, sample_diffs: list[ConfigDiff]) -> None:
        """Test adding multiple diffs to the report."""
        report = DriftReport()

        for diff in sample_diffs:
            report.add_diff(diff)

        assert report.total_changes == 4
        assert len(report.get_all_diffs()) == 4

    def test_get_diffs_by_category_tags(self, sample_diffs: list[ConfigDiff]) -> None:
        """Test filtering diffs by TAGS category."""
        report = DriftReport()
        for diff in sample_diffs:
            report.add_diff(diff)

        tags_diffs = report.get_diffs_by_category(ChangeCategory.TAGS)

        assert len(tags_diffs) == 1
        assert tags_diffs[0].field_path == "Tags.Environment"

    def test_get_diffs_by_category_configuration(self, sample_diffs: list[ConfigDiff]) -> None:
        """Test filtering diffs by CONFIGURATION category."""
        report = DriftReport()
        for diff in sample_diffs:
            report.add_diff(diff)

        config_diffs = report.get_diffs_by_category(ChangeCategory.CONFIGURATION)

        assert len(config_diffs) == 1
        assert config_diffs[0].field_path == "InstanceType"

    def test_get_diffs_by_category_security(self, sample_diffs: list[ConfigDiff]) -> None:
        """Test filtering diffs by SECURITY category."""
        report = DriftReport()
        for diff in sample_diffs:
            report.add_diff(diff)

        security_diffs = report.get_diffs_by_category(ChangeCategory.SECURITY)

        assert len(security_diffs) == 1
        assert security_diffs[0].field_path == "PubliclyAccessible"

    def test_get_diffs_by_category_permissions(self, sample_diffs: list[ConfigDiff]) -> None:
        """Test filtering diffs by PERMISSIONS category."""
        report = DriftReport()
        for diff in sample_diffs:
            report.add_diff(diff)

        permissions_diffs = report.get_diffs_by_category(ChangeCategory.PERMISSIONS)

        assert len(permissions_diffs) == 1
        assert "AssumeRolePolicyDocument" in permissions_diffs[0].field_path

    def test_get_diffs_by_category_empty(self) -> None:
        """Test get_diffs_by_category returns empty list when no matches."""
        report = DriftReport()
        diff = ConfigDiff(
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-12345",
            field_path="InstanceType",
            old_value="t2.micro",
            new_value="t2.small",
            category=ChangeCategory.CONFIGURATION,
        )
        report.add_diff(diff)

        security_diffs = report.get_diffs_by_category(ChangeCategory.SECURITY)

        assert len(security_diffs) == 0

    def test_get_security_critical_diffs(self, sample_diffs: list[ConfigDiff]) -> None:
        """Test filtering for security-critical diffs."""
        report = DriftReport()
        for diff in sample_diffs:
            report.add_diff(diff)

        critical_diffs = report.get_security_critical_diffs()

        # PubliclyAccessible change should be security-critical
        assert len(critical_diffs) >= 1
        critical_paths = [d.field_path for d in critical_diffs]
        assert "PubliclyAccessible" in critical_paths

    def test_get_security_critical_diffs_empty(self) -> None:
        """Test get_security_critical_diffs when no critical changes."""
        report = DriftReport()
        diff = ConfigDiff(
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-12345",
            field_path="Tags.Name",
            old_value="old-name",
            new_value="new-name",
            category=ChangeCategory.TAGS,
        )
        report.add_diff(diff)

        critical_diffs = report.get_security_critical_diffs()

        assert len(critical_diffs) == 0

    def test_get_diffs_by_resource(self, sample_diffs: list[ConfigDiff]) -> None:
        """Test filtering diffs by resource ARN."""
        report = DriftReport()
        for diff in sample_diffs:
            report.add_diff(diff)

        ec2_arn = "arn:aws:ec2:us-east-1:123456789012:instance/i-12345"
        ec2_diffs = report.get_diffs_by_resource(ec2_arn)

        assert len(ec2_diffs) == 2  # InstanceType and Tags.Environment
        arns = [d.resource_arn for d in ec2_diffs]
        assert all(arn == ec2_arn for arn in arns)

    def test_get_diffs_by_resource_no_matches(self, sample_diffs: list[ConfigDiff]) -> None:
        """Test get_diffs_by_resource when ARN doesn't exist."""
        report = DriftReport()
        for diff in sample_diffs:
            report.add_diff(diff)

        nonexistent_arn = "arn:aws:s3:::nonexistent-bucket"
        diffs = report.get_diffs_by_resource(nonexistent_arn)

        assert len(diffs) == 0

    def test_get_diffs_by_resource_type(self, sample_diffs: list[ConfigDiff]) -> None:
        """Test filtering diffs by resource type."""
        report = DriftReport()
        for diff in sample_diffs:
            report.add_diff(diff)

        # Filter for EC2 instances
        ec2_diffs = report.get_diffs_by_resource_type("ec2")

        assert len(ec2_diffs) == 2  # InstanceType and Tags
        assert all("ec2" in d.resource_arn for d in ec2_diffs)

    def test_get_diffs_by_resource_type_case_insensitive(self, sample_diffs: list[ConfigDiff]) -> None:
        """Test that resource type filtering is case insensitive."""
        report = DriftReport()
        for diff in sample_diffs:
            report.add_diff(diff)

        # Filter with uppercase
        ec2_diffs = report.get_diffs_by_resource_type("EC2")

        assert len(ec2_diffs) == 2

    def test_get_diffs_by_region(self, sample_diffs: list[ConfigDiff]) -> None:
        """Test filtering diffs by AWS region."""
        report = DriftReport()
        for diff in sample_diffs:
            report.add_diff(diff)

        us_east_diffs = report.get_diffs_by_region("us-east-1")

        # EC2 and RDS diffs are in us-east-1, IAM is global (no region)
        assert len(us_east_diffs) == 3

    def test_get_diffs_by_region_no_matches(self, sample_diffs: list[ConfigDiff]) -> None:
        """Test get_diffs_by_region when region doesn't exist."""
        report = DriftReport()
        for diff in sample_diffs:
            report.add_diff(diff)

        us_west_diffs = report.get_diffs_by_region("us-west-2")

        assert len(us_west_diffs) == 0

    def test_get_summary(self, sample_diffs: list[ConfigDiff]) -> None:
        """Test generating summary statistics."""
        report = DriftReport()
        for diff in sample_diffs:
            report.add_diff(diff)

        summary = report.get_summary()

        assert summary["total_changes"] == 4
        assert summary["tags_count"] == 1
        assert summary["configuration_count"] == 1
        assert summary["security_count"] == 1
        assert summary["permissions_count"] == 1
        assert summary["security_critical_count"] >= 1

    def test_get_summary_empty_report(self) -> None:
        """Test generating summary for empty report."""
        report = DriftReport()

        summary = report.get_summary()

        assert summary["total_changes"] == 0
        assert summary["tags_count"] == 0
        assert summary["configuration_count"] == 0
        assert summary["security_count"] == 0
        assert summary["permissions_count"] == 0
        assert summary["security_critical_count"] == 0

    def test_group_by_resource(self, sample_diffs: list[ConfigDiff]) -> None:
        """Test grouping diffs by resource ARN."""
        report = DriftReport()
        for diff in sample_diffs:
            report.add_diff(diff)

        grouped = report.group_by_resource()

        assert len(grouped) == 3  # EC2, RDS, IAM
        ec2_arn = "arn:aws:ec2:us-east-1:123456789012:instance/i-12345"
        assert ec2_arn in grouped
        assert len(grouped[ec2_arn]) == 2

    def test_group_by_category(self, sample_diffs: list[ConfigDiff]) -> None:
        """Test grouping diffs by category."""
        report = DriftReport()
        for diff in sample_diffs:
            report.add_diff(diff)

        grouped = report.group_by_category()

        assert len(grouped) == 4  # TAGS, CONFIGURATION, SECURITY, PERMISSIONS
        assert ChangeCategory.TAGS in grouped
        assert len(grouped[ChangeCategory.TAGS]) == 1
        assert ChangeCategory.SECURITY in grouped
        assert len(grouped[ChangeCategory.SECURITY]) == 1

    def test_to_dict(self, sample_diffs: list[ConfigDiff]) -> None:
        """Test converting DriftReport to dictionary."""
        report = DriftReport()
        for diff in sample_diffs:
            report.add_diff(diff)

        result = report.to_dict()

        assert result["total_changes"] == 4
        assert len(result["diffs"]) == 4
        assert "summary" in result
        # First diff should be serialized correctly
        assert result["diffs"][0]["field_path"] == "Tags.Environment"
        assert result["diffs"][0]["category"] == "tags"

    def test_to_dict_empty_report(self) -> None:
        """Test to_dict for empty report."""
        report = DriftReport()

        result = report.to_dict()

        assert result["total_changes"] == 0
        assert len(result["diffs"]) == 0
        assert result["summary"]["security_critical_count"] == 0

    def test_has_security_critical_changes(self, sample_diffs: list[ConfigDiff]) -> None:
        """Test checking if report has security-critical changes."""
        report = DriftReport()
        for diff in sample_diffs:
            report.add_diff(diff)

        assert report.has_security_critical_changes() is True

    def test_has_security_critical_changes_false(self) -> None:
        """Test has_security_critical_changes when no critical changes."""
        report = DriftReport()
        diff = ConfigDiff(
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-12345",
            field_path="Tags.Name",
            old_value="old",
            new_value="new",
            category=ChangeCategory.TAGS,
        )
        report.add_diff(diff)

        assert report.has_security_critical_changes() is False
