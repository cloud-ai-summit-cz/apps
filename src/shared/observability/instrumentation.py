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
from opentelemetry import trace, metrics, baggage
from opentelemetry.sdk.trace import TracerProvider, SpanProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import Sampler, SamplingResult, Decision, ParentBased, ALWAYS_ON
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.metrics.view import View, ExplicitBucketHistogramAggregation
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry._logs import set_logger_provider
from opentelemetry.context import Context

# Auto-instrumentation imports
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# Azure SDK tracing support
from azure.core.settings import settings as azure_settings


class BaggageSpanProcessor(SpanProcessor):
    """
    Span processor that automatically attaches Baggage items as Span attributes.
    
    This ensures that context (like user_id, is_admin) propagated via Baggage
    is visible in every span for querying and filtering.
    """
    def on_start(self, span, parent_context: Optional[Context] = None) -> None:
        # Get all baggage from the current context
        baggage_items = baggage.get_all(context=parent_context)
        for key, value in baggage_items.items():
            span.set_attribute(key, value)

    def on_end(self, span) -> None:
        pass
    
    def shutdown(self) -> None:
        pass
    
    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


class NameFilteringSampler(Sampler):
    """
    Sampler that drops spans with specific names (e.g. noisy ASGI events).
    
    Used to filter out high-volume, low-value spans like 'http send'/'http receive'
    generated during streaming responses.
    """
    def __init__(self, delegate: Sampler, ignored_substrings: list[str]):
        self._delegate = delegate
        self._ignored_substrings = ignored_substrings

    def should_sample(
        self,
        parent_context: Optional[Context],
        trace_id: int,
        name: str,
        kind=None,
        attributes=None,
        links=None,
        trace_state=None,
    ) -> SamplingResult:
        for ignored in self._ignored_substrings:
            if ignored in name:
                return SamplingResult(Decision.DROP, attributes, trace_state)
        return self._delegate.should_sample(
            parent_context, trace_id, name, kind, attributes, links, trace_state
        )

    def get_description(self) -> str:
        return f"NameFilteringSampler({self._delegate.get_description()})"


# Note: Python Azure SDK does NOT emit rich semantic spans like .NET/Java
# Instead, manually instrument Cosmos DB and Blob Storage operations in repositories/services
# using the get_azure_metrics_meter() function below.


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
    
    # Setup metrics
    _setup_metrics(otlp_endpoint, resource)
    
    # Setup tracing
    _setup_tracing(otlp_endpoint, resource)
    
    # Setup logging
    _setup_logging(otlp_endpoint, resource, service_name)
    
    # Enable Azure SDK tracing
    azure_settings.tracing_implementation = "opentelemetry"
    
    # Auto-instrument libraries
    _setup_auto_instrumentation()


def instrument_app(app, excluded_urls: str = "/health") -> None:
    """
    Instrument a FastAPI application with OpenTelemetry middleware.
    
    Must be called AFTER adding other middleware (like Auth, CORS) to ensure
    OpenTelemetry runs FIRST (outermost layer) and extracts trace context.
    """
    FastAPIInstrumentor.instrument_app(app, excluded_urls=excluded_urls)


def _setup_tracing(otlp_endpoint: str, resource: Resource) -> None:
    """Configure distributed tracing with OTLP exporter."""
    trace_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    # Export spans every 5 seconds for faster feedback
    batch_processor = BatchSpanProcessor(
        trace_exporter,
        schedule_delay_millis=5000,  # Export every 5 seconds
        max_export_batch_size=512
    )
    
    # Custom processors
    baggage_processor = BaggageSpanProcessor()
    
    # Configure sampling to drop noisy ASGI spans
    # We wrap the default ParentBased(AlwaysOn) sampler
    base_sampler = ParentBased(root=ALWAYS_ON)
    sampler = NameFilteringSampler(
        delegate=base_sampler,
        ignored_substrings=["http send", "http receive"]
    )
    
    tracer_provider = TracerProvider(resource=resource, sampler=sampler)
    tracer_provider.add_span_processor(batch_processor)
    tracer_provider.add_span_processor(baggage_processor)
    
    trace.set_tracer_provider(tracer_provider)


def _setup_metrics(otlp_endpoint: str, resource: Resource) -> None:
    """Configure metrics collection with OTLP exporter and custom histogram buckets."""
    metric_exporter = OTLPMetricExporter(endpoint=otlp_endpoint, insecure=True)
    # Export metrics every 10 seconds for faster feedback
    metric_reader = PeriodicExportingMetricReader(
        metric_exporter,
        export_interval_millis=10000,  # Export every 10 seconds
        export_timeout_millis=5000
    )
    
    # Define custom histogram buckets for subsecond database operations
    # Buckets: 5ms, 10ms, 25ms, 50ms, 100ms, 250ms, 500ms, 1s, 2.5s, 5s, 10s
    histogram_view = View(
        instrument_type=metrics.Histogram,
        instrument_name="*_duration_seconds",  # Match all duration histograms
        aggregation=ExplicitBucketHistogramAggregation(
            boundaries=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        )
    )
    
    meter_provider = MeterProvider(
        resource=resource, 
        metric_readers=[metric_reader],
        views=[histogram_view]
    )
    metrics.set_meter_provider(meter_provider)


