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
from opentelemetry import trace, metrics, baggage
from opentelemetry.sdk.trace import TracerProvider, SpanProcessor
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


class AzureSDKMetricsSpanProcessor(SpanProcessor):
    """
    Span processor that generates metrics from Azure SDK spans.
    
    Since Azure SDK tracing only produces spans, this processor observes them
    and updates counters/histograms for Blob Storage and Cosmos DB operations.
    """
    def __init__(self):
        meter = metrics.get_meter("shared.observability.azure_metrics")
        
        # Blob Storage Metrics
        self.blob_ops_counter = meter.create_counter(
            name="blob_operations_total",
            description="Total Blob Storage operations",
            unit="1"
        )
        self.blob_duration_histogram = meter.create_histogram(
            name="blob_operation_duration_seconds",
            description="Duration of Blob Storage operations",
            unit="s"
        )
        
        # Cosmos DB Metrics
        self.cosmos_ops_counter = meter.create_counter(
            name="cosmos_operations_total",
            description="Total Cosmos DB operations",
            unit="1"
        )
        self.cosmos_duration_histogram = meter.create_histogram(
            name="cosmos_operation_duration_seconds",
            description="Duration of Cosmos DB operations",
            unit="s"
        )
        self.cosmos_ru_counter = meter.create_counter(
            name="cosmos_request_units_consumed",
            description="Total Request Units (RUs) consumed",
            unit="1"
        )

    def on_start(self, span, parent_context: Optional[Context] = None) -> None:
        pass

    def on_end(self, span) -> None:
        # Check if this is an Azure SDK span
        # Azure SDK spans typically have 'az.namespace' attribute
        attributes = span.attributes or {}
        namespace = attributes.get("az.namespace")
        
        if not namespace:
            return
            
        duration_s = (span.end_time - span.start_time) / 1e9
        
        if namespace == "Microsoft.Storage":
            # Blob Storage Operation
            op_type = attributes.get("graphql.operation.name") or span.name
            self.blob_ops_counter.add(1, {"operation": op_type})
            self.blob_duration_histogram.record(duration_s, {"operation": op_type})
            
        elif namespace == "Microsoft.DocumentDB":
            # Cosmos DB Operation
            op_type = span.name
            self.cosmos_ops_counter.add(1, {"operation": op_type})
            self.cosmos_duration_histogram.record(duration_s, {"operation": op_type})
            
            # Extract Request Units if available (often in 'x-ms-request-charge' attribute)
            # Note: Azure SDK might put it in different attributes depending on version
            ru_charge = attributes.get("x-ms-request-charge")
            if ru_charge:
                try:
                    self.cosmos_ru_counter.add(float(ru_charge), {"operation": op_type})
                except (ValueError, TypeError):
                    pass

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


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
    batch_processor = BatchSpanProcessor(trace_exporter)
    
    # Custom processors
    baggage_processor = BaggageSpanProcessor()
    metrics_processor = AzureSDKMetricsSpanProcessor()
    
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(batch_processor)
    tracer_provider.add_span_processor(baggage_processor)
    tracer_provider.add_span_processor(metrics_processor)
    
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
