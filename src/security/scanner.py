"""Security scanner for detecting misconfigurations in AWS snapshots."""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import List, Optional

from ..models.security_finding import Severity
from ..models.snapshot import Snapshot
from .checks.base import SecurityCheck
from .models import SecurityScanResult


class SecurityScanner:
    """Scans AWS snapshots for security misconfigurations.

    The scanner automatically discovers and loads all security check modules
    from the checks package and executes them against snapshots.
    """

    def __init__(self) -> None:
        """Initialize the security scanner and load all security checks."""
        self.checks: List[SecurityCheck] = []
        self._load_checks()

    def _load_checks(self) -> None:
        """Dynamically load all security check modules from the checks package.

        Discovers all Python modules in src/security/checks/, finds SecurityCheck
        subclasses, and instantiates them.
        """
        from . import checks

        # Discover all check modules
        for importer, modname, ispkg in pkgutil.iter_modules(checks.__path__):
            # Skip the base module and __init__
            if modname in ("base", "__init__"):
                continue

            # Import the module
            try:
                module = importlib.import_module(f".checks.{modname}", package="src.security")

                # Find all SecurityCheck subclasses in the module
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    # Check if it's a subclass of SecurityCheck (but not SecurityCheck itself)
                    if issubclass(obj, SecurityCheck) and obj is not SecurityCheck:
                        # Instantiate and add to checks list
                        check_instance = obj()
                        self.checks.append(check_instance)

            except Exception as e:
                # Log the error but continue loading other checks
                print(f"Warning: Failed to load check module {modname}: {e}")
                continue

    def scan(self, snapshot: Snapshot, severity_filter: Optional[Severity] = None) -> SecurityScanResult:
        """Scan a snapshot for security misconfigurations.

        Args:
            snapshot: Snapshot to scan
            severity_filter: Optional severity level to filter findings (only include findings
                           matching this severity)

        Returns:
            SecurityScanResult containing all findings from the scan
        """
        result = SecurityScanResult(snapshot_name=snapshot.name)

        # Execute all checks on the snapshot
        for check in self.checks:
            try:
                findings = check.execute(snapshot)

                # Add findings to result, applying severity filter if specified
                for finding in findings:
                    if severity_filter is None or finding.severity == severity_filter:
                        result.add_finding(finding)

            except Exception as e:
                # Log the error but continue with other checks
                print(f"Warning: Check {check.check_id} failed: {e}")
                continue

        return result
