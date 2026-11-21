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


runner_settings = RunnerSettings()
