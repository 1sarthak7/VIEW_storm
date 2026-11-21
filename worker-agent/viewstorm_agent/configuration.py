"""Worker Agent Configuration."""

import os
import platform
import uuid
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_default_identifier() -> str:
    # Stable identifier based on hostname + mac
    node_uuid = uuid.getnode()
    return f"worker-{platform.node()}-{node_uuid:012x}"


class AgentSettings(BaseSettings):
    """Configuration settings for the outbound WorkerAgent."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    server_url: str = Field(default="http://127.0.0.1:8000", alias="VIEWSTORM_SERVER_URL")
    auth_token: str = Field(default="viewstorm-secret-token", alias="VIEWSTORM_WORKER_AUTH_TOKEN")
    worker_identifier: str = Field(default_factory=get_default_identifier, alias="VIEWSTORM_WORKER_IDENTIFIER")
    worker_name: str = Field(default=f"agent-{platform.node()}", alias="VIEWSTORM_WORKER_NAME")
    capacity: int = Field(default=100, ge=1, alias="VIEWSTORM_WORKER_CAPACITY")

    heartbeat_interval_seconds: float = Field(default=5.0, alias="VIEWSTORM_HEARTBEAT_INTERVAL")
    poll_interval_seconds: float = Field(default=2.0, alias="VIEWSTORM_POLL_INTERVAL")

    locustfile_path: Optional[Path] = Field(
        default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "simulator" / "locustfile.py"
    )


agent_settings = AgentSettings()
