"""
Observability Integration Service

Integrates with Prometheus, structured logging, and distributed tracing.
Provides metrics export, health checks, and correlation IDs for request tracking.
"""

import logging
import json
import uuid
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from contextlib import contextmanager
import time

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Prometheus metric types."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


@dataclass
class PrometheusMetric:
    """Prometheus metric definition."""
    name: str
    type: MetricType
    help: str
    labels: List[str] = field(default_factory=list)
    value: float = 0.0
    label_values: Dict[str, str] = field(default_factory=dict)

    def to_prometheus_format(self) -> str:
        """Convert to Prometheus text format."""
        label_str = ",".join(
            f'{k}="{v}"' for k, v in self.label_values.items()
        ) if self.label_values else ""

        if label_str:
            return f"{self.name}{{{label_str}}} {self.value}"
        return f"{self.name} {self.value}"


class MetricsExporter:
    """Export metrics in Prometheus format."""

    def __init__(self):
        self.metrics: Dict[str, PrometheusMetric] = {}
        self.counters: Dict[str, int] = {}
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = {}

    def register_metric(self, metric: PrometheusMetric) -> None:
        """Register a new metric."""
        self.metrics[metric.name] = metric
        logger.info(f"Metric registered: {metric.name}")

    def increment_counter(self, name: str, amount: int = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        key = self._make_key(name, labels)
        self.counters[key] = self.counters.get(key, 0) + amount

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric."""
        key = self._make_key(name, labels)
        self.gauges[key] = value

    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a histogram value."""
        key = self._make_key(name, labels)
        if key not in self.histograms:
            self.histograms[key] = []
        self.histograms[key].append(value)

    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> int:
        """Get counter value."""
        key = self._make_key(name, labels)
        return self.counters.get(key, 0)

    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get gauge value."""
        key = self._make_key(name, labels)
        return self.gauges.get(key, 0.0)

    def get_histogram_stats(self, name: str, labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """Get histogram statistics."""
        key = self._make_key(name, labels)
        values = self.histograms.get(key, [])

        if not values:
            return {
                "count": 0,
                "sum": 0.0,
                "min": 0.0,
                "max": 0.0,
                "avg": 0.0,
            }

        sorted_values = sorted(values)
        return {
            "count": len(values),
            "sum": sum(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "p50": sorted_values[len(values) // 2],
            "p95": sorted_values[int(len(values) * 0.95)],
            "p99": sorted_values[int(len(values) * 0.99)],
        }

    def export_prometheus_format(self) -> str:
        """Export all metrics in Prometheus text format."""
        lines = []

        # Export counters
        for key, value in self.counters.items():
            lines.append(f"{key} {value}")

        # Export gauges
        for key, value in self.gauges.items():
            lines.append(f"{key} {value}")

        # Export histograms (as summaries)
        for key, values in self.histograms.items():
            if values:
                stats = self.get_histogram_stats(key.split("{")[0])
                lines.append(f"{key}_sum {stats['sum']}")
                lines.append(f"{key}_count {stats['count']}")

        return "\n".join(lines)

    def _make_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Create metric key with labels."""
        if labels:
            label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
            return f"{name}{{{label_str}}}"
        return name


@dataclass
class CorrelationContext:
    """Context for tracking request flow across services."""
    correlation_id: str
    request_id: str
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "correlation_id": self.correlation_id,
            "request_id": self.request_id,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "start_time": self.start_time.isoformat(),
            "metadata": self.metadata,
        }


