"""Safety checks and protection rule evaluation.

Evaluates resources against protection rules to prevent accidental deletion.
"""

from __future__ import annotations

from typing import Optional

from src.models.protection_rule import ProtectionRule


class SafetyChecker:
    """Safety checker for resource protection evaluation.

    Evaluates resources against configured protection rules to determine if
    they should be protected from deletion. Supports multiple rule types
    (tag, type, age, cost, native) with priority-based evaluation.

    Attributes:
        rules: List of protection rules sorted by priority
    """

    def __init__(self, rules: list[ProtectionRule]) -> None:
        """Initialize safety checker.

        Args:
            rules: List of protection rules (sorted by priority, 1=highest)
        """
        self.rules = sorted(rules, key=lambda r: r.priority)

    def is_protected(self, resource: dict) -> tuple[bool, Optional[str]]:
        """Check if resource is protected by any rule.

        Evaluates resource against all enabled protection rules in priority order.
        Returns on first matching rule (highest priority wins).

        Args:
            resource: Resource metadata dictionary

        Returns:
            Tuple of (is_protected, reason)
                is_protected: True if resource matches any protection rule
                reason: Human-readable reason for protection, None if not protected
        """
        for rule in self.rules:
            if not rule.enabled:
                continue

            if rule.matches(resource):
                reason = self._get_protection_reason(rule, resource)
                return True, reason

        return False, None

    def check_all_protections(self, resource: dict) -> list[ProtectionRule]:
        """Check which protection rules match a resource.

        Unlike is_protected(), this returns ALL matching rules, not just the
        first one. Useful for detailed protection analysis.

        Args:
            resource: Resource metadata dictionary

        Returns:
            List of all matching protection rules
        """
        matching_rules = []

        for rule in self.rules:
            if not rule.enabled:
                continue

            if rule.matches(resource):
                matching_rules.append(rule)

        return matching_rules

    def _get_protection_reason(self, rule: ProtectionRule, resource: dict) -> str:
        """Generate human-readable protection reason.

        Args:
            rule: Protection rule that matched
            resource: Resource metadata

        Returns:
            Human-readable protection reason string
        """
        if rule.description:
            return f"{rule.description} (rule: {rule.rule_id})"

        # Generate default reason based on rule type
        if rule.rule_type.value == "tag":
            tag_key = rule.patterns.get("tag_key", "")
            resource_tag_value = resource.get("tags", {}).get(tag_key, "")
            return f"Tag {tag_key}={resource_tag_value} (rule: {rule.rule_id})"

        elif rule.rule_type.value == "type":
            resource_type = resource.get("resource_type", "")
            return f"Resource type {resource_type} protected (rule: {rule.rule_id})"

        elif rule.rule_type.value == "age":
            age_days = resource.get("age_days", 0)
            threshold = rule.threshold_value
            return f"Resource age {age_days} days < {threshold} days threshold (rule: {rule.rule_id})"

        elif rule.rule_type.value == "cost":
            cost = resource.get("estimated_monthly_cost", 0)
            threshold = rule.threshold_value
            return f"Resource cost ${cost}/month >= ${threshold} threshold (rule: {rule.rule_id})"

        elif rule.rule_type.value == "native":
            return f"Native protection enabled (rule: {rule.rule_id})"

        return f"Protected by rule {rule.rule_id}"