def _setup_logging(otlp_endpoint: str, resource: Resource, service_name: str) -> None:
    """
    Configure structured logging with OTLP exporter.
    
    Sets up:
    - OTLP log export for application logs
    - Respects LOG_LEVEL environment variable (default: INFO)
    - WARNING level for Azure SDK and third-party libraries
    """
    import os
    
    # Get log level from environment variable (default: INFO)
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    
    log_exporter = OTLPLogExporter(endpoint=otlp_endpoint, insecure=True)
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
    set_logger_provider(logger_provider)
    
    # Attach OTLP handler to root logger
    otlp_handler = LoggingHandler(level=log_level, logger_provider=logger_provider)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(otlp_handler)
    
    # Set WARNING level for Azure SDK and other verbose libraries (unless DEBUG is requested)
    azure_log_level = logging.WARNING if log_level > logging.DEBUG else logging.INFO
    logging.getLogger("azure").setLevel(azure_log_level)
    logging.getLogger("azure.core").setLevel(azure_log_level)
    logging.getLogger("azure.cosmos").setLevel(azure_log_level)
    logging.getLogger("azure.storage").setLevel(azure_log_level)
    logging.getLogger("azure.identity").setLevel(azure_log_level)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    # Application logger respects LOG_LEVEL
    app_logger = logging.getLogger(service_name)
    app_logger.setLevel(log_level)


def _setup_auto_instrumentation() -> None:
    """Enable auto-instrumentation for common libraries."""
    # Note: FastAPI instrumentation is NOT done here automatically anymore.
    # It must be done manually in the service using instrument_app(app)
    # to ensure correct middleware ordering (OTEL must run before Auth).
    
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


def get_azure_metrics_meter():
    """
    Get a meter for Azure SDK metrics (Cosmos DB, Blob Storage).
    
    Returns a tuple of (cosmos_counter, cosmos_histogram, cosmos_ru, blob_counter, blob_histogram).
    
    Note: Python Azure SDK does NOT emit rich semantic spans like .NET/Java.
    You must manually call these metrics in your repository/service code.
    
    Example:
        cosmos_ops, cosmos_duration, cosmos_ru, _, _ = get_azure_metrics_meter()
        
        start = time.time()
        result = await container.create_item(item)
        duration = time.time() - start
        
        attrs = get_metric_attributes({"operation": "create_item"})
        cosmos_ops.add(1, attrs)
        cosmos_duration.record(duration, attrs)
        if hasattr(result, '_request_charge'):
            cosmos_ru.add(result._request_charge, attrs)
    """
    meter = metrics.get_meter("shared.observability.azure_metrics")
    
    cosmos_ops = meter.create_counter(
        name="cosmos_operations_total",
        description="Total Cosmos DB operations",
        unit="1"
    )
    # Histogram buckets configured via View in _setup_metrics()
    cosmos_duration = meter.create_histogram(
        name="cosmos_operation_duration_seconds",
        description="Duration of Cosmos DB operations",
        unit="s"
    )
    cosmos_ru = meter.create_counter(
        name="cosmos_request_units_consumed",
        description="Total Request Units (RUs) consumed",
        unit="1"
    )
    blob_ops = meter.create_counter(
        name="blob_operations_total",
        description="Total Blob Storage operations",
        unit="1"
    )
    # Histogram buckets configured via View in _setup_metrics()
    blob_duration = meter.create_histogram(
        name="blob_operation_duration_seconds",
        description="Duration of Blob Storage operations",
        unit="s"
    )
    
    return cosmos_ops, cosmos_duration, cosmos_ru, blob_ops, blob_duration


def get_metric_attributes(base_attrs: dict) -> dict:
    """
    Get metric attributes by merging base attributes with baggage context.
    
    This ensures user context (user_id, is_admin, user_role) from baggage
    is automatically included in all metrics for filtering and analysis.
    
    Args:
        base_attrs: Base attributes (operation, container, etc.)
        
    Returns:
        Combined attributes including baggage items
        
    Example:
        attrs = get_metric_attributes({"operation": "read_item", "container": "toys"})
        # Returns: {"operation": "read_item", "container": "toys", "user_id": "...", "is_admin": "true"}
        cosmos_ops.add(1, attrs)
    """
    # Start with base attributes
    attrs = dict(base_attrs)
    
    # Add baggage items (user_id, is_admin, user_role, etc.)
    baggage_items = baggage.get_all()
    for key, value in baggage_items.items():
        if key not in attrs:  # Don't override base attributes
            attrs[key] = value
    
    return attrs
