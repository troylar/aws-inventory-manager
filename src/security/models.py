"""Security scan result model for aggregating security findings."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List

from ..models.security_finding import SecurityFinding, Severity


@dataclass
class SecurityScanResult:
    """Aggregates security findings from scanning a snapshot.

    Attributes:
        findings: List of all security findings
        total_findings: Total count of findings
        snapshot_name: Name of the snapshot that was scanned
        scan_timestamp: When the scan was executed
    """

    snapshot_name: str
    scan_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    findings: List[SecurityFinding] = field(default_factory=list)

    @property
    def total_findings(self) -> int:
        """Get total count of findings.

        Returns:
            Number of findings in the result
        """
        return len(self.findings)

    def add_finding(self, finding: SecurityFinding) -> None:
        """Add a security finding to the result.

        Args:
            finding: SecurityFinding to add
        """
        self.findings.append(finding)

    def get_findings_by_severity(self, severity: Severity) -> List[SecurityFinding]:
        """Get all findings matching a specific severity level.

        Args:
            severity: Severity level to filter by

        Returns:
            List of findings with the specified severity
        """
        return [f for f in self.findings if f.severity == severity]
