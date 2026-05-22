"""
Tests for Audit & Compliance Service
"""

import pytest
from datetime import datetime, timedelta
from apps.api.app.services.audit_compliance import (
    AuditEvent,
    EventType,
    ResourceType,
    DataRetentionPolicy,
    SensitiveDataMasker,
    AuditLogger,
    ComplianceChecker,
)


class TestAuditEvent:
    """Test audit event creation and serialization."""

    def test_audit_event_creation(self):
        """Test creating audit event."""
        event = AuditEvent(
            event_id="evt-123",
            event_type=EventType.CREATE,
            resource_type=ResourceType.AGENT,
            resource_id="agent-1",
            actor_id="user-1",
        )
        assert event.event_id == "evt-123"
        assert event.status == "success"

    def test_audit_event_to_dict(self):
        """Test converting audit event to dictionary."""
        event = AuditEvent(
            event_id="evt-123",
            event_type=EventType.DELETE,
            resource_type=ResourceType.SKILL,
            resource_id="skill-1",
            actor_id="user-1",
            tenant_id="tenant-1",
        )
        result = event.to_dict()
        assert result["event_id"] == "evt-123"
        assert result["event_type"] == "delete"
        assert result["resource_type"] == "skill"
        assert result["tenant_id"] == "tenant-1"


class TestSensitiveDataMasker:
    """Test sensitive data masking."""

    def test_mask_api_key(self):
        """Test masking API keys."""
        masker = SensitiveDataMasker()
        text = "api_key: 'sk-1234567890abcdef'"
        result = masker.mask_string(text)
        assert "[REDACTED_API_KEY]" in result
        assert "sk-1234567890" not in result

    def test_mask_password(self):
        """Test masking passwords."""
        masker = SensitiveDataMasker()
        text = "password: 'secretpassword123'"
        result = masker.mask_string(text)
        assert "[REDACTED_PASSWORD]" in result
        assert "secretpassword" not in result

    def test_mask_email(self):
        """Test masking email addresses."""
        masker = SensitiveDataMasker()
        text = "user@example.com sent a request"
        result = masker.mask_string(text)
        assert "[REDACTED_EMAIL]" in result
        assert "user@example.com" not in result

    def test_mask_dict(self):
        """Test masking sensitive fields in dictionary."""
        masker = SensitiveDataMasker()
        data = {
            "api_key": "sk-1234567890",
            "email": "user@example.com",
            "name": "John Doe",
        }
        result = masker.mask_dict(data)
        assert result["api_key"] == "[REDACTED]"
        assert "[REDACTED_EMAIL]" in result["email"]
        assert result["name"] == "John Doe"

    def test_mask_nested_dict(self):
        """Test masking nested dictionaries."""
        masker = SensitiveDataMasker()
        data = {
            "user": {
                "name": "John",
                "password": "secret123",
            },
            "credentials": ["token123", "key456"],
        }
        result = masker.mask_dict(data)
        assert result["user"]["password"] == "[REDACTED]"
        assert "[REDACTED]" in str(result["credentials"])


class TestDataRetentionPolicy:
    """Test data retention policy."""

    def test_default_retention_days(self):
        """Test default retention days."""
        policy = DataRetentionPolicy()
        assert policy.default_retention_days == 90

    def test_retention_by_event_type(self):
        """Test retention days by event type."""
        policy = DataRetentionPolicy()
        assert policy.get_retention_days(EventType.DELETE) == 365
        assert policy.get_retention_days(EventType.EXECUTE) == 30
        assert policy.get_retention_days(EventType.ACCESS) == 7

    def test_default_for_unknown_event_type(self):
        """Test default retention for unknown event type."""
        policy = DataRetentionPolicy()
        # ACCESS is in the policy
        days = policy.get_retention_days(EventType.CREATE)
        assert days == 90  # Default


