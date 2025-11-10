"""Base class for security checks."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from ...models.security_finding import SecurityFinding, Severity
from ...models.snapshot import Snapshot


class SecurityCheck(ABC):
    """Abstract base class for all security checks.

    Each security check should:
    1. Have a unique check_id
    2. Have a defined severity level
    3. Implement the execute method to scan a snapshot
    4. Return a list of SecurityFinding objects
    """

    def __init__(self) -> None:
        """Initialize the security check."""
        pass

    @property
    @abstractmethod
    def check_id(self) -> str:
        """Unique identifier for this check.

        Returns:
            String identifier (e.g., "s3_public_bucket")
        """
        pass

    @property
    @abstractmethod
    def severity(self) -> Severity:
        """Severity level for findings from this check.

        Returns:
            Severity enum value
        """
        pass

    @abstractmethod
    def execute(self, snapshot: Snapshot) -> List[SecurityFinding]:
        """Execute the security check on a snapshot.

        Args:
            snapshot: Snapshot to scan for security issues

        Returns:
            List of SecurityFinding objects (empty list if no issues found)
        """
        pass
