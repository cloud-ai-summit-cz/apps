"""Application configuration."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Azure Authentication
    azure_tenant_id: str
    app_id_uri: str
    # Managed Identity Client ID (optional - for explicit identity selection)
    azure_client_id: str | None = None

    # Cosmos DB
    cosmos_endpoint: str
    cosmos_database_name: str = "toytripdb"
    cosmos_container_name: str = "stories"

    # Azure Service Bus
    service_bus_namespace: str
    story_jobs_queue_name: str = "story-jobs"

    # Azure OpenAI
    azure_openai_endpoint: str
    azure_openai_deployment: str = "gpt-4o-mini"
    azure_openai_api_version: str = "2024-08-01-preview"

    # Inter-service Communication
    trip_service_url: str = "http://localhost:8002"
    toy_service_url: str = "http://localhost:8001"
    geo_service_url: str = "http://localhost:8003"

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8004
    log_level: str = "INFO"

    # Worker Configuration
    worker_mode: bool = False
    max_concurrent_messages: int = 5

    # OpenTelemetry Configuration
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "story-service"
    service_version: str = "1.0.0"
    k8s_namespace: str | None = None
    k8s_pod_name: str | None = None
    k8s_node_name: str | None = None

    # Testing (optional)
    test_client_secret: str | None = None


# Global settings instance
settings = Settings()
