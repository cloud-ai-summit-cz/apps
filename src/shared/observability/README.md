# Shared Observability Module

OpenTelemetry instrumentation utilities for all services in the monorepo.

## Features

- **Unified Telemetry**: Single initialization for logs, metrics, and traces
- **OTLP Export**: All telemetry routed to OTLP collector (no vendor-specific exporters)
- **Auto-Instrumentation**: Automatic instrumentation for:
  - FastAPI (HTTP endpoints, request/response)
  - Azure SDK (Cosmos DB, Blob Storage operations)
  - HTTP clients (httpx, requests)
- **Structured Logging**: Application logs (INFO+) sent to OTLP, SDK logs (WARNING+) only
- **Custom Metrics & Spans**: Helper functions for business telemetry

## Usage

### 1. Setup (in main.py, before FastAPI app creation)

```python
from shared.observability import setup_instrumentation
import os

# Initialize OTEL before creating FastAPI app
setup_instrumentation(
    service_name=os.getenv("OTEL_SERVICE_NAME", "my-service"),
    service_version=os.getenv("SERVICE_VERSION", "1.0.0"),
    otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
    namespace=os.getenv("K8S_NAMESPACE"),
    pod_name=os.getenv("K8S_POD_NAME"),
    node_name=os.getenv("K8S_NODE_NAME"),
)

# Now create FastAPI app (auto-instrumented)
app = FastAPI()
```

### 2. Custom Spans

```python
from shared.observability import get_tracer

tracer = get_tracer(__name__)

@app.post("/toys")
async def register_toy(toy: ToyCreate):
    with tracer.start_as_current_span("toy.register") as span:
        span.set_attribute("toy_id", toy.id)
        span.set_attribute("user_id", user_id)
        span.set_attribute("is_admin", is_admin)
        
        # Business logic
        result = await toy_repo.create(toy)
        
        span.set_attribute("success", True)
        return result
```

### 3. Custom Metrics

```python
from shared.observability import get_meter

meter = get_meter(__name__)

# Create counter
toys_viewed = meter.create_counter(
    "toys_viewed_total",
    description="Total toy profile views",
    unit="1"
)

@app.get("/toys/{toy_id}")
async def get_toy(toy_id: str):
    # Increment counter with dimensions
    toys_viewed.add(1, {
        "user_id": user_id,
        "is_admin": str(is_admin).lower(),
        "toy_id": toy_id
    })
    
    return await toy_repo.get(toy_id)
```

### 4. Logging

All `logging.info()` and above automatically sent to OTLP:

```python
import logging

logger = logging.getLogger(__name__)

logger.info("Toy registered", extra={
    "toy_id": toy_id,
    "user_id": user_id
})
```

## Environment Variables

Add to `.env` and config:

```bash
# OTLP Collector endpoint (gRPC)
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317

# Service identification
OTEL_SERVICE_NAME=toy-service
SERVICE_VERSION=1.0.0

# Kubernetes context (optional, auto-injected in K8s)
K8S_NAMESPACE=default
K8S_POD_NAME=toy-deployment-abc123
K8S_NODE_NAME=aks-nodepool-12345
```

## Auto-Instrumentation Details

### FastAPI
- All HTTP endpoints automatically traced
- Metrics: request count, duration, status codes
- Context propagation for distributed tracing

### Azure SDK (Cosmos DB, Blob Storage)
- All operations automatically traced
- Spans include: operation type, container/blob names, latency
- Request Unit (RU) consumption tracked

### HTTP Clients
- Outbound HTTP calls traced with W3C context propagation
- Supports httpx and requests libraries

## Dependencies

Required packages (add to `pyproject.toml`):

```toml
[project]
dependencies = [
    "opentelemetry-api>=1.20.0",
    "opentelemetry-sdk>=1.20.0",
    "opentelemetry-exporter-otlp-proto-grpc>=1.20.0",
    "opentelemetry-instrumentation-fastapi>=0.41b0",
    "opentelemetry-instrumentation-httpx>=0.41b0",
    "opentelemetry-instrumentation-requests>=0.41b0",
    "azure-core-tracing-opentelemetry>=1.0.0",
]
```

## See Also

- [Platform Observability Strategy](../../../specs/platform/OBSERVABILITY.md)
- [OpenTelemetry Python Documentation](https://opentelemetry.io/docs/instrumentation/python/)
