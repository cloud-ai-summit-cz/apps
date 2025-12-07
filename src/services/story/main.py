"""Main FastAPI application for Story Service."""
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
from repositories import StoryRepository
from routes import story_routes
from services import StoryGenerationService

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
stories_generated_counter = meter.create_counter(
    name="story_compositions_requested_total",
    description="Total story generation requests",
    unit="1"
)

stories_viewed_counter = meter.create_counter(
    name="stories_viewed_total",
    description="Total story views",
    unit="1"
)

story_generation_duration = meter.create_histogram(
    name="story_generation_duration_seconds",
    description="Story generation duration",
    unit="s"
)

story_jobs_pending = meter.create_gauge(
    name="story_jobs_pending",
    description="Number of pending story jobs in queue",
    unit="1"
)

# Global instances
story_repo: StoryRepository | None = None
story_gen_svc: StoryGenerationService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Initializes and cleans up resources (Cosmos DB, OpenAI clients).
    """
    global story_repo, story_gen_svc

    logger.info("Starting Story Service...")

    # Initialize repository
    story_repo = StoryRepository(
        cosmos_endpoint=settings.cosmos_endpoint,
        database_name=settings.cosmos_database_name,
        container_name=settings.cosmos_container_name,
    )

    # Initialize story generation service
    story_gen_svc = StoryGenerationService(
        azure_openai_endpoint=settings.azure_openai_endpoint,
        azure_openai_deployment=settings.azure_openai_deployment,
        azure_openai_api_version=settings.azure_openai_api_version,
        trip_service_url=settings.trip_service_url,
        toy_service_url=settings.toy_service_url,
        geo_service_url=settings.geo_service_url,
    )

    # Inject into routes module
    story_routes.story_repository = story_repo
    story_routes.story_generation_service = story_gen_svc
    story_routes.tracer = tracer
    story_routes.stories_generated_counter = stories_generated_counter
    story_routes.stories_viewed_counter = stories_viewed_counter
    story_routes.initialize_auth(settings.azure_tenant_id, settings.app_id_uri)

    logger.info("Story Service initialized successfully")

    yield

    # Cleanup
    logger.info("Shutting down Story Service...")
    if story_repo:
        await story_repo.close()
    logger.info("Story Service shut down complete")


# Create FastAPI app
app = FastAPI(
    title="Story Service",
    description="AI-powered Story Generation Service for Stuffed Toy World Tour",
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
app.include_router(story_routes.router)

# Add observability middleware
app.add_middleware(AuthContextMiddleware)

# Explicitly instrument the app to ensure OTEL middleware is the outermost
instrument_app(app)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "story"}


@app.get("/healthz")
async def healthz():
    """Kubernetes health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        log_level=settings.log_level.lower(),
    )
