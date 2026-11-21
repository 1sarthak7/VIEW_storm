"""Locust Runner Configuration and Target Allowlisting."""

from pathlib import Path
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RunnerSettings(BaseSettings):
    """Configuration settings for managing local Locust runner processes."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Base workspace directory
    base_dir: Path = Path(__file__).resolve().parent.parent.parent.parent
    locustfile_path: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parent.parent.parent.parent / "simulator" / "locustfile.py"
    )
    artifacts_dir: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parent.parent.parent.parent / "artifacts" / "runs"
    )

    # Security target allowlist
    target_local_url: str = Field(
        default="http://127.0.0.1:8000",
        alias="VIEWSTORM_TARGET_LOCAL_URL"
    )
    allowed_target_hosts: List[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:8000",
            "http://localhost:8000",
            "http://[::1]:8000",
        ]
    )

    # Process controls
    stop_grace_period_seconds: float = 5.0
    metrics_poll_interval_seconds: float = 2.0
    max_concurrent_runners: int = 3

    # Distributed Master-Worker Settings
    master_bind_host: str = Field(default="0.0.0.0", alias="VIEWSTORM_MASTER_BIND_HOST")
    master_bind_port: int = Field(default=5557, alias="VIEWSTORM_MASTER_BIND_PORT")
    master_advertise_host: str = Field(default="127.0.0.1", alias="VIEWSTORM_MASTER_ADVERTISE_HOST")
    expect_workers_max_wait: int = Field(default=30, alias="VIEWSTORM_EXPECT_WORKERS_MAX_WAIT")
    worker_heartbeat_timeout_seconds: int = Field(default=30, alias="VIEWSTORM_WORKER_HEARTBEAT_TIMEOUT_SECONDS")
    worker_auth_token: str = Field(default="viewstorm-secret-token", alias="VIEWSTORM_WORKER_AUTH_TOKEN")
    pinned_locust_version: str = Field(default="2.47.0", alias="VIEWSTORM_PINNED_LOCUST_VERSION")


runner_settings = RunnerSettings()
