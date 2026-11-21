"""ViewStorm Core Configuration Module."""

from typing import List, Optional
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
    environment: str = Field(default="local", alias="APP_ENV")
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    # Authorized target environments
    allowed_target_environments: List[str] = Field(
        default_factory=lambda: ["local", "test", "staging-authorized"]
    )
    default_target_environment: str = "local"
    max_local_virtual_users: int = 1000

    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_pool_size: int = 50

    # PostgreSQL Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://viewstorm:viewstorm_password@localhost:5432/viewstorm",
        alias="DATABASE_URL"
    )
    postgres_user: Optional[str] = Field(default="viewstorm", alias="POSTGRES_USER")
    postgres_password: Optional[str] = Field(default="viewstorm_password", alias="POSTGRES_PASSWORD")
    postgres_db: Optional[str] = Field(default="viewstorm", alias="POSTGRES_DB")

    # Ingestion & retention settings
    idempotency_cache_ttl_seconds: int = 86400  # 24 hours
    stats_retention_ttl_seconds: int = 604800   # 7 days
    metrics_retention_points: int = 300

    # Security & RBAC Configuration
    secret_key: str = Field(
        default="viewstorm-prod-secret-key-hardening-2026-super-secure",
        alias="SECRET_KEY",
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours
    auth_enabled: bool = Field(default=True, alias="AUTH_ENABLED")
    admin_username: str = Field(default="admin", alias="VIEWSTORM_ADMIN_USERNAME")
    admin_password: Optional[str] = Field(default=None, alias="VIEWSTORM_ADMIN_PASSWORD")
    admin_email: str = Field(default="admin@viewstorm.local", alias="VIEWSTORM_ADMIN_EMAIL")
    bootstrap_token: Optional[str] = Field(default=None, alias="VIEWSTORM_BOOTSTRAP_TOKEN")
    bootstrap_token_file: str = Field(
        default=".viewstorm_bootstrap.token",
        alias="VIEWSTORM_BOOTSTRAP_FILE",
    )
    login_rate_limit_max_attempts: int = 5
    login_rate_limit_window_seconds: int = 300

    # Emergency Stop Keys
    emergency_stop_key: str = "viewstorm:emergency_stop:active"
    emergency_stop_reason_key: str = "viewstorm:emergency_stop:reason"
    emergency_stop_meta_key: str = "viewstorm:emergency_stop:meta"


settings = Settings()
