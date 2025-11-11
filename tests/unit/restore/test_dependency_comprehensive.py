"""Comprehensive tests for DependencyResolver class.

Test coverage for dependency graph building and topological sort.
"""

from __future__ import annotations

import pytest

from src.restore.dependency import DependencyResolver


class TestDependencyResolverBasic:
    """Basic tests for DependencyResolver."""

    def test_init_creates_empty_graph(self) -> None:
        """Test initialization creates empty dependency graph."""
        resolver = DependencyResolver()
        assert resolver.graph == {}

    def test_add_dependency_creates_parent_child_relationship(self) -> None:
        """Test adding dependency creates correct relationship."""
        resolver = DependencyResolver()
        resolver.add_dependency(parent="vpc-123", child="subnet-456")

        assert "subnet-456" in resolver.graph
        assert "vpc-123" in resolver.graph["subnet-456"]
        assert "vpc-123" in resolver.graph

    def test_add_dependency_prevents_duplicates(self) -> None:
        """Test adding same dependency twice doesn't create duplicates."""
        resolver = DependencyResolver()
        resolver.add_dependency(parent="vpc-123", child="subnet-456")
        resolver.add_dependency(parent="vpc-123", child="subnet-456")

        assert resolver.graph["subnet-456"].count("vpc-123") == 1

    def test_add_dependency_allows_multiple_parents(self) -> None:
        """Test child can have multiple parents."""
        resolver = DependencyResolver()
        resolver.add_dependency(parent="vpc-123", child="instance-789")
        resolver.add_dependency(parent="sg-456", child="instance-789")

        assert len(resolver.graph["instance-789"]) == 2
        assert "vpc-123" in resolver.graph["instance-789"]
        assert "sg-456" in resolver.graph["instance-789"]


class TestDependencyResolverGraphBuilding:
    """Tests for automatic graph building from resource metadata."""

    def test_build_graph_from_ec2_instance(self) -> None:
        """Test building dependency graph from EC2 instance."""
        resolver = DependencyResolver()
        resources = [
            {
                "resource_id": "vpc-123",
                "resource_type": "AWS::EC2::VPC",
                "metadata": {},
            },
            {
                "resource_id": "subnet-456",
                "resource_type": "AWS::EC2::Subnet",
                "metadata": {"VpcId": "vpc-123"},
            },
            {
                "resource_id": "instance-789",
                "resource_type": "AWS::EC2::Instance",
                "metadata": {
                    "VpcId": "vpc-123",
                    "SubnetId": "subnet-456",
                },
            },
        ]

        resolver.build_graph_from_resources(resources)

        # Instance depends on VPC and Subnet
        assert "vpc-123" in resolver.graph["instance-789"]
        assert "subnet-456" in resolver.graph["instance-789"]
        # Subnet depends on VPC
        assert "vpc-123" in resolver.graph["subnet-456"]

    def test_build_graph_handles_security_group_list(self) -> None:
        """Test building graph with list values (SecurityGroupIds)."""
        resolver = DependencyResolver()
        resources = [
            {"resource_id": "sg-111", "resource_type": "AWS::EC2::SecurityGroup", "metadata": {}},
            {"resource_id": "sg-222", "resource_type": "AWS::EC2::SecurityGroup", "metadata": {}},
            {
                "resource_id": "instance-789",
                "resource_type": "AWS::EC2::Instance",
                "metadata": {"SecurityGroupIds": ["sg-111", "sg-222"]},
            },
        ]

        resolver.build_graph_from_resources(resources)

        # Instance depends on both security groups
        assert "sg-111" in resolver.graph["instance-789"]
        assert "sg-222" in resolver.graph["instance-789"]

    def test_build_graph_ignores_missing_dependencies(self) -> None:
        """Test graph building ignores references to non-existent resources."""
        resolver = DependencyResolver()
        resources = [
            {
                "resource_id": "instance-789",
                "resource_type": "AWS::EC2::Instance",
                "metadata": {"VpcId": "vpc-nonexistent"},
            },
        ]

        resolver.build_graph_from_resources(resources)

        # No dependencies should be added since vpc-nonexistent doesn't exist
        # Instance won't be in graph since it has no valid dependencies
        assert "instance-789" not in resolver.graph
        assert "vpc-nonexistent" not in resolver.graph

    def test_build_graph_handles_nested_fields(self) -> None:
        """Test graph building handles nested metadata fields."""
        resolver = DependencyResolver()
        resources = [
            {"resource_id": "subnet-456", "resource_type": "AWS::EC2::Subnet", "metadata": {}},
            {
                "resource_id": "lambda-123",
                "resource_type": "AWS::Lambda::Function",
                "metadata": {"VpcConfig": {"SubnetIds": ["subnet-456"]}},
            },
        ]

        resolver.build_graph_from_resources(resources)

        # Lambda depends on subnet
        assert "subnet-456" in resolver.graph["lambda-123"]

    def test_build_graph_with_no_dependencies(self) -> None:
        """Test building graph for resource with no dependencies."""
        resolver = DependencyResolver()
        resources = [
            {"resource_id": "vpc-123", "resource_type": "AWS::EC2::VPC", "metadata": {}},
        ]

        resolver.build_graph_from_resources(resources)

        # VPC has no dependency fields defined (DEPENDENCY_FIELDS["AWS::EC2::VPC"] = [])
        # So it won't be added to the graph at all
        assert "vpc-123" not in resolver.graph


