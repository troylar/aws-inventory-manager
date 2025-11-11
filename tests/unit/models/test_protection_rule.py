"""Tests for ProtectionRule model.

Test coverage for protection rule configuration with type-specific patterns.
"""

from __future__ import annotations

import pytest

from src.models.protection_rule import ProtectionRule, RuleType


class TestProtectionRule:
    """Test suite for ProtectionRule model."""

    def test_create_tag_rule(self) -> None:
        """Test creating tag-based protection rule."""
        rule = ProtectionRule(
            rule_id="rule_001",
            rule_type=RuleType.TAG,
            enabled=True,
            priority=1,
            patterns={
                "tag_key": "Protection",
                "tag_values": ["true", "critical"],
                "match_mode": "exact",
            },
            description="Protect resources with Protection tag",
        )

        assert rule.rule_id == "rule_001"
        assert rule.rule_type == RuleType.TAG
        assert rule.enabled is True
        assert rule.priority == 1
        assert rule.patterns["tag_key"] == "Protection"
        assert rule.description == "Protect resources with Protection tag"

    def test_create_type_rule(self) -> None:
        """Test creating type-based protection rule."""
        rule = ProtectionRule(
            rule_id="rule_002",
            rule_type=RuleType.TYPE,
            enabled=True,
            priority=2,
            patterns={
                "resource_types": ["AWS::IAM::Role", "AWS::KMS::Key"],
                "match_mode": "exact",
            },
        )

        assert rule.rule_type == RuleType.TYPE
        assert "AWS::IAM::Role" in rule.patterns["resource_types"]

    def test_create_age_rule(self) -> None:
        """Test creating age-based protection rule."""
        rule = ProtectionRule(
            rule_id="rule_003",
            rule_type=RuleType.AGE,
            enabled=True,
            priority=3,
            patterns={"environment": "production"},
            threshold_value=30.0,
            description="Production resources must be 30+ days old",
        )

        assert rule.rule_type == RuleType.AGE
        assert rule.threshold_value == 30.0

    def test_create_cost_rule(self) -> None:
        """Test creating cost-based protection rule."""
        rule = ProtectionRule(
            rule_id="rule_004",
            rule_type=RuleType.COST,
            enabled=True,
            priority=4,
            patterns={"action": "block"},
            threshold_value=5000.0,
            description="Block deletion of resources >$5000/month",
        )

        assert rule.rule_type == RuleType.COST
        assert rule.threshold_value == 5000.0

    def test_create_native_rule(self) -> None:
        """Test creating native protection rule."""
        rule = ProtectionRule(
            rule_id="rule_005",
            rule_type=RuleType.NATIVE,
            enabled=True,
            priority=5,
            patterns={
                "protection_types": [
                    "ec2_termination_protection",
                    "rds_deletion_protection",
                ]
            },
        )

        assert rule.rule_type == RuleType.NATIVE
        assert "ec2_termination_protection" in rule.patterns["protection_types"]

    def test_validate_age_rule_requires_threshold(self) -> None:
        """Test validation fails for age rule without threshold."""
        rule = ProtectionRule(
            rule_id="rule_invalid",
            rule_type=RuleType.AGE,
            enabled=True,
            priority=1,
            patterns={"environment": "production"},
            # Missing threshold_value!
        )

        with pytest.raises(ValueError, match="age rule requires positive threshold"):
            rule.validate()

    def test_validate_cost_rule_requires_threshold(self) -> None:
        """Test validation fails for cost rule without threshold."""
        rule = ProtectionRule(
            rule_id="rule_invalid",
            rule_type=RuleType.COST,
            enabled=True,
            priority=1,
            patterns={"action": "block"},
            # Missing threshold_value!
        )

        with pytest.raises(ValueError, match="cost rule requires positive threshold"):
            rule.validate()

    def test_validate_negative_threshold_raises_error(self) -> None:
        """Test validation fails for negative threshold."""
        rule = ProtectionRule(
            rule_id="rule_negative",
            rule_type=RuleType.AGE,
            enabled=True,
            priority=1,
            patterns={"environment": "test"},
            threshold_value=-10.0,  # Invalid!
        )

        with pytest.raises(ValueError, match="requires positive threshold"):
            rule.validate()

    def test_validate_empty_patterns_raises_error(self) -> None:
        """Test validation fails for empty patterns."""
        rule = ProtectionRule(
            rule_id="rule_empty",
            rule_type=RuleType.TAG,
            enabled=True,
            priority=1,
            patterns={},  # Empty!
        )

        with pytest.raises(ValueError, match="Patterns cannot be empty"):
            rule.validate()

    def test_validate_priority_range(self) -> None:
        """Test validation checks priority range 1-100."""
        rule_low = ProtectionRule(
            rule_id="rule_low",
            rule_type=RuleType.TAG,
            enabled=True,
            priority=0,  # Too low!
            patterns={"tag_key": "Test"},
        )

        with pytest.raises(ValueError, match="Priority must be 1-100"):
            rule_low.validate()

        rule_high = ProtectionRule(
            rule_id="rule_high",
            rule_type=RuleType.TAG,
            enabled=True,
            priority=101,  # Too high!
            patterns={"tag_key": "Test"},
        )

        with pytest.raises(ValueError, match="Priority must be 1-100"):
            rule_high.validate()

    def test_validate_valid_priority_range(self) -> None:
        """Test validation passes for valid priority range."""
        rule_min = ProtectionRule(
            rule_id="rule_min",
            rule_type=RuleType.TAG,
            enabled=True,
            priority=1,
            patterns={"tag_key": "Test"},
        )
        assert rule_min.validate() is True

        rule_max = ProtectionRule(
            rule_id="rule_max",
            rule_type=RuleType.TAG,
            enabled=True,
            priority=100,
            patterns={"tag_key": "Test"},
        )
        assert rule_max.validate() is True

    def test_matches_tag_rule(self) -> None:
        """Test tag rule matching logic."""
        rule = ProtectionRule(
            rule_id="rule_tag",
            rule_type=RuleType.TAG,
            enabled=True,
            priority=1,
            patterns={
                "tag_key": "Protection",
                "tag_values": ["true", "critical"],
                "match_mode": "exact",
            },
        )

        # Should match
        protected_resource = {
            "resource_id": "i-001",
            "tags": {"Protection": "true", "Environment": "prod"},
        }
        assert rule.matches(protected_resource) is True

        # Should not match
        unprotected_resource = {
            "resource_id": "i-002",
            "tags": {"Protection": "false"},
        }
        assert rule.matches(unprotected_resource) is False

        # Missing tag
        no_tag_resource = {
            "resource_id": "i-003",
            "tags": {"Environment": "dev"},
        }
        assert rule.matches(no_tag_resource) is False

    def test_matches_type_rule(self) -> None:
        """Test type rule matching logic."""
        rule = ProtectionRule(
            rule_id="rule_type",
            rule_type=RuleType.TYPE,
            enabled=True,
            priority=1,
            patterns={
                "resource_types": ["AWS::IAM::Role", "AWS::KMS::Key"],
            },
        )

        # Should match
        iam_resource = {
            "resource_id": "role-admin",
            "resource_type": "AWS::IAM::Role",
        }
        assert rule.matches(iam_resource) is True

        # Should not match
        ec2_resource = {
            "resource_id": "i-001",
            "resource_type": "AWS::EC2::Instance",
        }
        assert rule.matches(ec2_resource) is False

    def test_matches_age_rule(self) -> None:
        """Test age rule matching logic."""
        rule = ProtectionRule(
            rule_id="rule_age",
            rule_type=RuleType.AGE,
            enabled=True,
            priority=1,
            patterns={"environment": "production"},
            threshold_value=30.0,
        )

        # Too young (protected)
        young_resource = {
            "resource_id": "i-001",
            "age_days": 15,
        }
        assert rule.matches(young_resource) is True

        # Old enough (not protected)
        old_resource = {
            "resource_id": "i-002",
            "age_days": 45,
        }
        assert rule.matches(old_resource) is False

    def test_matches_cost_rule(self) -> None:
        """Test cost rule matching logic."""
        rule = ProtectionRule(
            rule_id="rule_cost",
            rule_type=RuleType.COST,
            enabled=True,
            priority=1,
            patterns={"action": "block"},
            threshold_value=5000.0,
        )

        # High cost (protected)
        expensive_resource = {
            "resource_id": "db-prod",
            "estimated_monthly_cost": 6000.0,
        }
        assert rule.matches(expensive_resource) is True

        # Low cost (not protected)
        cheap_resource = {
            "resource_id": "i-test",
            "estimated_monthly_cost": 10.0,
        }
        assert rule.matches(cheap_resource) is False

    def test_matches_disabled_rule_always_false(self) -> None:
        """Test disabled rule never matches."""
        rule = ProtectionRule(
            rule_id="rule_disabled",
            rule_type=RuleType.TAG,
            enabled=False,  # Disabled!
            priority=1,
            patterns={
                "tag_key": "Protection",
                "tag_values": ["true"],
            },
        )

        resource = {
            "resource_id": "i-001",
            "tags": {"Protection": "true"},
        }

        # Even though it matches pattern, disabled rule returns False
        assert rule.matches(resource) is False


class TestRuleType:
    """Test RuleType enum."""

    def test_rule_type_values(self) -> None:
        """Test rule type enum values."""
        assert RuleType.TAG.value == "tag"
        assert RuleType.TYPE.value == "type"
        assert RuleType.AGE.value == "age"
        assert RuleType.COST.value == "cost"
        assert RuleType.NATIVE.value == "native"

    def test_rule_type_from_string(self) -> None:
        """Test creating rule type from string value."""
        assert RuleType("tag") == RuleType.TAG
        assert RuleType("type") == RuleType.TYPE
        assert RuleType("age") == RuleType.AGE
        assert RuleType("cost") == RuleType.COST
        assert RuleType("native") == RuleType.NATIVE
