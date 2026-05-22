"""
Analytics Service

Tracks and aggregates system metrics across agents, skills, and workflows.
Provides performance analysis, anomaly detection, and trend analysis.
"""

import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from statistics import mean, stdev, median

logger = logging.getLogger(__name__)


class MetricCategory(str, Enum):
    """Categories of metrics."""
    AGENT = "agent"
    SKILL = "skill"
    WORKFLOW = "workflow"
    SYSTEM = "system"


@dataclass
class PerformanceMetrics:
    """Metrics for agent or workflow execution."""
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    average_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    max_duration_ms: float = 0.0
    last_execution_time: Optional[datetime] = None
    error_messages: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.execution_count == 0:
            return 0.0
        return (self.success_count / self.execution_count) * 100

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate percentage."""
        return 100 - self.success_rate

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_rate,
            "failure_rate": self.failure_rate,
            "average_duration_ms": self.average_duration_ms,
            "min_duration_ms": self.min_duration_ms if self.min_duration_ms != float('inf') else None,
            "max_duration_ms": self.max_duration_ms,
            "last_execution_time": self.last_execution_time.isoformat() if self.last_execution_time else None,
        }


@dataclass
class SkillMetrics:
    """Metrics for skill extraction."""
    total_skills_extracted: int = 0
    average_extraction_accuracy: float = 0.0
    average_confidence_score: float = 0.0
    extraction_attempts: int = 0
    successful_extractions: int = 0
    failed_extractions: int = 0
    accuracy_scores: List[float] = field(default_factory=list)
    confidence_scores: List[float] = field(default_factory=list)

    @property
    def extraction_success_rate(self) -> float:
        """Calculate extraction success rate."""
        if self.extraction_attempts == 0:
            return 0.0
        return (self.successful_extractions / self.extraction_attempts) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_skills_extracted": self.total_skills_extracted,
            "extraction_success_rate": self.extraction_success_rate,
            "average_extraction_accuracy": self.average_extraction_accuracy,
            "average_confidence_score": self.average_confidence_score,
            "extraction_attempts": self.extraction_attempts,
            "successful_extractions": self.successful_extractions,
            "failed_extractions": self.failed_extractions,
        }


@dataclass
class WorkflowMetrics:
    """Metrics for workflow execution."""
    workflow_count: int = 0
    execution_count: int = 0
    completion_count: int = 0
    average_duration_ms: float = 0.0
    bottleneck_steps: List[str] = field(default_factory=list)
    execution_durations: List[float] = field(default_factory=list)

    @property
    def completion_rate(self) -> float:
        """Calculate workflow completion rate."""
        if self.execution_count == 0:
            return 0.0
        return (self.completion_count / self.execution_count) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "workflow_count": self.workflow_count,
            "execution_count": self.execution_count,
            "completion_count": self.completion_count,
            "completion_rate": self.completion_rate,
            "average_duration_ms": self.average_duration_ms,
            "bottleneck_steps": self.bottleneck_steps,
        }


class AgentAnalytics:
    """Track individual agent performance over time."""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.metrics = PerformanceMetrics()
        self.execution_history: List[Dict[str, Any]] = []
        self.created_at = datetime.utcnow()

    def record_execution(self, duration_ms: float, success: bool, error: Optional[str] = None) -> None:
        """Record an agent execution."""
        self.metrics.execution_count += 1
        self.metrics.last_execution_time = datetime.utcnow()

        if success:
            self.metrics.success_count += 1
        else:
            self.metrics.failure_count += 1
            if error:
                self.metrics.error_messages.append(error)

        # Update min/max
        self.metrics.min_duration_ms = min(self.metrics.min_duration_ms, duration_ms)
        self.metrics.max_duration_ms = max(self.metrics.max_duration_ms, duration_ms)

        # Update average (incremental)
        if self.metrics.execution_count == 1:
            self.metrics.average_duration_ms = duration_ms
        else:
            total = self.metrics.average_duration_ms * (self.metrics.execution_count - 1)
            self.metrics.average_duration_ms = (total + duration_ms) / self.metrics.execution_count

        # Record in history
        self.execution_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "duration_ms": duration_ms,
            "success": success,
            "error": error,
        })

    def get_metrics(self) -> Dict[str, Any]:
        """Get agent metrics."""
        return {
            "agent_id": self.agent_id,
            "created_at": self.created_at.isoformat(),
            **self.metrics.to_dict(),
        }

    def get_recent_executions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent executions."""
        return self.execution_history[-limit:]


