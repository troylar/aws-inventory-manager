"""Tests for DependencyResolver class.

Test coverage for dependency graph construction and deletion ordering using Kahn's algorithm.
"""

from __future__ import annotations

import pytest

from src.restore.dependency import DependencyResolver


class TestDependencyResolver:
    """Test suite for DependencyResolver class."""

    def test_init_creates_empty_graph(self) -> None:
        """Test initialization creates empty dependency graph."""
        resolver = DependencyResolver()
        assert resolver.graph == {}

    def test_add_dependency_creates_edge(self) -> None:
        """Test adding dependency creates edge in graph."""
        resolver = DependencyResolver()

        # Add dependency: subnet depends on vpc (vpc must be deleted AFTER subnet)
        resolver.add_dependency(parent="vpc-001", child="subnet-001")

        assert "subnet-001" in resolver.graph
        assert "vpc-001" in resolver.graph["subnet-001"]

    def test_add_multiple_dependencies_for_same_child(self) -> None:
        """Test adding multiple parent dependencies for same child."""
        resolver = DependencyResolver()

        # EC2 instance depends on subnet AND security group
        resolver.add_dependency(parent="subnet-001", child="instance-001")
        resolver.add_dependency(parent="sg-001", child="instance-001")

        assert len(resolver.graph["instance-001"]) == 2
        assert "subnet-001" in resolver.graph["instance-001"]
        assert "sg-001" in resolver.graph["instance-001"]

    def test_compute_deletion_order_simple_chain(self) -> None:
        """Test deletion order for simple dependency chain."""
        resolver = DependencyResolver()

        # Chain: vpc -> subnet -> instance
        # Deletion order should be: instance, subnet, vpc
        resolver.add_dependency(parent="vpc-001", child="subnet-001")
        resolver.add_dependency(parent="subnet-001", child="instance-001")

        resources = ["vpc-001", "subnet-001", "instance-001"]
        order = resolver.compute_deletion_order(resources)

        # Instance must come before subnet, subnet before vpc
        assert order.index("instance-001") < order.index("subnet-001")
        assert order.index("subnet-001") < order.index("vpc-001")

    def test_compute_deletion_order_parallel_dependencies(self) -> None:
        """Test deletion order for parallel dependencies."""
        resolver = DependencyResolver()

        # Parallel: vpc has two subnets
        # Order: subnets first (any order), then vpc
        resolver.add_dependency(parent="vpc-001", child="subnet-001")
        resolver.add_dependency(parent="vpc-001", child="subnet-002")

        resources = ["vpc-001", "subnet-001", "subnet-002"]
        order = resolver.compute_deletion_order(resources)

        # Both subnets must come before vpc
        assert order.index("subnet-001") < order.index("vpc-001")
        assert order.index("subnet-002") < order.index("vpc-001")

    def test_compute_deletion_order_complex_graph(self) -> None:
        """Test deletion order for complex dependency graph."""
        resolver = DependencyResolver()

        # Complex:
        # vpc-001
        #   ├── subnet-001
        #   │   └── instance-001
        #   └── sg-001
        #       └── instance-001 (also depends on subnet)

        resolver.add_dependency(parent="vpc-001", child="subnet-001")
        resolver.add_dependency(parent="vpc-001", child="sg-001")
        resolver.add_dependency(parent="subnet-001", child="instance-001")
        resolver.add_dependency(parent="sg-001", child="instance-001")

        resources = ["vpc-001", "subnet-001", "sg-001", "instance-001"]
        order = resolver.compute_deletion_order(resources)

        # Instance must be first (depends on subnet and sg)
        assert order[0] == "instance-001"

        # VPC must be last (has no dependencies)
        assert order[-1] == "vpc-001"

        # Subnet and SG can be in any order, but after instance
        assert order.index("subnet-001") > order.index("instance-001")
        assert order.index("sg-001") > order.index("instance-001")

    def test_compute_deletion_order_no_dependencies(self) -> None:
        """Test deletion order when no dependencies exist."""
        resolver = DependencyResolver()

        # No dependencies - any order is valid
        resources = ["resource-001", "resource-002", "resource-003"]
        order = resolver.compute_deletion_order(resources)

        # All resources should be in result
        assert len(order) == 3
        assert set(order) == set(resources)

    def test_compute_deletion_order_partial_dependencies(self) -> None:
        """Test deletion order with only some resources having dependencies."""
        resolver = DependencyResolver()

        # Only instance-001 has dependency on subnet-001
        resolver.add_dependency(parent="subnet-001", child="instance-001")

        resources = ["subnet-001", "instance-001", "independent-resource"]
        order = resolver.compute_deletion_order(resources)

        # Instance must come before subnet
        assert order.index("instance-001") < order.index("subnet-001")

        # Independent resource can be anywhere
        assert "independent-resource" in order

    def test_detect_cycle_returns_false_for_acyclic_graph(self) -> None:
        """Test cycle detection returns False for acyclic graph."""
        resolver = DependencyResolver()

        resolver.add_dependency(parent="vpc-001", child="subnet-001")
        resolver.add_dependency(parent="subnet-001", child="instance-001")

        assert resolver.has_cycle() is False

    def test_detect_cycle_returns_true_for_circular_dependency(self) -> None:
        """Test cycle detection returns True for circular dependency."""
        resolver = DependencyResolver()

        # Create cycle: A -> B -> C -> A
        resolver.add_dependency(parent="resource-B", child="resource-A")
        resolver.add_dependency(parent="resource-C", child="resource-B")
        resolver.add_dependency(parent="resource-A", child="resource-C")

        assert resolver.has_cycle() is True

    def test_compute_deletion_order_raises_error_on_cycle(self) -> None:
        """Test deletion order computation raises error when cycle detected."""
        resolver = DependencyResolver()

        # Create cycle
        resolver.add_dependency(parent="resource-B", child="resource-A")
        resolver.add_dependency(parent="resource-A", child="resource-B")

        resources = ["resource-A", "resource-B"]

        with pytest.raises(ValueError, match="Circular dependency"):
            resolver.compute_deletion_order(resources)

    def test_build_graph_from_resources_detects_dependencies(self) -> None:
        """Test building graph from resource metadata automatically."""
        resources = [
            {
                "resource_id": "vpc-001",
                "resource_type": "AWS::EC2::VPC",
                "metadata": {},
            },
            {
                "resource_id": "subnet-001",
                "resource_type": "AWS::EC2::Subnet",
                "metadata": {"VpcId": "vpc-001"},
            },
            {
                "resource_id": "instance-001",
                "resource_type": "AWS::EC2::Instance",
                "metadata": {
                    "VpcId": "vpc-001",
                    "SubnetId": "subnet-001",
                },
            },
        ]

        resolver = DependencyResolver()
        resolver.build_graph_from_resources(resources)

        # Verify dependencies were detected
        assert "subnet-001" in resolver.graph
        assert "vpc-001" in resolver.graph["subnet-001"]

        assert "instance-001" in resolver.graph
        assert "subnet-001" in resolver.graph["instance-001"]

    def test_get_deletion_tiers_assigns_correct_tiers(self) -> None:
        """Test get_deletion_tiers assigns resources to correct tiers."""
        resolver = DependencyResolver()

        # Build graph
        resolver.add_dependency(parent="vpc-001", child="subnet-001")
        resolver.add_dependency(parent="subnet-001", child="instance-001")

        resources = ["vpc-001", "subnet-001", "instance-001"]
        tiers = resolver.get_deletion_tiers(resources)

        # Tier 1: No dependencies (instance)
        assert "instance-001" in tiers[1]

        # Tier 2: Depends on tier 1 (subnet)
        assert "subnet-001" in tiers[2]

        # Tier 3: Depends on tier 2 (vpc)
        assert "vpc-001" in tiers[3]
