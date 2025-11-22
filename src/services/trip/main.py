"""Main FastAPI application for Trip Service."""
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared"))

from shared.observability import setup_instrumentation, get_tracer, get_meter
from shared.auth.middleware import AuthContextMiddleware

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from repositories import TripRepository
from routes import trip_routes
from services import GalleryService

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
trips_viewed_counter = meter.create_counter(
    name="trips_viewed_total",
    description="Total trip detail views",
    unit="1"
)

trips_created_counter = meter.create_counter(
    name="trips_created_total",
    description="Total trip creations",
    unit="1"
)

gallery_images_viewed_counter = meter.create_counter(
    name="gallery_images_viewed_total",
    description="Total gallery image views",
    unit="1"
)

# Global instances
trip_repo: TripRepository | None = None
gallery_svc: GalleryService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Initializes and cleans up resources (DB, Blob clients).
    """
    global trip_repo, gallery_svc

    logger.info("Starting Trip Service...")

    # Initialize repositories and services
    trip_repo = TripRepository(
        cosmos_endpoint=settings.cosmos_endpoint,
        database_name=settings.cosmos_database_name,
        container_name=settings.cosmos_container_name,
    )

    gallery_svc = GalleryService(
        storage_account_url=settings.storage_account_url,
        container_name=settings.blob_container_gallery,
    )

    # Inject into routes module
    trip_routes.trip_repository = trip_repo
    trip_routes.gallery_service = gallery_svc
    trip_routes.tracer = tracer
    trip_routes.trips_viewed_counter = trips_viewed_counter
    trip_routes.trips_created_counter = trips_created_counter
    trip_routes.gallery_images_viewed_counter = gallery_images_viewed_counter
    trip_routes.initialize_auth(settings.azure_tenant_id, settings.app_id_uri)
    trip_routes.set_toy_service_url(settings.toy_service_url)

    logger.info("Trip Service initialized successfully")

    yield

    # Cleanup
    logger.info("Shutting down Trip Service...")
    if trip_repo:
        await trip_repo.close()
    if gallery_svc:
        await gallery_svc.close()
    logger.info("Trip Service shut down complete")


# Create FastAPI app
app = FastAPI(
    title="Trip Service",
    description="Trip & Gallery Service for Stuffed Toy World Tour",
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
app.include_router(trip_routes.router)

# Add observability middleware
app.add_middleware(AuthContextMiddleware)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "trip"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        log_level=settings.log_level.lower(),
    )
