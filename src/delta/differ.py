"""Configuration differ for recursive comparison of resource configurations."""

from __future__ import annotations

from typing import Any

from ..models.config_diff import SECURITY_CRITICAL_FIELDS, ChangeCategory, ConfigDiff


class ConfigDiffer:
    """Recursive configuration comparison engine.

    Compares two resource configuration dictionaries and produces a list
    of ConfigDiff objects representing field-level changes.
    """

    def __init__(self) -> None:
        """Initialize the configuration differ."""
        pass

    def compare(
        self,
        resource_arn: str,
        old_config: dict[str, Any],
        new_config: dict[str, Any],
        field_prefix: str = "",
    ) -> list[ConfigDiff]:
        """Recursively compare two configuration dictionaries.

        Args:
            resource_arn: ARN of the resource being compared
            old_config: Previous configuration
            new_config: Current configuration
            field_prefix: Dot-notation prefix for nested fields (internal use)

        Returns:
            List of ConfigDiff objects representing changes
        """
        diffs: list[ConfigDiff] = []

        # Get all unique keys from both configs
        all_keys = set(old_config.keys()) | set(new_config.keys())

        for key in all_keys:
            field_path = f"{field_prefix}.{key}" if field_prefix else key

            old_value = old_config.get(key)
            new_value = new_config.get(key)

            # Skip if values are identical
            if old_value == new_value:
                continue

            # Recursively compare nested dictionaries
            if isinstance(old_value, dict) and isinstance(new_value, dict):
                nested_diffs = self.compare(resource_arn, old_value, new_value, field_path)
                diffs.extend(nested_diffs)
            # Recursively compare lists
            elif isinstance(old_value, list) and isinstance(new_value, list):
                list_diffs = self._compare_lists(resource_arn, old_value, new_value, field_path)
                diffs.extend(list_diffs)
            # Handle nested dict in old but not in new (or vice versa)
            elif isinstance(old_value, dict) and not isinstance(new_value, dict):
                # Dict was replaced with non-dict or removed
                category = self._categorize_change(field_path, resource_arn)
                diff = ConfigDiff(
                    resource_arn=resource_arn,
                    field_path=field_path,
                    old_value=old_value,
                    new_value=new_value,
                    category=category,
                )
                diffs.append(diff)
            elif isinstance(new_value, dict) and not isinstance(old_value, dict):
                # Dict was added or replaced
                category = self._categorize_change(field_path, resource_arn)
                diff = ConfigDiff(
                    resource_arn=resource_arn,
                    field_path=field_path,
                    old_value=old_value,
                    new_value=new_value,
                    category=category,
                )
                diffs.append(diff)
            else:
                # Simple value change, addition, or removal
                category = self._categorize_change(field_path, resource_arn)
                diff = ConfigDiff(
                    resource_arn=resource_arn,
                    field_path=field_path,
                    old_value=old_value,
                    new_value=new_value,
                    category=category,
                )
                diffs.append(diff)

        return diffs

    def _compare_lists(
        self,
        resource_arn: str,
        old_list: list[Any],
        new_list: list[Any],
        field_path: str,
    ) -> list[ConfigDiff]:
        """Compare two lists element by element.

        Args:
            resource_arn: ARN of the resource
            old_list: Previous list
            new_list: Current list
            field_path: Field path for the list

        Returns:
            List of ConfigDiff objects for list changes
        """
        diffs: list[ConfigDiff] = []

        max_len = max(len(old_list), len(new_list))

        for i in range(max_len):
            element_path = f"{field_path}.{i}"

            old_value = old_list[i] if i < len(old_list) else None
            new_value = new_list[i] if i < len(new_list) else None

            if old_value == new_value:
                continue

            # Recursively compare nested dicts in lists
            if isinstance(old_value, dict) and isinstance(new_value, dict):
                nested_diffs = self.compare(resource_arn, old_value, new_value, element_path)
                diffs.extend(nested_diffs)
            else:
                # Simple value change
                category = self._categorize_change(element_path, resource_arn)
                diff = ConfigDiff(
                    resource_arn=resource_arn,
                    field_path=element_path,
                    old_value=old_value,
                    new_value=new_value,
                    category=category,
                )
                diffs.append(diff)

        return diffs

    def _categorize_change(self, field_path: str, resource_arn: str) -> ChangeCategory:
        """Categorize a configuration change based on field path and resource type.

        Args:
            field_path: Dot-notation field path
            resource_arn: ARN of the resource

        Returns:
            ChangeCategory enum value
        """
        field_lower = field_path.lower()
        arn_lower = resource_arn.lower()

        # Check for Tags category
        if "tags" in field_lower or field_path.startswith("Tags."):
            return ChangeCategory.TAGS

        # Check for Permissions category (IAM-related) - do this BEFORE security check
        # because some IAM fields like "Policy" could match security keywords
        permissions_keywords = [
            "policy",
            "permission",
            "role",
            "assumerolepolicydocument",
            "statement",
        ]
        if "iam" in arn_lower:
            # For IAM resources, policy/permission changes are PERMISSIONS
            if any(keyword in field_lower for keyword in permissions_keywords):
                return ChangeCategory.PERMISSIONS

        # Check for Security category
        for security_field in SECURITY_CRITICAL_FIELDS:
            if security_field.lower() in field_lower:
                return ChangeCategory.SECURITY

        # Default to Configuration
        return ChangeCategory.CONFIGURATION
