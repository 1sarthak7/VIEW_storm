"""Pydantic Schemas for Worker Node Capacity Calibration."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CalibrationStepResult(BaseModel):
    """Telemetry and performance metrics captured during a single calibration step."""
    users: int
    duration_seconds: int
    requests_per_second: float
    total_requests: int
    accepted_events: int
    error_rate_pct: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    worker_cpu_pct: float
    worker_ram_mb: float
    worker_ram_pct: float
    is_saturated: bool
    saturation_reason: Optional[str] = None


class WorkerCalibrationRequest(BaseModel):
    """Execution parameters for worker capacity calibration."""
    steps: List[int] = Field(default_factory=lambda: [10, 25, 50, 100, 250, 500])
    step_duration_seconds: int = Field(default=15, ge=5, le=60)
    target_environment: str = "local"
    max_cpu_pct_threshold: float = Field(default=85.0, ge=50.0, le=95.0)
    max_error_rate_threshold: float = Field(default=2.0, ge=0.5, le=10.0)
    max_p95_latency_threshold_ms: float = Field(default=1500.0, ge=100.0, le=10000.0)
    notes: Optional[str] = None


class WorkerCalibrationResponse(BaseModel):
    """Summary and step metrics of a worker capacity calibration."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    worker_node_id: Optional[str]
    worker_identifier: str
    cpu_cores: int
    total_memory_mb: float
    steps_tested: Optional[List[Dict[str, Any]]] = None
    max_stable_users: int
    max_stable_rps: float
    saturation_bottleneck: Optional[str]
    recommended_capacity: int
    notes: Optional[str]
    created_at: datetime
