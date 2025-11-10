"""Security Group security checks."""

from __future__ import annotations

from typing import Any, Dict, List

from ...models.security_finding import SecurityFinding, Severity
from ...models.snapshot import Snapshot
from .base import SecurityCheck


class SecurityGroupOpenCheck(SecurityCheck):
    """Check for security groups with critical ports open to 0.0.0.0/0.

    Critical ports checked:
    - 22 (SSH) - CIS 5.2
    - 3389 (RDP) - CIS 5.3
    - 3306 (MySQL)
    - 5432 (PostgreSQL)
    - 1433 (Microsoft SQL Server)
    - 27017 (MongoDB)

    Severity: HIGH
    """

    # Critical ports to check and their descriptions
    CRITICAL_PORTS = {
        22: ("SSH", "5.2"),
        3389: ("RDP", "5.3"),
        3306: ("MySQL", "5.2"),
        5432: ("PostgreSQL", "5.2"),
        1433: ("Microsoft SQL Server", "5.2"),
        27017: ("MongoDB", "5.2"),
    }

    @property
    def check_id(self) -> str:
        """Return check identifier."""
        return "security_group_open"

    @property
    def severity(self) -> Severity:
        """Return check severity."""
        return Severity.HIGH

    def execute(self, snapshot: Snapshot) -> List[SecurityFinding]:
        """Execute security group open port check.

        Checks for critical ports (22, 3389, 3306, 5432, 1433, 27017) that are
        open to 0.0.0.0/0 in security group ingress rules.

        Args:
            snapshot: Snapshot to scan

        Returns:
            List of findings for security groups with open critical ports
        """
        findings: List[SecurityFinding] = []

        for resource in snapshot.resources:
            # Only check EC2 security groups
            if not resource.resource_type.startswith("ec2:security-group"):
                continue

            if resource.raw_config is None:
                continue

            # Check for open critical ports
            open_ports = self._find_open_critical_ports(resource.raw_config)

            # Create one finding per open port
            for port in open_ports:
                port_name, cis_control = self.CRITICAL_PORTS[port]

                finding = SecurityFinding(
                    resource_arn=resource.arn,
                    finding_type=self.check_id,
                    severity=self.severity,
                    description=f"Security group '{resource.name}' has port {port} ({port_name}) "
                    f"open to 0.0.0.0/0. This allows unrestricted access from the internet.",
                    remediation=f"Restrict access to port {port} by removing the 0.0.0.0/0 CIDR range "
                    f"from the security group ingress rules. Only allow access from specific, "
                    f"trusted IP addresses or CIDR blocks that require access.",
                    cis_control=cis_control,
                    metadata={
                        "group_id": resource.raw_config.get("GroupId", ""),
                        "port": port,
                        "protocol": "tcp",
                        "cidr": "0.0.0.0/0",
                    },
                )
                findings.append(finding)

        return findings

    def _find_open_critical_ports(self, config: Dict[str, Any]) -> List[int]:
        """Find critical ports that are open to 0.0.0.0/0.

        Args:
            config: Security group raw configuration

        Returns:
            List of critical port numbers that are open to 0.0.0.0/0
        """
        open_ports: List[int] = []
        ip_permissions = config.get("IpPermissions", [])

        for permission in ip_permissions:
            # Get the port range
            from_port = permission.get("FromPort")
            to_port = permission.get("ToPort")

            # Skip if no ports defined
            if from_port is None or to_port is None:
                continue

            # Check if any critical port is in this range
            for critical_port in self.CRITICAL_PORTS.keys():
                if from_port <= critical_port <= to_port:
                    # Check if this port is open to 0.0.0.0/0
                    if self._is_open_to_world(permission):
                        open_ports.append(critical_port)

        return open_ports

    def _is_open_to_world(self, permission: Dict[str, Any]) -> bool:
        """Check if a permission allows access from 0.0.0.0/0.

        Args:
            permission: IP permission dictionary from IpPermissions

        Returns:
            True if permission includes 0.0.0.0/0
        """
        ip_ranges = permission.get("IpRanges", [])

        for ip_range in ip_ranges:
            cidr = ip_range.get("CidrIp", "")
            if cidr == "0.0.0.0/0":
                return True

        return False
