"""
Tests for Observability Service
"""

import pytest
from datetime import datetime
from apps.api.app.services.observability import (
    MetricsExporter,
    MetricType,
    PrometheusMetric,
    StructuredLogger,
    CorrelationContext,
    HealthChecker,
    TracingIntegration,
    observability,
)


class TestPrometheusMetric:
    """Test Prometheus metric definitions."""

    def test_metric_creation(self):
        """Test creating a metric."""
        metric = PrometheusMetric(
            name="test_metric",
            type=MetricType.COUNTER,
            help="Test metric",
        )
        assert metric.name == "test_metric"
        assert metric.type == MetricType.COUNTER

    def test_metric_to_prometheus_format(self):
        """Test converting metric to Prometheus format."""
        metric = PrometheusMetric(
            name="test_counter",
            type=MetricType.COUNTER,
            help="Test",
            value=42.0,
        )
        result = metric.to_prometheus_format()
        assert "test_counter" in result
        assert "42.0" in result

    def test_metric_with_labels(self):
        """Test metric with labels."""
        metric = PrometheusMetric(
            name="requests_total",
            type=MetricType.COUNTER,
            help="Total requests",
            label_values={"method": "GET", "status": "200"},
        )
        result = metric.to_prometheus_format()
        assert "method" in result
        assert "status" in result


class TestMetricsExporter:
    """Test metrics exporter."""

    def test_exporter_creation(self):
        """Test creating metrics exporter."""
        exporter = MetricsExporter()
        assert len(exporter.metrics) == 0

    def test_register_metric(self):
        """Test registering a metric."""
        exporter = MetricsExporter()
        metric = PrometheusMetric(
            name="test_metric",
            type=MetricType.COUNTER,
            help="Test",
        )
        exporter.register_metric(metric)
        assert "test_metric" in exporter.metrics

    def test_increment_counter(self):
        """Test incrementing a counter."""
        exporter = MetricsExporter()
        exporter.increment_counter("test_counter", amount=5)
        assert exporter.get_counter("test_counter") == 5

        exporter.increment_counter("test_counter", amount=3)
        assert exporter.get_counter("test_counter") == 8

    def test_set_gauge(self):
        """Test setting a gauge value."""
        exporter = MetricsExporter()
        exporter.set_gauge("cpu_usage", 75.5)
        assert exporter.get_gauge("cpu_usage") == 75.5

    def test_record_histogram(self):
        """Test recording histogram values."""
        exporter = MetricsExporter()
        exporter.record_histogram("request_duration", 100.0)
        exporter.record_histogram("request_duration", 200.0)
        exporter.record_histogram("request_duration", 300.0)

        stats = exporter.get_histogram_stats("request_duration")
        assert stats["count"] == 3
        assert stats["min"] == 100.0
        assert stats["max"] == 300.0
        assert stats["avg"] == 200.0

    def test_histogram_percentiles(self):
        """Test histogram percentile calculation."""
        exporter = MetricsExporter()
        for i in range(100):
            exporter.record_histogram("values", float(i))

        stats = exporter.get_histogram_stats("values")
        assert "p50" in stats
        assert "p95" in stats
        assert "p99" in stats

    def test_export_prometheus_format(self):
        """Test exporting in Prometheus format."""
        exporter = MetricsExporter()
        exporter.increment_counter("requests", 42)
        exporter.set_gauge("temperature", 23.5)

        prometheus_text = exporter.export_prometheus_format()
        assert "requests" in prometheus_text
        assert "temperature" in prometheus_text
        assert "42" in prometheus_text


class TestCorrelationContext:
    """Test correlation context."""

    def test_context_creation(self):
        """Test creating correlation context."""
        context = CorrelationContext(
            correlation_id="corr-123",
            request_id="req-456",
            user_id="user-1",
            tenant_id="tenant-1",
        )
        assert context.correlation_id == "corr-123"
        assert context.user_id == "user-1"

    def test_context_to_dict(self):
        """Test converting context to dictionary."""
        context = CorrelationContext(
            correlation_id="corr-123",
            request_id="req-456",
        )
        result = context.to_dict()
        assert result["correlation_id"] == "corr-123"
        assert result["request_id"] == "req-456"
        assert "start_time" in result


