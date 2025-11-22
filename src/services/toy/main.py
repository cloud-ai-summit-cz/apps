"""Main FastAPI application for Toy Service."""
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
from repositories import ToyRepository
from routes import toy_routes
from services import BlobService

# Initialize OpenTelemetry BEFORE creating FastAPI app
# This ensures auto-instrumentation captures all FastAPI operations
setup_instrumentation(
    service_name=settings.otel_service_name,
    service_version=settings.service_version,
    otlp_endpoint=settings.otel_exporter_otlp_endpoint,
    namespace=settings.k8s_namespace,
    pod_name=settings.k8s_pod_name,
    node_name=settings.k8s_node_name,
)

# Get logger after OTEL setup (will auto-export to OTLP)
logger = logging.getLogger(__name__)

# Get tracer and meter for custom instrumentation
tracer = get_tracer(__name__)
meter = get_meter(__name__)

# Custom business metrics
toys_viewed_counter = meter.create_counter(
    name="toys_viewed_total",
    description="Total toy profile views",
    unit="1"
)

toys_registered_counter = meter.create_counter(
    name="toys_registered_total",
    description="Total toy registrations",
    unit="1"
)

# Global instances
toy_repo: ToyRepository | None = None
blob_svc: BlobService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Initializes and cleans up resources (DB, Blob clients).
    """
    global toy_repo, blob_svc

    logger.info("Starting Toy Service...")

    # Initialize repositories and services
    toy_repo = ToyRepository(
        cosmos_endpoint=settings.cosmos_endpoint,
        database_name=settings.cosmos_database_name,
        container_name=settings.cosmos_container_name,
    )

    blob_svc = BlobService(
        storage_account_url=settings.storage_account_url,
        container_name=settings.blob_container_avatars,
    )

    # Inject into routes module
    toy_routes.toy_repository = toy_repo
    toy_routes.blob_service = blob_svc
    toy_routes.tracer = tracer
    toy_routes.toys_viewed_counter = toys_viewed_counter
    toy_routes.toys_registered_counter = toys_registered_counter
    toy_routes.initialize_auth(settings.azure_tenant_id, settings.app_id_uri)

    logger.info("Toy Service initialized successfully")

    yield

    # Cleanup
    logger.info("Shutting down Toy Service...")
    if toy_repo:
        await toy_repo.close()
    if blob_svc:
        await blob_svc.close()
    logger.info("Toy Service shut down complete")


# Create FastAPI app
app = FastAPI(
    title="Toy Service",
    description="Toy Registry & Profiles Service for Stuffed Toy World Tour",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware (configure as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(toy_routes.router)

# Add observability middleware
app.add_middleware(AuthContextMiddleware)

# Explicitly instrument the app to ensure OTEL middleware is the outermost (runs first)
instrument_app(app)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "toy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
