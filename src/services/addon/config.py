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
    azure_client_id: str | None = None

    # Cosmos DB
    cosmos_endpoint: str
    cosmos_database_name: str = "toytripdb"
    cosmos_container_name: str = "addons"

    # Service Bus
    service_bus_namespace: str
    service_bus_queue_name: str = "addon-fulfill"

    # Inter-service Communication
    trip_service_url: str = "http://localhost:8002"
    toy_service_url: str = "http://localhost:8001"
    demo_media_service_url: str = "http://localhost:8005"

    # Blob Storage
    storage_account_url: str
    blob_container_fulfillment: str = "fulfillment"

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8003
    log_level: str = "INFO"

    # OpenTelemetry Configuration
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "addon-service"
    service_version: str = "1.0.0"
    k8s_namespace: str | None = None
    k8s_pod_name: str | None = None
    k8s_node_name: str | None = None


# Global settings instance
settings = Settings()
