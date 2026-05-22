"""
Tests for Analytics Service
"""

import pytest
from datetime import datetime, timedelta
from apps.api.app.services.analytics_service import (
    PerformanceMetrics,
    SkillMetrics,
    WorkflowMetrics,
    AgentAnalytics,
    SystemAnalytics,
)


class TestPerformanceMetrics:
    """Test performance metrics calculations."""

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        metrics = PerformanceMetrics(
            execution_count=10,
            success_count=8,
            failure_count=2,
        )
        assert metrics.success_rate == 80.0
        assert metrics.failure_rate == 20.0

    def test_success_rate_zero_executions(self):
        """Test success rate with zero executions."""
        metrics = PerformanceMetrics()
        assert metrics.success_rate == 0.0

    def test_metrics_to_dict(self):
        """Test conversion to dictionary."""
        metrics = PerformanceMetrics(
            execution_count=5,
            success_count=4,
            failure_count=1,
            average_duration_ms=150.0,
        )
        result = metrics.to_dict()
        assert result["execution_count"] == 5
        assert result["success_rate"] == 80.0
        assert result["average_duration_ms"] == 150.0


class TestSkillMetrics:
    """Test skill extraction metrics."""

    def test_extraction_success_rate(self):
        """Test extraction success rate calculation."""
        metrics = SkillMetrics(
            extraction_attempts=10,
            successful_extractions=7,
            failed_extractions=3,
        )
        assert metrics.extraction_success_rate == 70.0

    def test_skill_metrics_to_dict(self):
        """Test conversion to dictionary."""
        metrics = SkillMetrics(
            total_skills_extracted=5,
            extraction_attempts=10,
            successful_extractions=7,
        )
        result = metrics.to_dict()
        assert result["total_skills_extracted"] == 5
        assert result["extraction_success_rate"] == 70.0


class TestAgentAnalytics:
    """Test individual agent analytics."""

    def test_agent_creation(self):
        """Test agent analytics creation."""
        analytics = AgentAnalytics("agent-123")
        assert analytics.agent_id == "agent-123"
        assert analytics.metrics.execution_count == 0

    def test_record_successful_execution(self):
        """Test recording successful execution."""
        analytics = AgentAnalytics("agent-123")
        analytics.record_execution(duration_ms=100.0, success=True)

        assert analytics.metrics.execution_count == 1
        assert analytics.metrics.success_count == 1
        assert analytics.metrics.failure_count == 0
        assert analytics.metrics.average_duration_ms == 100.0

    def test_record_failed_execution(self):
        """Test recording failed execution."""
        analytics = AgentAnalytics("agent-123")
        analytics.record_execution(duration_ms=50.0, success=False, error="Timeout")

        assert analytics.metrics.execution_count == 1
        assert analytics.metrics.success_count == 0
        assert analytics.metrics.failure_count == 1
        assert "Timeout" in analytics.metrics.error_messages

    def test_average_duration_calculation(self):
        """Test average duration calculation."""
        analytics = AgentAnalytics("agent-123")
        analytics.record_execution(duration_ms=100.0, success=True)
        analytics.record_execution(duration_ms=200.0, success=True)
        analytics.record_execution(duration_ms=300.0, success=True)

        assert analytics.metrics.average_duration_ms == 200.0
        assert analytics.metrics.min_duration_ms == 100.0
        assert analytics.metrics.max_duration_ms == 300.0

    def test_get_recent_executions(self):
        """Test getting recent executions."""
        analytics = AgentAnalytics("agent-123")
        for i in range(5):
            analytics.record_execution(duration_ms=100.0 * (i + 1), success=True)

        recent = analytics.get_recent_executions(limit=3)
        assert len(recent) == 3


