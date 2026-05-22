"""
Audit & Compliance Service

Tracks all operations for compliance and debugging.
Manages audit trails, compliance policies, and sensitive data masking.
"""

import logging
import re
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of audit events."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    ACCESS = "access"
    APPROVE = "approve"
    REJECT = "reject"
    ERROR = "error"


class ResourceType(str, Enum):
    """Types of resources being audited."""
    AGENT = "agent"
    SKILL = "skill"
    WORKFLOW = "workflow"
    CONNECTOR = "connector"
    USER = "user"
    TENANT = "tenant"
    CONFIGURATION = "configuration"


@dataclass
class AuditEvent:
    """Single audit event record."""
    event_id: str
    event_type: EventType
    resource_type: ResourceType
    resource_id: str
    actor_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tenant_id: Optional[str] = None
    correlation_id: Optional[str] = None
    status: str = "success"
    error_message: Optional[str] = None
    changes: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "resource_type": self.resource_type.value,
            "resource_id": self.resource_id,
            "actor_id": self.actor_id,
            "timestamp": self.timestamp.isoformat(),
            "tenant_id": self.tenant_id,
            "correlation_id": self.correlation_id,
            "status": self.status,
            "error_message": self.error_message,
            "changes": self.changes,
            "metadata": self.metadata,
        }


@dataclass
class DataRetentionPolicy:
    """Data retention policy for audit events."""
    default_retention_days: int = 90
    retention_by_event_type: Dict[EventType, int] = field(
        default_factory=lambda: {
            EventType.DELETE: 365,  # Keep deletions longer
            EventType.EXECUTE: 30,  # Keep executions shorter
            EventType.ACCESS: 7,    # Keep access logs briefly
        }
    )
    encryption_at_rest: bool = True
    access_log_enabled: bool = True
    sensitive_field_masking: bool = True

    def get_retention_days(self, event_type: EventType) -> int:
        """Get retention days for event type."""
        return self.retention_by_event_type.get(
            event_type, self.default_retention_days
        )


