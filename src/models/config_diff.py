"""Configuration diff model for representing field-level changes between snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ChangeCategory(Enum):
    """Categories of configuration changes."""

    TAGS = "tags"
    CONFIGURATION = "configuration"
    SECURITY = "security"
    PERMISSIONS = "permissions"


# Security-critical field patterns that should be flagged
SECURITY_CRITICAL_FIELDS = {
    "PubliclyAccessible",
    "public",
    "encryption",
    "kms",
    "SecurityGroups",
    "IpPermissions",
    "IpPermissionsEgress",
    "Policy",
    "BucketPolicy",
    "Acl",
    "HttpTokens",  # IMDSv2
    "MetadataOptions",
}


@dataclass
class ConfigDiff:
    """Represents a field-level configuration change between two resource snapshots.

    Attributes:
        resource_arn: AWS ARN of the resource that changed
        field_path: Dot-notation path to the changed field (e.g., "Tags.Environment")
        old_value: Previous value of the field (None if field was added)
        new_value: New value of the field (None if field was removed)
        category: Category of the change (tags/configuration/security/permissions)
    """

    resource_arn: str
    field_path: str
    old_value: Any
    new_value: Any
    category: ChangeCategory

    def __post_init__(self) -> None:
        """Validate ConfigDiff fields after initialization."""
        # Validate ARN format (basic check)
        if not self.resource_arn or not self.resource_arn.startswith("arn:"):
            raise ValueError(f"Invalid ARN format: {self.resource_arn}")

        # Validate field_path is not empty
        if not self.field_path:
            raise ValueError("field_path cannot be empty")

        # Validate category is ChangeCategory enum
        if not isinstance(self.category, ChangeCategory):
            raise ValueError(f"Invalid category type: {type(self.category)}. Must be ChangeCategory enum.")

    def with_path_prefix(self, prefix: str) -> ConfigDiff:
        """Create a new ConfigDiff with a prefix added to the field path.

        Args:
            prefix: Prefix to add to the field path

        Returns:
            New ConfigDiff instance with prefixed field path
        """
        return ConfigDiff(
            resource_arn=self.resource_arn,
            field_path=f"{prefix}.{self.field_path}",
            old_value=self.old_value,
            new_value=self.new_value,
            category=self.category,
        )

    def is_security_critical(self) -> bool:
        """Check if this configuration change affects security-related settings.

        Returns:
            True if the change is security-critical, False otherwise
        """
        # Check if field path contains any security-critical keywords
        field_lower = self.field_path.lower()
        return any(keyword.lower() in field_lower for keyword in SECURITY_CRITICAL_FIELDS)

    def to_dict(self) -> dict[str, Any]:
        """Convert ConfigDiff to dictionary representation.

        Returns:
            Dictionary with all diff attributes
        """
        return {
            "resource_arn": self.resource_arn,
            "field_path": self.field_path,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "category": self.category.value,
            "security_critical": self.is_security_critical(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConfigDiff:
        """Create ConfigDiff from dictionary representation.

        Args:
            data: Dictionary with diff attributes

        Returns:
            ConfigDiff instance

        Raises:
            ValueError: If category value is invalid
        """
        category_str = data.get("category", "").lower()
        try:
            category = ChangeCategory(category_str)
        except ValueError:
            raise ValueError(f"Invalid category value: {category_str}")

        return cls(
            resource_arn=data["resource_arn"],
            field_path=data["field_path"],
            old_value=data["old_value"],
            new_value=data["new_value"],
            category=category,
        )
