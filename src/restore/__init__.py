"""Resource cleanup/restoration module.

This module provides functionality to delete AWS resources created after a baseline
snapshot, with comprehensive safety protections.

Classes:
    ResourceCleaner: Main orchestrator for restore operations
    DependencyResolver: Dependency graph construction and deletion ordering
    SafetyChecker: Protection rule evaluation
    AuditStorage: Audit log storage and retrieval
"""

from __future__ import annotations

__all__ = [
    "ResourceCleaner",
    "DependencyResolver",
    "SafetyChecker",
    "AuditStorage",
]