class TestAuditLogger:
    """Test audit logging."""

    def test_log_event(self):
        """Test logging an event."""
        logger = AuditLogger()
        event = AuditEvent(
            event_id="evt-1",
            event_type=EventType.CREATE,
            resource_type=ResourceType.AGENT,
            resource_id="agent-1",
            actor_id="user-1",
        )
        logger.log_event(event)
        assert len(logger.events) == 1

    def test_log_agent_execution(self):
        """Test logging agent execution."""
        logger = AuditLogger()
        logger.log_agent_execution(
            agent_id="agent-1",
            actor_id="user-1",
            duration_ms=100.0,
            status="success",
        )
        assert len(logger.events) == 1
        assert logger.events[0].event_type == EventType.EXECUTE

    def test_log_data_access(self):
        """Test logging data access."""
        logger = AuditLogger()
        logger.log_data_access(
            user_id="user-1",
            resource_id="agent-1",
            resource_type=ResourceType.AGENT,
        )
        assert len(logger.events) == 1
        assert logger.events[0].event_type == EventType.ACCESS

    def test_log_resource_change(self):
        """Test logging resource changes."""
        logger = AuditLogger()
        before = {"name": "Old Agent", "status": "inactive"}
        after = {"name": "New Agent", "status": "active"}

        logger.log_resource_change(
            event_type=EventType.UPDATE,
            resource_id="agent-1",
            resource_type=ResourceType.AGENT,
            actor_id="user-1",
            before=before,
            after=after,
        )
        assert len(logger.events) == 1
        assert "name" in logger.events[0].changes
        assert "status" in logger.events[0].changes

    def test_get_events_all(self):
        """Test retrieving all events."""
        logger = AuditLogger()
        logger.log_agent_execution("agent-1", "user-1", 100.0)
        logger.log_agent_execution("agent-2", "user-1", 200.0)

        events = logger.get_events()
        assert len(events) == 2

    def test_get_events_with_filters(self):
        """Test retrieving events with filters."""
        logger = AuditLogger()
        logger.log_agent_execution("agent-1", "user-1", 100.0)
        logger.log_data_access("user-1", "agent-1", ResourceType.AGENT)

        # Filter by event type
        events = logger.get_events({"event_type": "execute"})
        assert len(events) == 1
        assert events[0]["event_type"] == "execute"

    def test_get_events_by_resource_id(self):
        """Test filtering by resource ID."""
        logger = AuditLogger()
        logger.log_agent_execution("agent-1", "user-1", 100.0)
        logger.log_agent_execution("agent-2", "user-1", 200.0)

        events = logger.get_events({"resource_id": "agent-1"})
        assert len(events) == 1
        assert events[0]["resource_id"] == "agent-1"

    def test_export_audit_trail(self):
        """Test exporting audit trail."""
        logger = AuditLogger()
        logger.log_agent_execution("agent-1", "user-1", 100.0, tenant_id="tenant-1")
        logger.log_agent_execution("agent-2", "user-1", 200.0, tenant_id="tenant-2")

        export = logger.export_audit_trail(tenant_id="tenant-1")
        assert export["tenant_id"] == "tenant-1"
        assert export["total_events"] == 1


class TestComplianceChecker:
    """Test compliance checking."""

    def test_compliance_checker_creation(self):
        """Test creating compliance checker."""
        logger = AuditLogger()
        policy = DataRetentionPolicy()
        checker = ComplianceChecker(logger, policy)
        assert checker.audit_logger is logger

    def test_check_data_retention_compliance(self):
        """Test data retention compliance check."""
        logger = AuditLogger()
        policy = DataRetentionPolicy()
        checker = ComplianceChecker(logger, policy)

        # Add an event
        logger.log_agent_execution("agent-1", "user-1", 100.0)

        result = checker.check_data_retention_compliance()
        assert "compliance_check_time" in result
        assert "violations" in result
        assert result["compliant"] is True

    def test_validate_multi_tenancy_isolation(self):
        """Test multi-tenancy isolation validation."""
        logger = AuditLogger()
        policy = DataRetentionPolicy()
        checker = ComplianceChecker(logger, policy)

        # Log events from different tenants
        logger.log_agent_execution("agent-1", "user-1", 100.0, tenant_id="tenant-1")
        logger.log_agent_execution("agent-2", "user-1", 200.0, tenant_id="tenant-2")

        result = checker.validate_multi_tenancy_isolation()
        assert result["total_tenants"] == 2
        assert result["total_events"] == 2
        assert result["compliant"] is True

    def test_verify_access_control(self):
        """Test access control verification."""
        logger = AuditLogger()
        policy = DataRetentionPolicy()
        checker = ComplianceChecker(logger, policy)

        # Log access events
        logger.log_data_access("user-1", "agent-1", ResourceType.AGENT)
        logger.log_data_access("user-2", "agent-2", ResourceType.AGENT)

        result = checker.verify_access_control()
        assert result["total_access_events"] == 2
        assert result["unique_users"] == 2
        assert result["compliant"] is True

    def test_generate_compliance_report(self):
        """Test generating compliance report."""
        logger = AuditLogger()
        policy = DataRetentionPolicy()
        checker = ComplianceChecker(logger, policy)

        logger.log_agent_execution("agent-1", "user-1", 100.0)
        logger.log_data_access("user-1", "agent-1", ResourceType.AGENT)

        report = checker.generate_compliance_report()
        assert "report_time" in report
        assert "retention_compliance" in report
        assert "isolation_compliance" in report
        assert "access_control_compliance" in report
        assert "overall_compliant" in report

    def test_suspicious_access_detection(self):
        """Test detection of suspicious access patterns."""
        logger = AuditLogger()
        policy = DataRetentionPolicy()
        checker = ComplianceChecker(logger, policy)

        # Log many access events for one user (would be suspicious)
        for i in range(150):
            logger.log_data_access(f"user-1", f"agent-{i}", ResourceType.AGENT)

        result = checker.verify_access_control()
        assert len(result["suspicious_access"]) > 0
