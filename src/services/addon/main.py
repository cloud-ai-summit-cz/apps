"""Main FastAPI application for Add-On Service."""
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared"))

from shared.observability import setup_instrumentation, get_tracer, get_meter, instrument_app
from shared.auth.middleware import AuthContextMiddleware

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from repositories import AddonRepository
from routes import addon_routes
from services import QueueService

# Initialize OpenTelemetry BEFORE creating FastAPI app
setup_instrumentation(
    service_name=settings.otel_service_name,
    service_version=settings.service_version,
    otlp_endpoint=settings.otel_exporter_otlp_endpoint,
    namespace=settings.k8s_namespace,
    pod_name=settings.k8s_pod_name,
    node_name=settings.k8s_node_name,
)

# Get logger after OTEL setup
logger = logging.getLogger(__name__)

# Get tracer and meter for custom instrumentation
tracer = get_tracer(__name__)
meter = get_meter(__name__)

# Custom business metrics
addons_ordered_counter = meter.create_counter(
    name="addons_ordered_total",
    description="Total addon orders created",
    unit="1"
)

addon_fulfillment_duration_histogram = meter.create_histogram(
    name="addon_fulfillment_duration_seconds",
    description="Addon fulfillment end-to-end duration",
    unit="s"
)

addon_queue_depth_gauge = meter.create_up_down_counter(
    name="addon_queue_depth",
    description="Current depth of addon fulfillment queue",
    unit="1"
)

addon_worker_retries_counter = meter.create_counter(
    name="addon_worker_retries_total",
    description="Total addon worker retry attempts",
    unit="1"
)

# Global instances
addon_repo: AddonRepository | None = None
queue_svc: QueueService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Initializes and cleans up resources (DB, Service Bus clients).
    """
    global addon_repo, queue_svc

    logger.info("Starting Add-On Service...")

    # Initialize repositories and services
    addon_repo = AddonRepository(
        cosmos_endpoint=settings.cosmos_endpoint,
        database_name=settings.cosmos_database_name,
        container_name=settings.cosmos_container_name,
    )

    queue_svc = QueueService(
        service_bus_namespace=settings.service_bus_namespace,
        queue_name=settings.service_bus_queue_name,
    )

    # Inject into routes module
    addon_routes.addon_repository = addon_repo
    addon_routes.queue_service = queue_svc
    addon_routes.tracer = tracer
    addon_routes.addons_ordered_counter = addons_ordered_counter
    addon_routes.addon_fulfillment_duration_histogram = addon_fulfillment_duration_histogram
    addon_routes.initialize_auth(settings.azure_tenant_id, settings.app_id_uri)
    addon_routes.set_service_urls(settings.trip_service_url, settings.toy_service_url)

    logger.info("Add-On Service initialized successfully")

    yield

    # Cleanup
    logger.info("Shutting down Add-On Service...")
    if addon_repo:
        await addon_repo.close()
    if queue_svc:
        await queue_svc.close()
    logger.info("Add-On Service shut down complete")


# Create FastAPI app
app = FastAPI(
    title="Add-On Service",
    description="Add-On Order Service for Stuffed Toy World Tour",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(addon_routes.router)

# Add auth context middleware
app.add_middleware(AuthContextMiddleware)

# Explicitly instrument the app to ensure OTEL middleware is the outermost
instrument_app(app)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "addon"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        log_level=settings.log_level.lower(),
    )