class TestDependencyResolverDeletionOrder:
    """Tests for computing deletion order using topological sort."""

    def test_compute_deletion_order_simple_chain(self) -> None:
        """Test deletion order for simple dependency chain."""
        resolver = DependencyResolver()
        resolver.add_dependency(parent="vpc-123", child="subnet-456")
        resolver.add_dependency(parent="subnet-456", child="instance-789")

        order = resolver.compute_deletion_order(["vpc-123", "subnet-456", "instance-789"])

        # Instance must be deleted before subnet, subnet before vpc
        instance_idx = order.index("instance-789")
        subnet_idx = order.index("subnet-456")
        vpc_idx = order.index("vpc-123")

        assert instance_idx < subnet_idx < vpc_idx

    def test_compute_deletion_order_with_independent_resources(self) -> None:
        """Test deletion order with independent resources."""
        resolver = DependencyResolver()
        resolver.add_dependency(parent="vpc-123", child="subnet-456")

        # Add independent resource
        order = resolver.compute_deletion_order(["vpc-123", "subnet-456", "s3-bucket-789"])

        # Subnet must be before VPC
        subnet_idx = order.index("subnet-456")
        vpc_idx = order.index("vpc-123")
        assert subnet_idx < vpc_idx

        # S3 bucket can be anywhere (no dependencies)
        assert "s3-bucket-789" in order

    def test_compute_deletion_order_diamond_dependency(self) -> None:
        """Test deletion order with diamond-shaped dependencies."""
        resolver = DependencyResolver()
        # Instance -> Subnet -> VPC
        # Instance -> SecurityGroup -> VPC
        resolver.add_dependency(parent="vpc-123", child="subnet-456")
        resolver.add_dependency(parent="vpc-123", child="sg-789")
        resolver.add_dependency(parent="subnet-456", child="instance-111")
        resolver.add_dependency(parent="sg-789", child="instance-111")

        order = resolver.compute_deletion_order(["vpc-123", "subnet-456", "sg-789", "instance-111"])

        # Instance must be deleted first
        instance_idx = order.index("instance-111")
        subnet_idx = order.index("subnet-456")
        sg_idx = order.index("sg-789")
        vpc_idx = order.index("vpc-123")

        # Instance before both subnet and sg
        assert instance_idx < subnet_idx
        assert instance_idx < sg_idx
        # Both subnet and sg before vpc
        assert subnet_idx < vpc_idx
        assert sg_idx < vpc_idx

    def test_compute_deletion_order_detects_cycle(self) -> None:
        """Test that circular dependencies are detected."""
        resolver = DependencyResolver()
        resolver.add_dependency(parent="a", child="b")
        resolver.add_dependency(parent="b", child="c")
        resolver.add_dependency(parent="c", child="a")  # Creates cycle

        with pytest.raises(ValueError, match="Circular dependency"):
            resolver.compute_deletion_order(["a", "b", "c"])

    def test_compute_deletion_order_empty_list(self) -> None:
        """Test deletion order with empty resource list."""
        resolver = DependencyResolver()
        order = resolver.compute_deletion_order([])
        assert order == []

    def test_compute_deletion_order_single_resource(self) -> None:
        """Test deletion order with single resource."""
        resolver = DependencyResolver()
        order = resolver.compute_deletion_order(["vpc-123"])
        assert order == ["vpc-123"]


