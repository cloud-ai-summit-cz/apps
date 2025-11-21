"""
OpenTelemetry instrumentation setup for FastAPI services.

Configures:
- Distributed tracing with OTLP exporter
- Metrics collection
- Structured logging with OTLP export
- Auto-instrumentation for FastAPI, Azure SDK, HTTP clients

Usage:
    from shared.observability import setup_instrumentation
    
    setup_instrumentation(
        service_name="toy-service",
        service_version="1.0.0",
        otlp_endpoint="http://otel-collector:4317"
    )
"""

import logging
from typing import Optional

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry._logs import set_logger_provider

# Auto-instrumentation imports
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# Azure SDK tracing support
from azure.core.settings import settings as azure_settings


def setup_instrumentation(
    service_name: str,
    service_version: str,
    otlp_endpoint: str,
    namespace: Optional[str] = None,
    pod_name: Optional[str] = None,
    node_name: Optional[str] = None,
) -> None:
    """
    Initialize OpenTelemetry instrumentation with OTLP exporters.
    
    Args:
        service_name: Name of the service (e.g., "toy-service")
        service_version: Service version/commit SHA
        otlp_endpoint: OTLP collector endpoint (e.g., "http://otel-collector:4317")
        namespace: Kubernetes namespace (optional)
        pod_name: Pod name (optional)
        node_name: Node name (optional)
    """
    # Build resource attributes
    resource_attrs = {
        "service.name": service_name,
        "service.version": service_version,
    }
    
    if namespace:
        resource_attrs["k8s.namespace.name"] = namespace
    if pod_name:
        resource_attrs["k8s.pod.name"] = pod_name
    if node_name:
        resource_attrs["k8s.node.name"] = node_name
    
    resource = Resource.create(resource_attrs)
    
    # Setup tracing
    _setup_tracing(otlp_endpoint, resource)
    
    # Setup metrics
    _setup_metrics(otlp_endpoint, resource)
    
    # Setup logging
    _setup_logging(otlp_endpoint, resource, service_name)
    
    # Enable Azure SDK tracing
    azure_settings.tracing_implementation = "opentelemetry"
    
    # Auto-instrument libraries
    _setup_auto_instrumentation()


def _setup_tracing(otlp_endpoint: str, resource: Resource) -> None:
    """Configure distributed tracing with OTLP exporter."""
    trace_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    span_processor = BatchSpanProcessor(trace_exporter)
    
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(span_processor)
    trace.set_tracer_provider(tracer_provider)


def _setup_metrics(otlp_endpoint: str, resource: Resource) -> None:
    """Configure metrics collection with OTLP exporter."""
    metric_exporter = OTLPMetricExporter(endpoint=otlp_endpoint, insecure=True)
    metric_reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=60000)
    
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)


def _setup_logging(otlp_endpoint: str, resource: Resource, service_name: str) -> None:
    """
    Configure structured logging with OTLP exporter.
    
    Sets up:
    - OTLP log export for application logs
    - INFO level for application logger
    - WARNING level for Azure SDK and third-party libraries
    """
    log_exporter = OTLPLogExporter(endpoint=otlp_endpoint, insecure=True)
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
    set_logger_provider(logger_provider)
    
    # Attach OTLP handler to root logger
    otlp_handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(otlp_handler)
    
    # Set WARNING level for Azure SDK and other verbose libraries
    logging.getLogger("azure").setLevel(logging.WARNING)
    logging.getLogger("azure.core").setLevel(logging.WARNING)
    logging.getLogger("azure.cosmos").setLevel(logging.WARNING)
    logging.getLogger("azure.storage").setLevel(logging.WARNING)
    logging.getLogger("azure.identity").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    # Application logger at INFO level
    app_logger = logging.getLogger(service_name)
    app_logger.setLevel(logging.INFO)


def _setup_auto_instrumentation() -> None:
    """Enable auto-instrumentation for common libraries."""
    # FastAPI auto-instrumentation (instruments all HTTP endpoints)
    FastAPIInstrumentor().instrument()
    
    # HTTP client auto-instrumentation
    HTTPXClientInstrumentor().instrument()
    RequestsInstrumentor().instrument()
    
    # Note: Azure SDK (Cosmos DB, Blob Storage) tracing is enabled via
    # azure.core.settings.tracing_implementation = "opentelemetry"


def get_tracer(name: str) -> trace.Tracer:
    """
    Get a tracer instance for creating custom spans.
    
    Args:
        name: Tracer name (typically module or component name)
        
    Returns:
        Tracer instance for creating spans
        
    Example:
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("toy.register") as span:
            span.set_attribute("toy_id", toy_id)
            # ... business logic
    """
    return trace.get_tracer(name)


def get_meter(name: str) -> metrics.Meter:
    """
    Get a meter instance for creating custom metrics.
    
    Args:
        name: Meter name (typically module or component name)
        
    Returns:
        Meter instance for creating counters, gauges, histograms
        
    Example:
        meter = get_meter(__name__)
        toys_viewed = meter.create_counter(
            "toys_viewed_total",
            description="Total toy profile views"
        )
        toys_viewed.add(1, {"user_id": user_id, "is_admin": is_admin})
    """
    return metrics.get_meter(name)
