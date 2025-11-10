"""Unit tests for CIS Benchmark mapper."""

from __future__ import annotations

from src.models.security_finding import SecurityFinding, Severity
from src.security.cis_mapper import CISMapper
from tests.fixtures.snapshots import create_s3_bucket


class TestCISMapper:
    """Tests for CISMapper."""

    def test_mapper_initializes(self) -> None:
        """Test that CIS mapper initializes."""
        mapper = CISMapper()
        assert mapper is not None

    def test_map_finding_to_cis_control(self) -> None:
        """Test mapping a security finding to CIS control."""
        finding = SecurityFinding(
            resource_arn="arn:aws:s3:::test-bucket",
            finding_type="s3_public_bucket",
            severity=Severity.CRITICAL,
            description="S3 bucket is publicly accessible",
            remediation="Enable block public access",
            cis_control="2.1.5",
        )

        mapper = CISMapper()
        control = mapper.get_cis_control(finding)

        assert control == "2.1.5"

    def test_get_cis_control_name(self) -> None:
        """Test getting CIS control human-readable name."""
        mapper = CISMapper()

        # CIS 2.1.5 is about S3 bucket public access
        control_name = mapper.get_control_name("2.1.5")

        assert control_name is not None
        assert len(control_name) > 0
        assert "s3" in control_name.lower() or "bucket" in control_name.lower()

    def test_calculate_pass_fail_counts(self) -> None:
        """Test calculating pass/fail counts for CIS controls."""
        bucket = create_s3_bucket("test-bucket", public=True)

        finding1 = SecurityFinding(
            resource_arn=bucket.arn,
            finding_type="s3_public_bucket",
            severity=Severity.CRITICAL,
            description="Test",
            remediation="Test",
            cis_control="2.1.5",
        )

        finding2 = SecurityFinding(
            resource_arn="arn:aws:ec2:us-east-1:123:security-group/sg-1",
            finding_type="security_group_open",
            severity=Severity.HIGH,
            description="Test",
            remediation="Test",
            cis_control="5.2",
        )

        findings = [finding1, finding2]
        mapper = CISMapper()

        summary = mapper.get_summary(findings)

        assert "total_controls_checked" in summary
        assert "controls_failed" in summary
        assert "controls_passed" in summary

        # Should have at least 2 controls checked (2.1.5 and 5.2)
        assert summary["total_controls_checked"] >= 2
        # Should have at least 2 failures
        assert summary["controls_failed"] >= 2

    def test_group_findings_by_control(self) -> None:
        """Test grouping findings by CIS control."""
        finding1 = SecurityFinding(
            resource_arn="arn:aws:s3:::bucket1",
            finding_type="s3_public_bucket",
            severity=Severity.CRITICAL,
            description="Test",
            remediation="Test",
            cis_control="2.1.5",
        )

        finding2 = SecurityFinding(
            resource_arn="arn:aws:s3:::bucket2",
            finding_type="s3_public_bucket",
            severity=Severity.CRITICAL,
            description="Test",
            remediation="Test",
            cis_control="2.1.5",
        )

        finding3 = SecurityFinding(
            resource_arn="arn:aws:ec2:us-east-1:123:sg/sg-1",
            finding_type="security_group_open",
            severity=Severity.HIGH,
            description="Test",
            remediation="Test",
            cis_control="5.2",
        )

        findings = [finding1, finding2, finding3]
        mapper = CISMapper()

        grouped = mapper.group_by_control(findings)

        # Should have 2 groups (2.1.5 and 5.2)
        assert len(grouped) == 2
        assert "2.1.5" in grouped
        assert "5.2" in grouped
        assert len(grouped["2.1.5"]) == 2  # Two S3 findings
        assert len(grouped["5.2"]) == 1  # One SG finding

    def test_findings_without_cis_control(self) -> None:
        """Test handling findings without CIS control mapping."""
        finding = SecurityFinding(
            resource_arn="arn:aws:custom:::resource",
            finding_type="custom_check",
            severity=Severity.LOW,
            description="Test",
            remediation="Test",
            cis_control=None,  # No CIS mapping
        )

        mapper = CISMapper()
        control = mapper.get_cis_control(finding)

        assert control is None

    def test_cis_summary_with_no_findings(self) -> None:
        """Test CIS summary with no findings."""
        mapper = CISMapper()
        summary = mapper.get_summary([])

        assert summary["total_controls_checked"] == 0
        assert summary["controls_failed"] == 0
        assert summary["controls_passed"] >= 0  # May have baseline checks
