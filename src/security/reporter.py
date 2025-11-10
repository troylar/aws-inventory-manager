"""Security findings reporter with multiple output formats."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List

from rich.console import Console
from rich.table import Table

from src.models.security_finding import SecurityFinding, Severity


class SecurityReporter:
    """Report security findings in various formats (terminal, JSON, CSV)."""

    def format_terminal(self, findings: List[SecurityFinding]) -> str:
        """Format findings for terminal output using Rich.

        Args:
            findings: List of security findings

        Returns:
            Formatted string for terminal display
        """
        if not findings:
            return "No security findings detected."

        # Create a Rich table
        table = Table(title="Security Findings")
        table.add_column("Severity", style="bold")
        table.add_column("Resource")
        table.add_column("Finding Type")
        table.add_column("Description")

        for finding in findings:
            # Color code severity
            severity_str = finding.severity.value.upper()
            if finding.severity == Severity.CRITICAL:
                severity_display = f"[red]{severity_str}[/red]"
            elif finding.severity == Severity.HIGH:
                severity_display = f"[orange1]{severity_str}[/orange1]"
            elif finding.severity == Severity.MEDIUM:
                severity_display = f"[yellow]{severity_str}[/yellow]"
            else:
                severity_display = f"[cyan]{severity_str}[/cyan]"

            # Truncate description if too long
            description = finding.description
            if len(description) > 60:
                description = description[:57] + "..."

            # Extract resource ID from ARN for display
            resource_display = (
                finding.resource_arn.split("/")[-1]
                if "/" in finding.resource_arn
                else finding.resource_arn.split(":")[-1]
            )

            table.add_row(
                severity_display,
                resource_display,
                finding.finding_type,
                description,
            )

        # Render table to string
        console = Console()
        with console.capture() as capture:
            console.print(table)

        return capture.get()

    def export_json(self, findings: List[SecurityFinding], filepath: str) -> None:
        """Export findings to JSON format.

        Args:
            findings: List of security findings
            filepath: Output file path
        """
        # Generate summary statistics
        summary = self.generate_summary(findings)

        # Convert findings to dictionaries
        findings_data = [finding.to_dict() for finding in findings]

        output = {
            "findings": findings_data,
            "summary": summary,
        }

        # Write to file
        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)

    def export_csv(self, findings: List[SecurityFinding], filepath: str) -> None:
        """Export findings to CSV format.

        Args:
            findings: List of security findings
            filepath: Output file path
        """
        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Define CSV columns
        fieldnames = [
            "resource_arn",
            "finding_type",
            "severity",
            "description",
            "remediation",
            "cis_control",
        ]

        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for finding in findings:
                row = {
                    "resource_arn": finding.resource_arn,
                    "finding_type": finding.finding_type,
                    "severity": finding.severity.value,
                    "description": finding.description,
                    "remediation": finding.remediation,
                    "cis_control": finding.cis_control or "",
                }
                writer.writerow(row)

    def group_by_severity(self, findings: List[SecurityFinding]) -> Dict[Severity, List[SecurityFinding]]:
        """Group findings by severity level.

        Args:
            findings: List of security findings

        Returns:
            Dictionary mapping Severity to lists of findings
        """
        grouped: Dict[Severity, List[SecurityFinding]] = {
            Severity.CRITICAL: [],
            Severity.HIGH: [],
            Severity.MEDIUM: [],
            Severity.LOW: [],
        }

        for finding in findings:
            grouped[finding.severity].append(finding)

        return grouped

    def generate_summary(self, findings: List[SecurityFinding]) -> dict:
        """Generate summary statistics for findings.

        Args:
            findings: List of security findings

        Returns:
            Dictionary with counts by severity
        """
        grouped = self.group_by_severity(findings)

        return {
            "total_findings": len(findings),
            "critical_count": len(grouped[Severity.CRITICAL]),
            "high_count": len(grouped[Severity.HIGH]),
            "medium_count": len(grouped[Severity.MEDIUM]),
            "low_count": len(grouped[Severity.LOW]),
        }
