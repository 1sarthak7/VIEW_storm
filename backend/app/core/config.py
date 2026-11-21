"""ViewStorm Core Configuration Module."""

from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """ViewStorm Application Settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    project_name: str = "ViewStorm"
    version: str = "1.0.0"
    environment: str = "local"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    
    # Authorized target environments
    allowed_target_environments: List[str] = Field(
        default_factory=lambda: ["local", "test", "staging-authorized"]
    )
    default_target_environment: str = "local"
    max_local_virtual_users: int = 1000
    
    # Infrastructure placeholders (for Milestone 2+)
    redis_url: str = "redis://localhost:6379/0"
    postgres_url: str = "postgresql+asyncpg://viewstorm:viewstorm_password@localhost:5432/viewstorm"
    
    # Ingestion settings
    idempotency_cache_ttl_seconds: int = 3600
    metrics_retention_points: int = 300


settings = Settings()