class TestStructuredLogger:
    """Test structured logging."""

    def test_logger_creation(self):
        """Test creating structured logger."""
        logger = StructuredLogger()
        assert logger.get_context() is None

    def test_set_context(self):
        """Test setting correlation context."""
        logger = StructuredLogger()
        context = CorrelationContext(
            correlation_id="corr-123",
            request_id="req-456",
        )
        logger.set_context(context)
        assert logger.get_context() == context

    def test_clear_context(self):
        """Test clearing context."""
        logger = StructuredLogger()
        context = CorrelationContext(
            correlation_id="corr-123",
            request_id="req-456",
        )
        logger.set_context(context)
        logger.clear_context()
        assert logger.get_context() is None

    def test_context_manager(self):
        """Test context manager."""
        logger = StructuredLogger()
        with logger.context(user_id="user-1", tenant_id="tenant-1") as ctx:
            assert ctx.user_id == "user-1"
            assert logger.get_context() == ctx

        assert logger.get_context() is None

    def test_log_info_with_context(self):
        """Test logging info with context."""
        logger = StructuredLogger()
        context = CorrelationContext(
            correlation_id="corr-123",
            request_id="req-456",
        )
        logger.set_context(context)

        # Should not raise exception
        logger.log_info("Test message", extra_field="value")

    def test_log_error_with_exception(self):
        """Test logging error with exception."""
        logger = StructuredLogger()
        try:
            raise ValueError("Test error")
        except ValueError as e:
            logger.log_error("An error occurred", error=e)


class TestHealthChecker:
    """Test health checker."""

    def test_health_checker_creation(self):
        """Test creating health checker."""
        checker = HealthChecker()
        assert checker.is_ready() is False
        assert checker.is_alive() is True

    def test_set_ready(self):
        """Test setting component as ready."""
        checker = HealthChecker()
        checker.set_ready("database", True)
        checker.set_ready("api", True)

        assert checker.is_ready() is True

    def test_set_alive(self):
        """Test setting component as alive."""
        checker = HealthChecker()
        checker.set_alive("worker", True)
        assert checker.is_alive() is True

    def test_startup_complete(self):
        """Test marking startup as complete."""
        checker = HealthChecker()
        assert checker.startup_complete is False
        checker.set_startup_complete()
        assert checker.startup_complete is True

    def test_get_health_status(self):
        """Test getting health status."""
        checker = HealthChecker()
        checker.set_ready("database", True)
        checker.set_startup_complete()

        status = checker.get_health_status()
        assert status["startup_complete"] is True
        assert "timestamp" in status


class TestTracingIntegration:
    """Test distributed tracing."""

    def test_tracing_creation(self):
        """Test creating tracing integration."""
        tracing = TracingIntegration()
        assert tracing.tracer_enabled is False

    def test_enable_disable_tracing(self):
        """Test enabling and disabling tracing."""
        tracing = TracingIntegration()
        tracing.enable_tracing()
        assert tracing.tracer_enabled is True

        tracing.disable_tracing()
        assert tracing.tracer_enabled is False

    def test_start_end_span(self):
        """Test starting and ending spans."""
        tracing = TracingIntegration()
        tracing.enable_tracing()

        tracing.start_span("span-1", "test_operation")
        assert "span-1" in tracing.spans

        tracing.end_span("span-1", status="OK")
        span = tracing.get_trace("span-1")
        assert span is not None
        assert span["status"] == "OK"
        assert span["duration"] is not None

    def test_add_span_attribute(self):
        """Test adding attributes to span."""
        tracing = TracingIntegration()
        tracing.enable_tracing()

        tracing.start_span("span-1", "test_operation")
        tracing.add_span_attribute("span-1", "user_id", "user-123")

        span = tracing.get_trace("span-1")
        assert span["attributes"]["user_id"] == "user-123"

    def test_get_all_traces(self):
        """Test getting all traces."""
        tracing = TracingIntegration()
        tracing.enable_tracing()

        tracing.start_span("span-1", "op1")
        tracing.start_span("span-2", "op2")
        tracing.end_span("span-1")

        all_traces = tracing.get_all_traces()
        assert len(all_traces) == 2


class TestObservabilityManager:
    """Test observability manager."""

    def test_initialization(self):
        """Test observability manager initialization."""
        observability.initialize()
        assert len(observability.metrics.metrics) >= 3

    def test_get_prometheus_metrics(self):
        """Test getting Prometheus metrics."""
        observability.metrics.increment_counter("test_counter", 5)
        prometheus_text = observability.get_prometheus_metrics()
        assert isinstance(prometheus_text, str)
        assert "test_counter" in prometheus_text