class TestDependencyResolverCycleDetection:
    """Tests for cycle detection in dependency graph."""

    def test_has_cycle_returns_false_for_acyclic_graph(self) -> None:
        """Test cycle detection on acyclic graph."""
        resolver = DependencyResolver()
        resolver.add_dependency(parent="vpc-123", child="subnet-456")
        resolver.add_dependency(parent="subnet-456", child="instance-789")

        assert resolver.has_cycle() is False

    def test_has_cycle_returns_true_for_simple_cycle(self) -> None:
        """Test cycle detection on simple cycle."""
        resolver = DependencyResolver()
        resolver.add_dependency(parent="a", child="b")
        resolver.add_dependency(parent="b", child="a")

        assert resolver.has_cycle() is True

    def test_has_cycle_returns_true_for_indirect_cycle(self) -> None:
        """Test cycle detection on indirect cycle."""
        resolver = DependencyResolver()
        resolver.add_dependency(parent="a", child="b")
        resolver.add_dependency(parent="b", child="c")
        resolver.add_dependency(parent="c", child="d")
        resolver.add_dependency(parent="d", child="a")  # Creates cycle

        assert resolver.has_cycle() is True

    def test_has_cycle_returns_false_for_empty_graph(self) -> None:
        """Test cycle detection on empty graph."""
        resolver = DependencyResolver()
        assert resolver.has_cycle() is False

    def test_has_cycle_handles_multiple_components(self) -> None:
        """Test cycle detection with multiple disconnected components."""
        resolver = DependencyResolver()
        # Component 1 (acyclic)
        resolver.add_dependency(parent="a", child="b")
        # Component 2 (has cycle)
        resolver.add_dependency(parent="x", child="y")
        resolver.add_dependency(parent="y", child="x")

        assert resolver.has_cycle() is True


class TestDependencyResolverDeletionTiers:
    """Tests for organizing resources into deletion tiers."""

    def test_get_deletion_tiers_simple_chain(self) -> None:
        """Test tier assignment for simple chain."""
        resolver = DependencyResolver()
        resolver.add_dependency(parent="vpc-123", child="subnet-456")
        resolver.add_dependency(parent="subnet-456", child="instance-789")

        tiers = resolver.get_deletion_tiers(["vpc-123", "subnet-456", "instance-789"])

        # Instance has no dependencies (tier 1)
        assert "instance-789" in tiers[1]
        # Subnet depends on instance (tier 2)
        assert "subnet-456" in tiers[2]
        # VPC depends on subnet (tier 3)
        assert "vpc-123" in tiers[3]

    def test_get_deletion_tiers_multiple_in_same_tier(self) -> None:
        """Test tier assignment with multiple resources in same tier."""
        resolver = DependencyResolver()
        resolver.add_dependency(parent="vpc-123", child="instance-1")
        resolver.add_dependency(parent="vpc-123", child="instance-2")

        tiers = resolver.get_deletion_tiers(["vpc-123", "instance-1", "instance-2"])

        # Both instances in tier 1 (no dependencies)
        assert "instance-1" in tiers[1]
        assert "instance-2" in tiers[1]
        # VPC in tier 2
        assert "vpc-123" in tiers[2]

    def test_get_deletion_tiers_diamond_dependency(self) -> None:
        """Test tier assignment with diamond dependencies."""
        resolver = DependencyResolver()
        resolver.add_dependency(parent="vpc-123", child="subnet-456")
        resolver.add_dependency(parent="vpc-123", child="sg-789")
        resolver.add_dependency(parent="subnet-456", child="instance-111")
        resolver.add_dependency(parent="sg-789", child="instance-111")

        tiers = resolver.get_deletion_tiers(["vpc-123", "subnet-456", "sg-789", "instance-111"])

        # Instance in tier 1
        assert "instance-111" in tiers[1]
        # Subnet and SG in tier 2
        assert "subnet-456" in tiers[2]
        assert "sg-789" in tiers[2]
        # VPC in tier 3
        assert "vpc-123" in tiers[3]

    def test_get_deletion_tiers_independent_resources(self) -> None:
        """Test tier assignment with independent resources."""
        resolver = DependencyResolver()
        tiers = resolver.get_deletion_tiers(["s3-bucket-1", "s3-bucket-2", "lambda-func"])

        # All independent resources in tier 1
        assert len(tiers[1]) == 3
        assert "s3-bucket-1" in tiers[1]
        assert "s3-bucket-2" in tiers[1]
        assert "lambda-func" in tiers[1]

    def test_get_deletion_tiers_empty_resources(self) -> None:
        """Test tier assignment with no resources."""
        resolver = DependencyResolver()
        tiers = resolver.get_deletion_tiers([])
        assert tiers == {}


