"""Runner Process Schemas and Performance Summary Models."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class RunnerProcessStatus(str, Enum):
    """Process lifecycle states."""
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


class RunnerMetadata(BaseModel):
    """Runtime process metadata for an active or completed Locust run."""
    run_id: str
    pid: Optional[int] = None
    status: RunnerProcessStatus
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    exit_code: Optional[int] = None
    error_message: Optional[str] = None
    artifacts_dir: str


class LocustPerformanceMetrics(BaseModel):
    """Parsed real performance metrics extracted from Locust execution."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    requests_per_second: float = 0.0
    failures_per_second: float = 0.0
    active_users: int = 0
    min_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    median_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p90_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
