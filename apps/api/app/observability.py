"""
Observability Setup

Configures distributed tracing, metrics collection, and logging for the application.
Integrates with OpenTelemetry, Prometheus, and Langfuse.
"""

import logging
import logging.handlers
from typing import Optional

from fastapi import FastAPI
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from prometheus_client import Counter, Histogram, Gauge

from app.config import settings

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """
    Setup structured logging configuration.

    Configures JSON logging with request IDs and structured context.
    """
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt=(
            "%(asctime)s - %(name)s - %(levelname)s - "
            "%(message)s - %(request_id)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(detailed_formatter)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    # File handler (if not in debug mode)
    if not settings.DEBUG:
        file_handler = logging.handlers.RotatingFileHandler(
            filename="logs/gbrain-api.log",
            maxBytes=100 * 1024 * 1024,  # 100MB
            backupCount=10,
        )
        file_handler.setFormatter(detailed_formatter)
        file_handler.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)

    root_logger.addHandler(console_handler)

    logger.info(f"Logging configured at level {settings.LOG_LEVEL}")


def setup_tracing(app: FastAPI) -> None:
    """
    Setup distributed tracing with Jaeger.

    Args:
        app: FastAPI application instance
    """
    if not settings.ENABLE_TRACING:
        logger.info("Tracing disabled")
        return

    logger.info("Setting up distributed tracing...")

    try:
        # Create Jaeger exporter
        jaeger_exporter = JaegerExporter(
            agent_host_name=settings.JAEGER_AGENT_HOST,
            agent_port=settings.JAEGER_AGENT_PORT,
        )

        # Create tracer provider
        trace_provider = TracerProvider()
        trace_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))

        # Set global tracer provider
        trace.set_tracer_provider(trace_provider)

        # Instrument FastAPI
        FastAPIInstrumentor.instrument_app(app)

        # Instrument SQLAlchemy
        SQLAlchemyInstrumentor().instrument()

        # Instrument Redis
        RedisInstrumentor().instrument()

        logger.info("Distributed tracing configured")

    except Exception as e:
        logger.error(f"Failed to setup tracing: {e}", exc_info=True)


def setup_metrics(app: FastAPI) -> None:
    """
    Setup metrics collection with Prometheus.

    Args:
        app: FastAPI application instance
    """
    if not settings.ENABLE_METRICS:
        logger.info("Metrics disabled")
        return

    logger.info("Setting up metrics collection...")

    try:
        # Create Prometheus metric reader
        prometheus_reader = PrometheusMetricReader()

        # Create meter provider
        meter_provider = MeterProvider(metric_readers=[prometheus_reader])
        metrics.set_meter_provider(meter_provider)

        meter = metrics.get_meter(__name__)

        # Define custom metrics
        request_counter = meter.create_counter(
            name="http_requests_total",
            description="Total HTTP requests",
            unit="1",
        )

        request_duration = meter.create_histogram(
            name="http_request_duration_seconds",
            description="HTTP request duration in seconds",
            unit="s",
        )

        active_requests = meter.create_up_down_counter(
            name="http_active_requests",
            description="Active HTTP requests",
            unit="1",
        )

        # Skill execution metrics
        skill_executions = meter.create_counter(
            name="skill_executions_total",
            description="Total skill executions",
            unit="1",
        )

        skill_duration = meter.create_histogram(
            name="skill_execution_duration_seconds",
            description="Skill execution duration",
            unit="s",
        )

        # Agent metrics
        agent_executions = meter.create_counter(
            name="agent_executions_total",
            description="Total agent executions",
            unit="1",
        )

        agent_success_rate = meter.create_gauge(
            name="agent_success_rate",
            description="Agent execution success rate",
            unit="1",
        )

        # Database metrics
        db_query_duration = meter.create_histogram(
            name="db_query_duration_seconds",
            description="Database query duration",
            unit="s",
        )

        # Store metrics in app state for use in handlers
        app.state.metrics = {
            "request_counter": request_counter,
            "request_duration": request_duration,
            "active_requests": active_requests,
            "skill_executions": skill_executions,
            "skill_duration": skill_duration,
            "agent_executions": agent_executions,
            "agent_success_rate": agent_success_rate,
            "db_query_duration": db_query_duration,
        }

        logger.info("Metrics collection configured")

    except Exception as e:
        logger.error(f"Failed to setup metrics: {e}", exc_info=True)


def setup_observability(app: FastAPI) -> None:
    """
    Setup all observability features.

    Args:
        app: FastAPI application instance
    """
    logger.info("Setting up observability...")

    setup_logging()
    setup_tracing(app)
    setup_metrics(app)

    logger.info("Observability setup complete")