class StructuredLogger:
    """JSON-structured logging with correlation IDs."""

    def __init__(self):
        self.context_stack: List[CorrelationContext] = []

    def set_context(self, context: CorrelationContext) -> None:
        """Set correlation context."""
        self.context_stack.append(context)

    def clear_context(self) -> None:
        """Clear correlation context."""
        if self.context_stack:
            self.context_stack.pop()

    def get_context(self) -> Optional[CorrelationContext]:
        """Get current correlation context."""
        return self.context_stack[-1] if self.context_stack else None

    @contextmanager
    def context(self, user_id: Optional[str] = None, tenant_id: Optional[str] = None):
        """Context manager for correlation context."""
        ctx = CorrelationContext(
            correlation_id=str(uuid.uuid4()),
            request_id=str(uuid.uuid4()),
            user_id=user_id,
            tenant_id=tenant_id,
        )
        self.set_context(ctx)
        try:
            yield ctx
        finally:
            self.clear_context()

    def _add_context(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add correlation context to log data."""
        context = self.get_context()
        if context:
            log_data.update({
                "correlation_id": context.correlation_id,
                "request_id": context.request_id,
                "user_id": context.user_id,
                "tenant_id": context.tenant_id,
            })
        return log_data

    def log_info(self, message: str, **kwargs) -> None:
        """Log info message."""
        log_data = self._add_context({
            "level": "INFO",
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        })
        logger.info(json.dumps(log_data))

    def log_error(self, message: str, error: Optional[Exception] = None, **kwargs) -> None:
        """Log error message."""
        log_data = self._add_context({
            "level": "ERROR",
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        })
        if error:
            log_data["error"] = str(error)
            log_data["error_type"] = type(error).__name__
        logger.error(json.dumps(log_data))

    def log_warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        log_data = self._add_context({
            "level": "WARNING",
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        })
        logger.warning(json.dumps(log_data))


class HealthChecker:
    """Health check implementation for Kubernetes probes."""

    def __init__(self):
        self.readiness: Dict[str, bool] = {}
        self.liveness: Dict[str, bool] = {}
        self.startup_complete = False

    def set_ready(self, component: str, ready: bool = True) -> None:
        """Mark component as ready."""
        self.readiness[component] = ready

    def set_alive(self, component: str, alive: bool = True) -> None:
        """Mark component as alive."""
        self.liveness[component] = alive

    def set_startup_complete(self) -> None:
        """Mark startup as complete."""
        self.startup_complete = True

    def is_ready(self) -> bool:
        """Check if all components are ready."""
        return all(self.readiness.values()) if self.readiness else self.startup_complete

    def is_alive(self) -> bool:
        """Check if all components are alive."""
        return all(self.liveness.values()) if self.liveness else True

    def get_health_status(self) -> Dict[str, Any]:
        """Get detailed health status."""
        return {
            "ready": self.is_ready(),
            "alive": self.is_alive(),
            "startup_complete": self.startup_complete,
            "readiness": self.readiness,
            "liveness": self.liveness,
            "timestamp": datetime.utcnow().isoformat(),
        }


class TracingIntegration:
    """OpenTelemetry integration for distributed tracing."""

    def __init__(self):
        self.spans: Dict[str, Dict[str, Any]] = {}
        self.tracer_enabled = False

    def enable_tracing(self) -> None:
        """Enable tracing."""
        self.tracer_enabled = True
        logger.info("Distributed tracing enabled")

    def disable_tracing(self) -> None:
        """Disable tracing."""
        self.tracer_enabled = False

    def start_span(self, span_id: str, operation: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Start a new span."""
        if not self.tracer_enabled:
            return

        self.spans[span_id] = {
            "operation": operation,
            "start_time": time.time(),
            "attributes": attributes or {},
            "end_time": None,
            "duration": None,
        }

    def end_span(self, span_id: str, status: str = "OK") -> None:
        """End a span."""
        if span_id not in self.spans:
            return

        span = self.spans[span_id]
        span["end_time"] = time.time()
        span["duration"] = span["end_time"] - span["start_time"]
        span["status"] = status

    def add_span_attribute(self, span_id: str, key: str, value: Any) -> None:
        """Add attribute to span."""
        if span_id in self.spans:
            self.spans[span_id]["attributes"][key] = value

    def get_trace(self, span_id: str) -> Optional[Dict[str, Any]]:
        """Get trace information."""
        return self.spans.get(span_id)

    def get_all_traces(self) -> Dict[str, Dict[str, Any]]:
        """Get all traces."""
        return self.spans.copy()


# Global instances
metrics_exporter = MetricsExporter()
structured_logger = StructuredLogger()
health_checker = HealthChecker()
tracing_integration = TracingIntegration()


class ObservabilityManager:
    """Central observability management."""

    def __init__(self):
        self.metrics = metrics_exporter
        self.logger = structured_logger
        self.health = health_checker
        self.tracing = tracing_integration

    def initialize(self) -> None:
        """Initialize observability components."""
        # Register standard metrics
        self.metrics.register_metric(
            PrometheusMetric(
                name="api_requests_total",
                type=MetricType.COUNTER,
                help="Total API requests",
                labels=["method", "endpoint", "status"],
            )
        )
        self.metrics.register_metric(
            PrometheusMetric(
                name="api_request_duration_seconds",
                type=MetricType.HISTOGRAM,
                help="API request duration in seconds",
                labels=["method", "endpoint"],
            )
        )
        self.metrics.register_metric(
            PrometheusMetric(
                name="active_agents",
                type=MetricType.GAUGE,
                help="Number of active agents",
            )
        )

        logger.info("Observability manager initialized")

    def get_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format."""
        return self.metrics.export_prometheus_format()


# Global observability manager
observability = ObservabilityManager()
