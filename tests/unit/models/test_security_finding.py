"""Unit tests for SecurityFinding model."""

from __future__ import annotations

import pytest

from src.models.security_finding import SecurityFinding, Severity


class TestSeverity:
    """Tests for Severity enum."""

    def test_severity_values(self) -> None:
        """Test that Severity enum has correct values."""
        assert Severity.CRITICAL.value == "critical"
        assert Severity.HIGH.value == "high"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.LOW.value == "low"


class TestSecurityFinding:
    """Tests for SecurityFinding dataclass."""

    def test_create_valid_finding(self) -> None:
        """Test creating a valid security finding."""
        finding = SecurityFinding(
            resource_arn="arn:aws:s3:::my-bucket",
            finding_type="public_s3_bucket",
            severity=Severity.CRITICAL,
            description="S3 bucket is publicly accessible",
            remediation="Disable public access on the bucket",
        )

        assert finding.resource_arn == "arn:aws:s3:::my-bucket"
        assert finding.finding_type == "public_s3_bucket"
        assert finding.severity == Severity.CRITICAL
        assert finding.description == "S3 bucket is publicly accessible"
        assert finding.remediation == "Disable public access on the bucket"
        assert finding.cis_control is None
        assert finding.metadata is None

    def test_create_finding_with_cis_control(self) -> None:
        """Test creating a finding with CIS control mapping."""
        finding = SecurityFinding(
            resource_arn="arn:aws:s3:::my-bucket",
            finding_type="public_s3_bucket",
            severity=Severity.CRITICAL,
            description="S3 bucket is publicly accessible",
            remediation="Disable public access on the bucket",
            cis_control="2.1.5",
        )

        assert finding.cis_control == "2.1.5"

    def test_create_finding_with_metadata(self) -> None:
        """Test creating a finding with additional metadata."""
        metadata = {"port": 22, "cidr": "0.0.0.0/0"}
        finding = SecurityFinding(
            resource_arn="arn:aws:ec2:us-east-1:123456789012:security-group/sg-12345",
            finding_type="open_security_group",
            severity=Severity.HIGH,
            description="Security group allows SSH from anywhere",
            remediation="Restrict SSH access to specific IP ranges",
            metadata=metadata,
        )

        assert finding.metadata == metadata
        assert finding.metadata["port"] == 22  # type: ignore

    def test_invalid_arn_format(self) -> None:
        """Test that invalid ARN format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid ARN format"):
            SecurityFinding(
                resource_arn="not-an-arn",
                finding_type="public_s3_bucket",
                severity=Severity.CRITICAL,
                description="Test",
                remediation="Test",
            )

    def test_empty_arn(self) -> None:
        """Test that empty ARN raises ValueError."""
        with pytest.raises(ValueError, match="Invalid ARN format"):
            SecurityFinding(
                resource_arn="",
                finding_type="public_s3_bucket",
                severity=Severity.CRITICAL,
                description="Test",
                remediation="Test",
            )

    def test_invalid_severity_type(self) -> None:
        """Test that invalid severity type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid severity type"):
            SecurityFinding(
                resource_arn="arn:aws:s3:::my-bucket",
                finding_type="public_s3_bucket",
                severity="critical",  # type: ignore
                description="Test",
                remediation="Test",
            )

    def test_empty_finding_type(self) -> None:
        """Test that empty finding_type raises ValueError."""
        with pytest.raises(ValueError, match="finding_type cannot be empty"):
            SecurityFinding(
                resource_arn="arn:aws:s3:::my-bucket",
                finding_type="",
                severity=Severity.CRITICAL,
                description="Test",
                remediation="Test",
            )

    def test_empty_description(self) -> None:
        """Test that empty description raises ValueError."""
        with pytest.raises(ValueError, match="description cannot be empty"):
            SecurityFinding(
                resource_arn="arn:aws:s3:::my-bucket",
                finding_type="public_s3_bucket",
                severity=Severity.CRITICAL,
                description="",
                remediation="Test",
            )

    def test_empty_remediation(self) -> None:
        """Test that empty remediation raises ValueError."""
        with pytest.raises(ValueError, match="remediation cannot be empty"):
            SecurityFinding(
                resource_arn="arn:aws:s3:::my-bucket",
                finding_type="public_s3_bucket",
                severity=Severity.CRITICAL,
                description="Test",
                remediation="",
            )

    def test_to_dict(self) -> None:
        """Test converting SecurityFinding to dictionary."""
        metadata = {"port": 22}
        finding = SecurityFinding(
            resource_arn="arn:aws:s3:::my-bucket",
            finding_type="public_s3_bucket",
            severity=Severity.CRITICAL,
            description="S3 bucket is publicly accessible",
            remediation="Disable public access",
            cis_control="2.1.5",
            metadata=metadata,
        )

        result = finding.to_dict()

        assert result["resource_arn"] == "arn:aws:s3:::my-bucket"
        assert result["finding_type"] == "public_s3_bucket"
        assert result["severity"] == "critical"
        assert result["description"] == "S3 bucket is publicly accessible"
        assert result["remediation"] == "Disable public access"
        assert result["cis_control"] == "2.1.5"
        assert result["metadata"] == metadata

    def test_to_dict_without_optional_fields(self) -> None:
        """Test to_dict with no optional fields returns empty metadata."""
        finding = SecurityFinding(
            resource_arn="arn:aws:s3:::my-bucket",
            finding_type="public_s3_bucket",
            severity=Severity.HIGH,
            description="Test",
            remediation="Test",
        )

        result = finding.to_dict()

        assert result["cis_control"] is None
        assert result["metadata"] == {}

    def test_from_dict(self) -> None:
        """Test creating SecurityFinding from dictionary."""
        data = {
            "resource_arn": "arn:aws:s3:::my-bucket",
            "finding_type": "public_s3_bucket",
            "severity": "critical",
            "description": "S3 bucket is publicly accessible",
            "remediation": "Disable public access",
            "cis_control": "2.1.5",
            "metadata": {"port": 22},
        }

        finding = SecurityFinding.from_dict(data)

        assert finding.resource_arn == "arn:aws:s3:::my-bucket"
        assert finding.finding_type == "public_s3_bucket"
        assert finding.severity == Severity.CRITICAL
        assert finding.description == "S3 bucket is publicly accessible"
        assert finding.remediation == "Disable public access"
        assert finding.cis_control == "2.1.5"
        assert finding.metadata == {"port": 22}

    def test_from_dict_case_insensitive_severity(self) -> None:
        """Test that from_dict handles uppercase severity values."""
        data = {
            "resource_arn": "arn:aws:s3:::my-bucket",
            "finding_type": "test",
            "severity": "CRITICAL",
            "description": "Test",
            "remediation": "Test",
        }

        finding = SecurityFinding.from_dict(data)
        assert finding.severity == Severity.CRITICAL

    def test_from_dict_invalid_severity(self) -> None:
        """Test that from_dict raises ValueError for invalid severity."""
        data = {
            "resource_arn": "arn:aws:s3:::my-bucket",
            "finding_type": "test",
            "severity": "invalid",
            "description": "Test",
            "remediation": "Test",
        }

        with pytest.raises(ValueError, match="Invalid severity value: invalid"):
            SecurityFinding.from_dict(data)

    def test_from_dict_without_optional_fields(self) -> None:
        """Test creating SecurityFinding from dictionary without optional fields."""
        data = {
            "resource_arn": "arn:aws:s3:::my-bucket",
            "finding_type": "public_s3_bucket",
            "severity": "high",
            "description": "Test",
            "remediation": "Test",
        }

        finding = SecurityFinding.from_dict(data)

        assert finding.cis_control is None
        assert finding.metadata is None

    def test_round_trip_to_dict_from_dict(self) -> None:
        """Test that to_dict and from_dict are symmetric."""
        original = SecurityFinding(
            resource_arn="arn:aws:rds:us-east-1:123456789012:db:mydb",
            finding_type="public_rds",
            severity=Severity.HIGH,
            description="RDS instance is publicly accessible",
            remediation="Disable public accessibility",
            cis_control="2.3.1",
            metadata={"engine": "postgres"},
        )

        # Convert to dict and back
        data = original.to_dict()
        reconstructed = SecurityFinding.from_dict(data)

        # Compare all fields
        assert reconstructed.resource_arn == original.resource_arn
        assert reconstructed.finding_type == original.finding_type
        assert reconstructed.severity == original.severity
        assert reconstructed.description == original.description
        assert reconstructed.remediation == original.remediation
        assert reconstructed.cis_control == original.cis_control
        assert reconstructed.metadata == original.metadata