class TestDependencyResolverNestedFields:
    """Tests for handling nested metadata fields."""

    def test_get_nested_field_single_level(self) -> None:
        """Test getting single-level field."""
        resolver = DependencyResolver()
        metadata = {"VpcId": "vpc-123"}
        value = resolver._get_nested_field(metadata, "VpcId")
        assert value == "vpc-123"

    def test_get_nested_field_nested_level(self) -> None:
        """Test getting nested field."""
        resolver = DependencyResolver()
        metadata = {"VpcConfig": {"SubnetIds": ["subnet-1", "subnet-2"]}}
        value = resolver._get_nested_field(metadata, "VpcConfig.SubnetIds")
        assert value == ["subnet-1", "subnet-2"]

    def test_get_nested_field_missing_returns_none(self) -> None:
        """Test getting non-existent field returns None."""
        resolver = DependencyResolver()
        metadata = {"VpcId": "vpc-123"}
        value = resolver._get_nested_field(metadata, "SubnetId")
        assert value is None

    def test_get_nested_field_partial_path_returns_none(self) -> None:
        """Test getting partially valid path returns None."""
        resolver = DependencyResolver()
        metadata = {"VpcConfig": {"SubnetIds": ["subnet-1"]}}
        value = resolver._get_nested_field(metadata, "VpcConfig.InvalidField")
        assert value is None

    def test_get_nested_field_non_dict_returns_none(self) -> None:
        """Test getting field from non-dict value returns None."""
        resolver = DependencyResolver()
        metadata = {"Value": "string-value"}
        value = resolver._get_nested_field(metadata, "Value.SubField")
        assert value is None


class TestDependencyResolverRDSResources:
    """Tests for RDS-specific dependency handling."""

    def test_build_graph_from_rds_instance(self) -> None:
        """Test building dependency graph from RDS instance."""
        resolver = DependencyResolver()
        resources = [
            {"resource_id": "subnet-group", "resource_type": "AWS::RDS::DBSubnetGroup", "metadata": {}},
            {"resource_id": "sg-123", "resource_type": "AWS::EC2::SecurityGroup", "metadata": {}},
            {
                "resource_id": "rds-instance",
                "resource_type": "AWS::RDS::DBInstance",
                "metadata": {
                    "DBSubnetGroupName": "subnet-group",
                    "VpcSecurityGroupIds": ["sg-123"],
                },
            },
        ]

        resolver.build_graph_from_resources(resources)

        # RDS depends on subnet group and security group
        assert "subnet-group" in resolver.graph["rds-instance"]
        assert "sg-123" in resolver.graph["rds-instance"]


class TestDependencyResolverECSResources:
    """Tests for ECS-specific dependency handling."""

    def test_build_graph_from_ecs_service(self) -> None:
        """Test building dependency graph from ECS service."""
        resolver = DependencyResolver()
        resources = [
            {"resource_id": "cluster-123", "resource_type": "AWS::ECS::Cluster", "metadata": {}},
            {"resource_id": "tg-456", "resource_type": "AWS::ElasticLoadBalancingV2::TargetGroup", "metadata": {}},
            {
                "resource_id": "service-789",
                "resource_type": "AWS::ECS::Service",
                "metadata": {
                    "Cluster": "cluster-123",
                    "LoadBalancers": [{"TargetGroupArn": "tg-456"}],
                },
            },
        ]

        resolver.build_graph_from_resources(resources)

        # Service depends on cluster
        assert "cluster-123" in resolver.graph["service-789"]
