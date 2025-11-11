"""Drift report model for containing configuration differences."""

from __future__ import annotations

from typing import Any

from ..models.config_diff import ChangeCategory, ConfigDiff


class DriftReport:
    """Container for configuration drift analysis results.

    Stores and organizes ConfigDiff objects representing field-level changes
    between snapshot versions.
    """

    def __init__(self) -> None:
        """Initialize an empty drift report."""
        self._diffs: list[ConfigDiff] = []

    @property
    def total_changes(self) -> int:
        """Get total number of configuration changes."""
        return len(self._diffs)

    def add_diff(self, diff: ConfigDiff) -> None:
        """Add a configuration diff to the report.

        Args:
            diff: ConfigDiff to add
        """
        self._diffs.append(diff)

    def get_all_diffs(self) -> list[ConfigDiff]:
        """Get all configuration diffs.

        Returns:
            List of all ConfigDiff objects
        """
        return self._diffs.copy()

    def get_diffs_by_category(self, category: ChangeCategory) -> list[ConfigDiff]:
        """Get diffs filtered by change category.

        Args:
            category: ChangeCategory to filter by

        Returns:
            List of diffs matching the category
        """
        return [d for d in self._diffs if d.category == category]

    def get_security_critical_diffs(self) -> list[ConfigDiff]:
        """Get diffs that affect security-critical settings.

        Returns:
            List of security-critical diffs
        """
        return [d for d in self._diffs if d.is_security_critical()]

    def get_diffs_by_resource(self, resource_arn: str) -> list[ConfigDiff]:
        """Get diffs for a specific resource ARN.

        Args:
            resource_arn: ARN of the resource

        Returns:
            List of diffs for the specified resource
        """
        return [d for d in self._diffs if d.resource_arn == resource_arn]

    def get_diffs_by_resource_type(self, resource_type: str) -> list[ConfigDiff]:
        """Get diffs filtered by resource type.

        Args:
            resource_type: Resource type to filter by (e.g., "ec2", "rds")

        Returns:
            List of diffs matching the resource type (case insensitive)
        """
        resource_type_lower = resource_type.lower()
        return [d for d in self._diffs if resource_type_lower in d.resource_arn.lower()]

    def get_diffs_by_region(self, region: str) -> list[ConfigDiff]:
        """Get diffs filtered by AWS region.

        Args:
            region: AWS region (e.g., "us-east-1")

        Returns:
            List of diffs in the specified region
        """
        return [d for d in self._diffs if region in d.resource_arn]

    def get_summary(self) -> dict[str, Any]:
        """Generate summary statistics for the drift report.

        Returns:
            Dictionary with total counts by category and security criticality
        """
        return {
            "total_changes": self.total_changes,
            "tags_count": len(self.get_diffs_by_category(ChangeCategory.TAGS)),
            "configuration_count": len(self.get_diffs_by_category(ChangeCategory.CONFIGURATION)),
            "security_count": len(self.get_diffs_by_category(ChangeCategory.SECURITY)),
            "permissions_count": len(self.get_diffs_by_category(ChangeCategory.PERMISSIONS)),
            "security_critical_count": len(self.get_security_critical_diffs()),
        }

    def group_by_resource(self) -> dict[str, list[ConfigDiff]]:
        """Group diffs by resource ARN.

        Returns:
            Dictionary mapping resource ARN to list of diffs
        """
        grouped: dict[str, list[ConfigDiff]] = {}
        for diff in self._diffs:
            if diff.resource_arn not in grouped:
                grouped[diff.resource_arn] = []
            grouped[diff.resource_arn].append(diff)
        return grouped

    def group_by_category(self) -> dict[ChangeCategory, list[ConfigDiff]]:
        """Group diffs by change category.

        Returns:
            Dictionary mapping ChangeCategory to list of diffs
        """
        grouped: dict[ChangeCategory, list[ConfigDiff]] = {}
        for diff in self._diffs:
            if diff.category not in grouped:
                grouped[diff.category] = []
            grouped[diff.category].append(diff)
        return grouped

    def has_security_critical_changes(self) -> bool:
        """Check if the report contains any security-critical changes.

        Returns:
            True if there are security-critical changes, False otherwise
        """
        return len(self.get_security_critical_diffs()) > 0

    def to_dict(self) -> dict[str, Any]:
        """Convert drift report to dictionary representation.

        Returns:
            Dictionary with all diffs and summary statistics
        """
        return {
            "total_changes": self.total_changes,
            "summary": self.get_summary(),
            "diffs": [diff.to_dict() for diff in self._diffs],
        }
