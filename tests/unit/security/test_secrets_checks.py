"""Unit tests for Secrets Manager security checks."""

from __future__ import annotations

from src.models.security_finding import Severity
from src.security.checks.secrets_checks import SecretsRotationCheck
from tests.fixtures.snapshots import create_mock_snapshot, create_secrets_manager_secret


class TestSecretsRotationCheck:
    """Tests for SecretsRotationCheck."""

    def test_check_id_and_severity(self) -> None:
        """Test that check has correct ID and severity."""
        check = SecretsRotationCheck()
        assert check.check_id == "secrets_rotation_age"
        assert check.severity == Severity.MEDIUM

    def test_detect_secret_not_rotated_90_days(self) -> None:
        """Test detection of secret not rotated in 90+ days."""
        old_secret = create_secrets_manager_secret("old-secret", last_rotated_days_ago=120)
        snapshot = create_mock_snapshot(resources=[old_secret])

        check = SecretsRotationCheck()
        findings = check.execute(snapshot)

        assert len(findings) == 1
        assert findings[0].resource_arn == old_secret.arn
        assert findings[0].severity == Severity.MEDIUM
        assert "90" in findings[0].description or "120" in findings[0].description

    def test_recently_rotated_secret_no_findings(self) -> None:
        """Test that recently rotated secret produces no findings."""
        recent_secret = create_secrets_manager_secret("recent-secret", last_rotated_days_ago=30)
        snapshot = create_mock_snapshot(resources=[recent_secret])

        check = SecretsRotationCheck()
        findings = check.execute(snapshot)

        assert len(findings) == 0

    def test_secret_exactly_90_days_no_findings(self) -> None:
        """Test that secret rotated exactly 90 days ago produces no findings (boundary)."""
        secret_90 = create_secrets_manager_secret("secret-90", last_rotated_days_ago=90)
        snapshot = create_mock_snapshot(resources=[secret_90])

        check = SecretsRotationCheck()
        findings = check.execute(snapshot)

        assert len(findings) == 0

    def test_secret_91_days_creates_finding(self) -> None:
        """Test that secret rotated 91 days ago creates a finding (just over threshold)."""
        secret_91 = create_secrets_manager_secret("secret-91", last_rotated_days_ago=91)
        snapshot = create_mock_snapshot(resources=[secret_91])

        check = SecretsRotationCheck()
        findings = check.execute(snapshot)

        assert len(findings) == 1

    def test_multiple_secrets_mixed_rotation_age(self) -> None:
        """Test scanning multiple secrets with mixed rotation ages."""
        old_secret1 = create_secrets_manager_secret("old-1", last_rotated_days_ago=150)
        recent_secret = create_secrets_manager_secret("recent", last_rotated_days_ago=20)
        old_secret2 = create_secrets_manager_secret("old-2", last_rotated_days_ago=200)

        snapshot = create_mock_snapshot(resources=[old_secret1, recent_secret, old_secret2])

        check = SecretsRotationCheck()
        findings = check.execute(snapshot)

        assert len(findings) == 2
        finding_arns = [f.resource_arn for f in findings]
        assert old_secret1.arn in finding_arns
        assert old_secret2.arn in finding_arns
        assert recent_secret.arn not in finding_arns

    def test_remediation_guidance_present(self) -> None:
        """Test that findings include remediation guidance."""
        old_secret = create_secrets_manager_secret("test-secret", last_rotated_days_ago=100)
        snapshot = create_mock_snapshot(resources=[old_secret])

        check = SecretsRotationCheck()
        findings = check.execute(snapshot)

        assert len(findings) == 1
        assert findings[0].remediation
        assert "rotate" in findings[0].remediation.lower()

    def test_empty_snapshot_no_findings(self) -> None:
        """Test that empty snapshot produces no findings."""
        snapshot = create_mock_snapshot(resources=[])

        check = SecretsRotationCheck()
        findings = check.execute(snapshot)

        assert len(findings) == 0
