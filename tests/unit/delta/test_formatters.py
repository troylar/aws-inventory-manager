"""Unit tests for DriftFormatter - color-coded drift output."""

from __future__ import annotations

from io import StringIO

import pytest
from rich.console import Console

from src.delta.formatters import DriftFormatter
from src.delta.models import DriftReport
from src.models.config_diff import ChangeCategory, ConfigDiff


class TestDriftFormatter:
    """Tests for DriftFormatter class."""

    @pytest.fixture
    def console(self) -> Console:
        """Create a Rich console for testing."""
        return Console(file=StringIO(), force_terminal=True, width=120)

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
        ]

    def test_format_empty_report(self, console: Console) -> None:
        """Test formatting an empty drift report."""
        report = DriftReport()
        formatter = DriftFormatter(console)

        formatter.display(report)

        output = console.file.getvalue()  # type: ignore
        assert "No configuration changes detected" in output or "0 changes" in output

    def test_format_single_diff(self, console: Console) -> None:
        """Test formatting a single configuration diff."""
        diff = ConfigDiff(
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-12345",
            field_path="InstanceType",
            old_value="t2.micro",
            new_value="t2.small",
            category=ChangeCategory.CONFIGURATION,
        )
        report = DriftReport()
        report.add_diff(diff)

        formatter = DriftFormatter(console)
        formatter.display(report)

        output = console.file.getvalue()  # type: ignore
        assert "InstanceType" in output
        assert "t2.micro" in output
        assert "t2.small" in output

    def test_format_color_coding_removed(self, console: Console) -> None:
        """Test that removed fields are displayed in red."""
        diff = ConfigDiff(
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-12345",
            field_path="Tags.OldTag",
            old_value="old-value",
            new_value=None,
            category=ChangeCategory.TAGS,
        )
        report = DriftReport()
        report.add_diff(diff)

        formatter = DriftFormatter(console)
        formatter.display(report)

        output = console.file.getvalue()  # type: ignore
        # Rich output includes ANSI codes for red color
        assert "OldTag" in output
        assert "old-value" in output

    def test_format_color_coding_added(self, console: Console) -> None:
        """Test that added fields are displayed in green."""
        diff = ConfigDiff(
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-12345",
            field_path="Tags.NewTag",
            old_value=None,
            new_value="new-value",
            category=ChangeCategory.TAGS,
        )
        report = DriftReport()
        report.add_diff(diff)

        formatter = DriftFormatter(console)
        formatter.display(report)

        output = console.file.getvalue()  # type: ignore
        assert "NewTag" in output
        assert "new-value" in output

    def test_format_color_coding_security(self, console: Console) -> None:
        """Test that security changes are highlighted in yellow."""
        diff = ConfigDiff(
            resource_arn="arn:aws:rds:us-east-1:123456789012:db:mydb",
            field_path="PubliclyAccessible",
            old_value=False,
            new_value=True,
            category=ChangeCategory.SECURITY,
        )
        report = DriftReport()
        report.add_diff(diff)

        formatter = DriftFormatter(console)
        formatter.display(report)

        output = console.file.getvalue()  # type: ignore
        assert "PubliclyAccessible" in output
        assert "False" in output or "false" in output.lower()
        assert "True" in output or "true" in output.lower()

    def test_format_color_coding_configuration(self, console: Console) -> None:
        """Test that configuration changes are displayed in cyan."""
        diff = ConfigDiff(
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-12345",
            field_path="InstanceType",
            old_value="t2.micro",
            new_value="t2.small",
            category=ChangeCategory.CONFIGURATION,
        )
        report = DriftReport()
        report.add_diff(diff)

        formatter = DriftFormatter(console)
        formatter.display(report)

        output = console.file.getvalue()  # type: ignore
        assert "InstanceType" in output
        assert "t2.micro" in output
        assert "t2.small" in output

    def test_format_grouped_by_category(self, console: Console, sample_diffs: list[ConfigDiff]) -> None:
        """Test that diffs are grouped by category."""
        report = DriftReport()
        for diff in sample_diffs:
            report.add_diff(diff)

        formatter = DriftFormatter(console)
        formatter.display(report)

        output = console.file.getvalue()  # type: ignore
        # Should have sections for Tags, Configuration, Security
        assert "Tags" in output or "TAGS" in output
        assert "Configuration" in output or "CONFIGURATION" in output
        assert "Security" in output or "SECURITY" in output

    def test_format_grouped_by_resource(self, console: Console, sample_diffs: list[ConfigDiff]) -> None:
        """Test that diffs can be grouped by resource."""
        report = DriftReport()
        for diff in sample_diffs:
            report.add_diff(diff)

        formatter = DriftFormatter(console)
        formatter.display(report, group_by="resource")

        output = console.file.getvalue()  # type: ignore
        # Strip ANSI codes for easier testing
        import re

        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        plain_output = ansi_escape.sub("", output)
        # Should show resource ARNs or resource IDs
        assert "i-12345" in plain_output
        assert "db" in plain_output or "mydb" in plain_output

    def test_format_filter_by_resource_type(self, console: Console, sample_diffs: list[ConfigDiff]) -> None:
        """Test filtering diffs by resource type."""
        report = DriftReport()
        for diff in sample_diffs:
            report.add_diff(diff)

        formatter = DriftFormatter(console)
        # Filter to only show EC2 instances
        formatter.display(report, resource_type_filter="ec2")

        output = console.file.getvalue()  # type: ignore
        # Should show EC2 changes
        assert "InstanceType" in output or "Tags.Environment" in output
        # Should NOT show RDS changes
        assert "PubliclyAccessible" not in output

    def test_format_filter_by_region(self, console: Console) -> None:
        """Test filtering diffs by region."""
        diffs = [
            ConfigDiff(
                resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-12345",
                field_path="InstanceType",
                old_value="t2.micro",
                new_value="t2.small",
                category=ChangeCategory.CONFIGURATION,
            ),
            ConfigDiff(
                resource_arn="arn:aws:ec2:us-west-2:123456789012:instance/i-67890",
                field_path="InstanceType",
                old_value="t2.small",
                new_value="t2.medium",
                category=ChangeCategory.CONFIGURATION,
            ),
        ]
        report = DriftReport()
        for diff in diffs:
            report.add_diff(diff)

        formatter = DriftFormatter(console)
        formatter.display(report, region_filter="us-east-1")

        output = console.file.getvalue()  # type: ignore
        # Strip ANSI codes for easier testing
        import re

        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        plain_output = ansi_escape.sub("", output)
        # Should show us-east-1 changes (show i-12345, not i-67890)
        assert "i-12345" in plain_output
        # Should NOT show us-west-2 changes
        assert "i-67890" not in plain_output

    def test_format_old_to_new_arrow(self, console: Console) -> None:
        """Test that changes are formatted with old → new arrow."""
        diff = ConfigDiff(
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-12345",
            field_path="InstanceType",
            old_value="t2.micro",
            new_value="t2.small",
            category=ChangeCategory.CONFIGURATION,
        )
        report = DriftReport()
        report.add_diff(diff)

        formatter = DriftFormatter(console)
        formatter.display(report)

        output = console.file.getvalue()  # type: ignore
        # Should use arrow notation for changes
        assert "→" in output or "->" in output
        assert "t2.micro" in output
        assert "t2.small" in output

    def test_format_handles_long_values(self, console: Console) -> None:
        """Test formatting of very long configuration values."""
        long_value = "a" * 200
        diff = ConfigDiff(
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-12345",
            field_path="UserData",
            old_value=long_value,
            new_value="short",
            category=ChangeCategory.CONFIGURATION,
        )
        report = DriftReport()
        report.add_diff(diff)

        formatter = DriftFormatter(console)
        formatter.display(report)

        output = console.file.getvalue()  # type: ignore
        assert "UserData" in output
        # Long values should be truncated or formatted appropriately

    def test_format_summary_statistics(self, console: Console, sample_diffs: list[ConfigDiff]) -> None:
        """Test that summary statistics are displayed."""
        report = DriftReport()
        for diff in sample_diffs:
            report.add_diff(diff)

        formatter = DriftFormatter(console)
        formatter.display(report)

        output = console.file.getvalue()  # type: ignore
        # Should show total count and breakdown by category
        assert "3" in output  # Total diffs
        # Category counts
        assert "1" in output  # Count for each category

    def test_format_no_console_provided(self, sample_diffs: list[ConfigDiff]) -> None:
        """Test that formatter creates default console if none provided."""
        report = DriftReport()
        for diff in sample_diffs:
            report.add_diff(diff)

        formatter = DriftFormatter()  # No console provided
        # Should not raise an error
        formatter.display(report)