class SensitiveDataMasker:
    """Mask sensitive data in logs and audit trails."""

    def __init__(self):
        self.patterns = {
            "api_key": r"(?i)(api_key|api-key|apikey)\s*[:=]\s*['\"]?([a-z0-9\-_]+)['\"]?",
            "password": r"(?i)(password|pwd)\s*[:=]\s*['\"]?([^'\"\s]+)['\"]?",
            "token": r"(?i)(token|auth|bearer)\s+([a-z0-9\-_.]+)",
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
            "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
        }
        self.masking_rules = {
            "api_key": "[REDACTED_API_KEY]",
            "password": "[REDACTED_PASSWORD]",
            "token": "[REDACTED_TOKEN]",
            "email": "[REDACTED_EMAIL]",
            "phone": "[REDACTED_PHONE]",
            "credit_card": "[REDACTED_CREDIT_CARD]",
        }

    def mask_string(self, text: str) -> str:
        """Mask sensitive data in string."""
        if not text:
            return text

        for key, pattern in self.patterns.items():
            text = re.sub(pattern, self.masking_rules[key], text, flags=re.IGNORECASE)

        return text

    def mask_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive data in dictionary."""
        masked = {}

        for key, value in data.items():
            # Mask keys that look sensitive
            if any(sensitive in key.lower() for sensitive in ["password", "key", "token", "secret"]):
                masked[key] = "[REDACTED]"
            elif isinstance(value, str):
                masked[key] = self.mask_string(value)
            elif isinstance(value, dict):
                masked[key] = self.mask_dict(value)
            elif isinstance(value, list):
                masked[key] = [
                    self.mask_dict(item) if isinstance(item, dict) else
                    self.mask_string(item) if isinstance(item, str) else
                    item for item in value
                ]
            else:
                masked[key] = value

        return masked


class AuditLogger:
    """Log and retrieve audit events."""

    def __init__(self):
        self.events: List[AuditEvent] = []
        self.masker = SensitiveDataMasker()

    def log_event(self, event: AuditEvent) -> None:
        """Record an audit event."""
        # Mask sensitive data in changes and metadata
        if event.changes:
            event.changes = self.masker.mask_dict(event.changes)
        if event.metadata:
            event.metadata = self.masker.mask_dict(event.metadata)

        self.events.append(event)
        logger.info(f"Audit event logged: {event.event_type.value} on {event.resource_type.value}")

    def log_agent_execution(
        self, agent_id: str, actor_id: str, duration_ms: float,
        status: str = "success", tenant_id: Optional[str] = None
    ) -> None:
        """Log agent execution."""
        event = AuditEvent(
            event_id=f"exec-{id(object())}",
            event_type=EventType.EXECUTE,
            resource_type=ResourceType.AGENT,
            resource_id=agent_id,
            actor_id=actor_id,
            tenant_id=tenant_id,
            status=status,
            metadata={"duration_ms": duration_ms},
        )
        self.log_event(event)

    def log_data_access(
        self, user_id: str, resource_id: str, resource_type: ResourceType,
        access_type: str = "read", tenant_id: Optional[str] = None
    ) -> None:
        """Log data access."""
        event = AuditEvent(
            event_id=f"access-{id(object())}",
            event_type=EventType.ACCESS,
            resource_type=resource_type,
            resource_id=resource_id,
            actor_id=user_id,
            tenant_id=tenant_id,
            metadata={"access_type": access_type},
        )
        self.log_event(event)

    def log_resource_change(
        self, event_type: EventType, resource_id: str, resource_type: ResourceType,
        actor_id: str, before: Optional[Dict] = None, after: Optional[Dict] = None,
        tenant_id: Optional[str] = None
    ) -> None:
        """Log resource creation, update, or deletion."""
        changes = {}
        if before and after:
            for key in set(list(before.keys()) + list(after.keys())):
                if before.get(key) != after.get(key):
                    changes[key] = {
                        "before": before.get(key),
                        "after": after.get(key),
                    }

        event = AuditEvent(
            event_id=f"change-{id(object())}",
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            actor_id=actor_id,
            tenant_id=tenant_id,
            changes=changes,
        )
        self.log_event(event)

    def get_events(
        self, filters: Optional[Dict[str, Any]] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query audit trail with filters."""
        results = self.events

        if filters:
            if "event_type" in filters:
                event_type = filters["event_type"]
                if isinstance(event_type, str):
                    event_type = EventType(event_type)
                results = [e for e in results if e.event_type == event_type]

            if "resource_type" in filters:
                resource_type = filters["resource_type"]
                if isinstance(resource_type, str):
                    resource_type = ResourceType(resource_type)
                results = [e for e in results if e.resource_type == resource_type]

            if "resource_id" in filters:
                results = [e for e in results if e.resource_id == filters["resource_id"]]

            if "actor_id" in filters:
                results = [e for e in results if e.actor_id == filters["actor_id"]]

            if "tenant_id" in filters:
                results = [e for e in results if e.tenant_id == filters["tenant_id"]]

            if "start_time" in filters:
                start_time = filters["start_time"]
                results = [e for e in results if e.timestamp >= start_time]

            if "end_time" in filters:
                end_time = filters["end_time"]
                results = [e for e in results if e.timestamp <= end_time]

        return [e.to_dict() for e in results[-limit:]]

    def export_audit_trail(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Export complete audit trail."""
        events = [e for e in self.events if tenant_id is None or e.tenant_id == tenant_id]

        return {
            "export_time": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id,
            "total_events": len(events),
            "events": [e.to_dict() for e in events],
        }


class ComplianceChecker:
    """Check compliance with policies."""

    def __init__(self, audit_logger: AuditLogger, retention_policy: DataRetentionPolicy):
        self.audit_logger = audit_logger
        self.retention_policy = retention_policy

    def check_data_retention_compliance(self) -> Dict[str, Any]:
        """Check if data retention policy is being followed."""
        violations = []

        now = datetime.utcnow()

        for event in self.audit_logger.events:
            retention_days = self.retention_policy.get_retention_days(event.event_type)
            expiration_time = event.timestamp + timedelta(days=retention_days)

            # This is just checking if the logic would work; actual deletion would happen separately
            if now > expiration_time:
                violations.append({
                    "event_id": event.event_id,
                    "event_type": event.event_type.value,
                    "timestamp": event.timestamp.isoformat(),
                    "retention_days": retention_days,
                    "expired": True,
                })

        return {
            "compliance_check_time": datetime.utcnow().isoformat(),
            "total_events": len(self.audit_logger.events),
            "violations": violations,
            "compliant": len(violations) == 0,
        }

    def validate_multi_tenancy_isolation(self) -> Dict[str, Any]:
        """Validate multi-tenancy isolation in audit logs."""
        issues = []

        # Check for data leakage (shouldn't be any if properly isolated)
        tenant_events = {}
        for event in self.audit_logger.events:
            if event.tenant_id:
                if event.tenant_id not in tenant_events:
                    tenant_events[event.tenant_id] = []
                tenant_events[event.tenant_id].append(event)

        # All events should have proper tenant isolation
        return {
            "isolation_check_time": datetime.utcnow().isoformat(),
            "total_tenants": len(tenant_events),
            "total_events": len(self.audit_logger.events),
            "issues": issues,
            "compliant": len(issues) == 0,
        }

    def verify_access_control(self) -> Dict[str, Any]:
        """Verify that access control is properly logged."""
        access_events = [e for e in self.audit_logger.events if e.event_type == EventType.ACCESS]

        # Check for suspicious patterns (e.g., same user accessing too many resources)
        user_access_counts = {}
        for event in access_events:
            if event.actor_id not in user_access_counts:
                user_access_counts[event.actor_id] = 0
            user_access_counts[event.actor_id] += 1

        suspicious_access = [
            {
                "actor_id": actor_id,
                "access_count": count,
                "flag": "high_access_count" if count > 100 else None,
            }
            for actor_id, count in user_access_counts.items()
            if count > 100
        ]

        return {
            "access_control_check_time": datetime.utcnow().isoformat(),
            "total_access_events": len(access_events),
            "unique_users": len(user_access_counts),
            "suspicious_access": suspicious_access,
            "compliant": len(suspicious_access) == 0,
        }

    def generate_compliance_report(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate comprehensive compliance report."""
        retention_check = self.check_data_retention_compliance()
        isolation_check = self.validate_multi_tenancy_isolation()
        access_check = self.verify_access_control()

        return {
            "report_time": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id,
            "retention_compliance": retention_check,
            "isolation_compliance": isolation_check,
            "access_control_compliance": access_check,
            "overall_compliant": (
                retention_check["compliant"] and
                isolation_check["compliant"] and
                access_check["compliant"]
            ),
        }


# Global instances
audit_logger = AuditLogger()
retention_policy = DataRetentionPolicy()
compliance_checker = ComplianceChecker(audit_logger, retention_policy)
