"""CIS Benchmark mapper for security findings."""

from __future__ import annotations

from typing import Dict, List, Optional

from src.models.security_finding import SecurityFinding


class CISMapper:
    """Maps security findings to CIS AWS Foundations Benchmark controls."""

    # CIS control ID to human-readable name mapping
    CIS_CONTROLS = {
        "2.1.5": "S3 Bucket Public Access Block",
        "5.2": "Security Groups - SSH Access",
        "5.3": "Security Groups - RDP Access",
        "1.3": "IAM Access Keys Rotated",
        "1.4": "IAM Credentials Unused",
    }

    def get_cis_control(self, finding: SecurityFinding) -> Optional[str]:
        """Get the CIS control ID from a security finding.

        Args:
            finding: SecurityFinding to extract control ID from

        Returns:
            CIS control ID string or None if not mapped
        """
        return finding.cis_control

    def get_control_name(self, control_id: str) -> Optional[str]:
        """Get the human-readable name for a CIS control ID.

        Args:
            control_id: CIS control ID (e.g., "2.1.5")

        Returns:
            Human-readable control name or None if not found
        """
        return self.CIS_CONTROLS.get(control_id)

    def get_summary(self, findings: List[SecurityFinding]) -> dict:
        """Generate a summary of CIS control pass/fail statistics.

        Args:
            findings: List of security findings

        Returns:
            Dictionary with total_controls_checked, controls_failed, controls_passed
        """
        # If no findings, return zeros
        if not findings:
            return {
                "total_controls_checked": 0,
                "controls_failed": 0,
                "controls_passed": 0,
            }

        # Count unique CIS controls that have findings (failures)
        failed_controls = set()
        for finding in findings:
            if finding.cis_control:
                failed_controls.add(finding.cis_control)

        controls_failed = len(failed_controls)

        # For this implementation, we assume all known CIS controls were checked
        # and only the ones with findings failed
        total_controls_checked = len(self.CIS_CONTROLS)
        controls_passed = total_controls_checked - controls_failed

        return {
            "total_controls_checked": total_controls_checked,
            "controls_failed": controls_failed,
            "controls_passed": controls_passed,
        }

    def group_by_control(self, findings: List[SecurityFinding]) -> Dict[str, List[SecurityFinding]]:
        """Group security findings by their CIS control ID.

        Args:
            findings: List of security findings

        Returns:
            Dictionary mapping CIS control IDs to lists of findings
        """
        grouped: Dict[str, List[SecurityFinding]] = {}

        for finding in findings:
            if finding.cis_control:
                if finding.cis_control not in grouped:
                    grouped[finding.cis_control] = []
                grouped[finding.cis_control].append(finding)

        return grouped