class TestSystemAnalytics:
    """Test system-wide analytics."""

    def test_system_analytics_creation(self):
        """Test system analytics creation."""
        system = SystemAnalytics()
        assert len(system.agent_analytics) == 0

    def test_get_or_create_agent_analytics(self):
        """Test getting or creating agent analytics."""
        system = SystemAnalytics()
        agent1 = system.get_or_create_agent_analytics("agent-1")
        agent2 = system.get_or_create_agent_analytics("agent-1")

        assert agent1 is agent2
        assert len(system.agent_analytics) == 1

    def test_record_agent_execution(self):
        """Test recording agent execution."""
        system = SystemAnalytics()
        system.record_agent_execution("agent-1", duration_ms=100.0, success=True)

        agent_metrics = system.get_agent_performance("agent-1")
        assert agent_metrics is not None
        assert agent_metrics["execution_count"] == 1
        assert agent_metrics["success_rate"] == 100.0

    def test_record_skill_extraction(self):
        """Test recording skill extraction."""
        system = SystemAnalytics()
        system.record_skill_extraction(accuracy=0.9, confidence=0.85, skills_count=3)

        assert system.skill_metrics.total_skills_extracted == 3
        assert system.skill_metrics.extraction_attempts == 1
        assert system.skill_metrics.successful_extractions == 1

    def test_get_system_health(self):
        """Test getting system health metrics."""
        system = SystemAnalytics()
        system.record_agent_execution("agent-1", duration_ms=100.0, success=True)
        system.record_agent_execution("agent-1", duration_ms=200.0, success=True)
        system.record_agent_execution("agent-2", duration_ms=150.0, success=True)

        health = system.get_system_health()
        assert health["agent_count"] == 2
        assert health["total_agent_executions"] == 3
        assert health["agent_success_rate"] == 100.0

    def test_detect_anomalies_empty_system(self):
        """Test anomaly detection on empty system."""
        system = SystemAnalytics()
        anomalies = system.detect_anomalies()
        assert len(anomalies) == 0

    def test_detect_anomalies_high_failure_rate(self):
        """Test detecting high failure rate anomaly."""
        system = SystemAnalytics()
        # Record multiple failures
        for _ in range(5):
            system.record_agent_execution("agent-1", duration_ms=100.0, success=False)

        anomalies = system.detect_anomalies()
        high_failure_anomalies = [a for a in anomalies if a["type"] == "high_failure_rate"]
        assert len(high_failure_anomalies) > 0

    def test_get_trends(self):
        """Test getting trends."""
        system = SystemAnalytics()
        system.record_agent_execution("agent-1", duration_ms=100.0, success=True)
        system.record_agent_execution("agent-2", duration_ms=200.0, success=True)

        trends = system.get_trends(time_window_hours=24)
        assert trends["time_window_hours"] == 24
        assert trends["active_agents_in_window"] >= 2

    def test_export_metrics_json(self):
        """Test exporting metrics in JSON format."""
        system = SystemAnalytics()
        system.record_agent_execution("agent-1", duration_ms=100.0, success=True)
        system.record_skill_extraction(accuracy=0.9, confidence=0.85)

        metrics = system.export_metrics(format="json")
        assert "timestamp" in metrics
        assert "agents" in metrics
        assert "system_health" in metrics
        assert "anomalies" in metrics
        assert "skills" in metrics

    def test_export_metrics_invalid_format(self):
        """Test exporting metrics with invalid format."""
        system = SystemAnalytics()
        with pytest.raises(ValueError):
            system.export_metrics(format="invalid_format")

    def test_all_agents_performance(self):
        """Test getting performance for all agents."""
        system = SystemAnalytics()
        system.record_agent_execution("agent-1", duration_ms=100.0, success=True)
        system.record_agent_execution("agent-2", duration_ms=200.0, success=True)

        all_metrics = system.get_all_agents_performance()
        assert len(all_metrics) == 2
        assert all_metrics[0]["agent_id"] in ["agent-1", "agent-2"]

    def test_workflow_metrics_tracking(self):
        """Test workflow metrics tracking."""
        system = SystemAnalytics()
        system.record_workflow_execution("workflow-1", duration_ms=1000.0, completed=True)
        system.record_workflow_execution("workflow-1", duration_ms=1200.0, completed=True)
        system.record_workflow_execution("workflow-1", duration_ms=800.0, completed=False)

        assert system.workflow_metrics.execution_count == 3
        assert system.workflow_metrics.completion_count == 2
        assert system.workflow_metrics.completion_rate == pytest.approx(66.67, rel=0.01)
