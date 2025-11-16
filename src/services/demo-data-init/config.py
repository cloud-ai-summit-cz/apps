"""Settings module for the demo data init service."""
from __future__ import annotations

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_assets_path() -> Path:
    repo_data = Path(__file__).resolve().parents[3] / "tools" / "data"
    return repo_data if repo_data.exists() else Path(__file__).resolve().parent / "data"


class Settings(BaseSettings):
    """Central application configuration loaded from environment."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    api_host: str = Field("0.0.0.0", alias="API_HOST")
    api_port: int = Field(8080, alias="API_PORT")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    azure_tenant_id: str = Field(..., alias="AZURE_TENANT_ID")
    app_id_uri: str = Field(..., alias="APP_ID_URI")

    demo_data_role_value: str = Field("Admin.FullAccess", alias="DEMO_DATA_ROLE_VALUE")
    toy_service_url: str = Field(..., alias="TOY_SERVICE_URL")
    trip_service_url: str = Field(..., alias="TRIP_SERVICE_URL")

    assets_path: Path = Field(default_factory=_default_assets_path, alias="DEMO_DATA_ASSETS_PATH")

    http_timeout_seconds: int = Field(20, alias="DEMO_DATA_HTTP_TIMEOUT")
    max_retry_attempts: int = Field(3, alias="DEMO_DATA_HTTP_RETRIES")


settings = Settings()