class SystemAnalytics:
    """Aggregate metrics across all agents and workflows."""

    def __init__(self):
        self.agent_analytics: Dict[str, AgentAnalytics] = {}
        self.skill_metrics = SkillMetrics()
        self.workflow_metrics = WorkflowMetrics()
        self.startup_time = datetime.utcnow()
        self.metric_history: List[Dict[str, Any]] = []

    def get_or_create_agent_analytics(self, agent_id: str) -> AgentAnalytics:
        """Get or create analytics for an agent."""
        if agent_id not in self.agent_analytics:
            self.agent_analytics[agent_id] = AgentAnalytics(agent_id)
        return self.agent_analytics[agent_id]

    def record_agent_execution(
        self, agent_id: str, duration_ms: float, success: bool, error: Optional[str] = None
    ) -> None:
        """Record agent execution."""
        analytics = self.get_or_create_agent_analytics(agent_id)
        analytics.record_execution(duration_ms, success, error)

    def record_skill_extraction(
        self, accuracy: float, confidence: float, skills_count: int = 1
    ) -> None:
        """Record skill extraction."""
        self.skill_metrics.extraction_attempts += 1

        if accuracy > 0:
            self.skill_metrics.successful_extractions += 1
            self.skill_metrics.accuracy_scores.append(accuracy)
            self.skill_metrics.average_extraction_accuracy = mean(self.skill_metrics.accuracy_scores)
        else:
            self.skill_metrics.failed_extractions += 1

        self.skill_metrics.confidence_scores.append(confidence)
        self.skill_metrics.average_confidence_score = mean(self.skill_metrics.confidence_scores)
        self.skill_metrics.total_skills_extracted += skills_count

    def record_workflow_execution(
        self, workflow_id: str, duration_ms: float, completed: bool
    ) -> None:
        """Record workflow execution."""
        self.workflow_metrics.execution_count += 1

        if completed:
            self.workflow_metrics.completion_count += 1

        self.workflow_metrics.execution_durations.append(duration_ms)
        self.workflow_metrics.average_duration_ms = mean(self.workflow_metrics.execution_durations)

    def get_agent_performance(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get performance metrics for specific agent."""
        if agent_id in self.agent_analytics:
            return self.agent_analytics[agent_id].get_metrics()
        return None

    def get_all_agents_performance(self) -> List[Dict[str, Any]]:
        """Get performance metrics for all agents."""
        return [analytics.get_metrics() for analytics in self.agent_analytics.values()]

    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health KPIs."""
        uptime_seconds = (datetime.utcnow() - self.startup_time).total_seconds()

        agent_count = len(self.agent_analytics)
        total_agent_executions = sum(a.metrics.execution_count for a in self.agent_analytics.values())
        total_agent_successes = sum(a.metrics.success_count for a in self.agent_analytics.values())

        agent_success_rate = (
            (total_agent_successes / total_agent_executions * 100)
            if total_agent_executions > 0 else 0.0
        )

        avg_agent_duration = (
            mean([a.metrics.average_duration_ms for a in self.agent_analytics.values()])
            if self.agent_analytics else 0.0
        )

        return {
            "uptime_seconds": uptime_seconds,
            "startup_time": self.startup_time.isoformat(),
            "agent_count": agent_count,
            "total_agent_executions": total_agent_executions,
            "agent_success_rate": agent_success_rate,
            "average_agent_duration_ms": avg_agent_duration,
            "skill_extraction_success_rate": self.skill_metrics.extraction_success_rate,
            "workflow_completion_rate": self.workflow_metrics.completion_rate,
            "total_skills_extracted": self.skill_metrics.total_skills_extracted,
            "total_workflows_executed": self.workflow_metrics.execution_count,
        }

    def detect_anomalies(self, threshold_std_dev: float = 2.0) -> List[Dict[str, Any]]:
        """Detect performance anomalies using statistical analysis."""
        anomalies = []

        # Check each agent for duration anomalies
        for agent_id, analytics in self.agent_analytics.items():
            if len(analytics.execution_history) < 3:
                continue

            durations = [exec["duration_ms"] for exec in analytics.execution_history]
            avg = mean(durations)
            std = stdev(durations) if len(durations) > 1 else 0

            # Find executions beyond threshold
            for i, execution in enumerate(analytics.execution_history[-10:]):  # Check last 10
                if std > 0 and abs(execution["duration_ms"] - avg) > threshold_std_dev * std:
                    anomalies.append({
                        "type": "duration_anomaly",
                        "agent_id": agent_id,
                        "duration_ms": execution["duration_ms"],
                        "average_ms": avg,
                        "std_dev": std,
                        "timestamp": execution["timestamp"],
                    })

        # Check for high failure rates
        for agent_id, analytics in self.agent_analytics.items():
            if analytics.metrics.failure_rate > 20 and analytics.metrics.execution_count > 5:
                anomalies.append({
                    "type": "high_failure_rate",
                    "agent_id": agent_id,
                    "failure_rate": analytics.metrics.failure_rate,
                    "recent_errors": analytics.metrics.error_messages[-5:],
                })

        return anomalies

    def get_trends(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Analyze trends over time window."""
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)

        # Collect metrics for agents with recent activity
        active_agents = []
        for agent_id, analytics in self.agent_analytics.items():
            if analytics.execution_history:
                last_exec_time = datetime.fromisoformat(
                    analytics.execution_history[-1]["timestamp"]
                )
                if last_exec_time > cutoff_time:
                    active_agents.append({
                        "agent_id": agent_id,
                        "metrics": analytics.get_metrics(),
                    })

        return {
            "time_window_hours": time_window_hours,
            "active_agents_in_window": len(active_agents),
            "agents": active_agents,
            "system_health": self.get_system_health(),
        }

    def export_metrics(self, format: str = "json") -> Any:
        """Export metrics in specified format."""
        if format == "json":
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "agents": self.get_all_agents_performance(),
                "system_health": self.get_system_health(),
                "anomalies": self.detect_anomalies(),
                "skills": self.skill_metrics.to_dict(),
                "workflows": self.workflow_metrics.to_dict(),
            }
        elif format == "csv":
            # Could be extended for CSV export
            raise NotImplementedError("CSV export not yet implemented")
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Global analytics instance
system_analytics = SystemAnalytics()
