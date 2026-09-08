"""Central configuration loaded from environment variables.

This module intentionally contains no AI-model configuration. Local model discovery
and integration are deferred to Phase 8.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings with safe development defaults."""

    app_name: str = "document-intelligence-analytics"
    app_env: str = "development"
    log_level: str = "INFO"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "document_intelligence"
    postgres_user: str = "document_app"
    postgres_password: str = "change_me"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
