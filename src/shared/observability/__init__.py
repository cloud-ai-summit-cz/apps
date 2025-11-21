"""
Shared OpenTelemetry instrumentation utilities.

Provides centralized setup for logs, metrics, and traces with auto-instrumentation
for FastAPI, Azure SDK (Cosmos DB, Blob Storage), and HTTP clients.
"""

from .instrumentation import setup_instrumentation, get_tracer, get_meter

__all__ = ["setup_instrumentation", "get_tracer", "get_meter"]
