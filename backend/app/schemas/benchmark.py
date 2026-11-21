"""Pydantic Schemas for Controlled Large-Scale Benchmarking Framework."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class BenchmarkStage(BaseModel):
    """Specification of a ramp-up or stabilization stage."""
    stage_number: int
    name: str
    target_users: int
    duration_seconds: int
    is_stabilization: bool = False


class BenchmarkProfile(BaseModel):
    """Specification of a standardized benchmark load test profile."""
    name: str
    description: str
    virtual_users: int
    spawn_rate: float
    duration_seconds: int
    recommended_mode: str = "local"
    max_error_rate_pct: float
    max_p95_latency_ms: float
    requires_explicit_approval: bool = False
    min_worker_nodes: int = 1
    min_physical_nodes: Optional[int] = 1
    min_worker_processes: Optional[int] = 1
    ramp_duration_seconds: Optional[int] = None
    steady_state_duration_seconds: Optional[int] = None
    ramp_down_duration_seconds: Optional[int] = None
    stages: Optional[List[BenchmarkStage]] = None


class PreflightCheckRequest(BaseModel):
    """Request to validate cluster readiness before launching a benchmark."""
    profile_name: str = Field(..., pattern="^(smoke|baseline|small|medium|large|extended|high_capacity|extreme|intermediate_150k|massive|target)$")
    execution_mode: Optional[str] = Field(None, pattern="^(local|distributed)$")


class PreflightCheckResponse(BaseModel):
    """Readiness assessment result across cluster infrastructure."""
    ready: bool
    profile_name: str
    required_users: int
    available_worker_nodes: int
    total_worker_capacity: int
    redis_ok: bool
    db_ok: bool
    memory_ok: bool
    requires_explicit_approval: bool
    messages: List[str]
    target_api_ok: Optional[bool] = True
    dataplane_ok: Optional[bool] = True
    artifact_storage_ok: Optional[bool] = True
    zeromq_ok: Optional[bool] = True
    active_worker_processes: Optional[int] = 0


class BenchmarkRunRequest(BaseModel):
    """Execution request for a standardized benchmark."""
    profile_name: str = Field(..., pattern="^(smoke|baseline|small|medium|large|extended|high_capacity|extreme|intermediate_150k|massive|target)$")
    execution_mode: Optional[str] = Field(None, pattern="^(local|distributed)$")
    target_environment: str = Field("local")
    approval_confirmed: bool = Field(default=False, description="Explicit operator authorization for high/extreme profiles")
    notes: Optional[str] = None


class ThresholdEvaluation(BaseModel):
    """Evaluation of SLA compliance against profile thresholds."""
    passed: bool
    max_error_rate_pct: float
    actual_error_rate_pct: float
    error_rate_passed: bool
    max_p95_latency_ms: float
    actual_p95_latency_ms: float
    p95_latency_passed: bool


class BenchmarkResultResponse(BaseModel):
    """Persistent benchmark execution outcome with full telemetry and environment metadata."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    profile_name: str
    test_type: str
    run_id: Optional[str]
    target_environment: str
    virtual_users: int
    actual_active_users: int
    spawn_rate: float
    duration_seconds: int
    total_requests: int
    accepted_events: int
    requests_per_second: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    max_latency_ms: float
    error_rate_pct: float
    passed_thresholds: bool
    preflight_passed: bool
    approval_operator: Optional[str] = None
    abort_reason: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    threshold_evaluation: Optional[ThresholdEvaluation] = None

    # Environment & reproducibility snapshots
    software_metadata: Optional[Dict[str, Any]] = None
    infrastructure_metadata: Optional[Dict[str, Any]] = None
    workload_metadata: Optional[Dict[str, Any]] = None
    resource_metrics: Optional[Dict[str, Any]] = None


class BenchmarkComparisonResponse(BaseModel):
    """Comparative delta analysis between baseline and candidate benchmark runs."""
    baseline: BenchmarkResultResponse
    candidate: BenchmarkResultResponse
    is_comparable: bool = True
    incomparable_reason: Optional[str] = None
    rps_delta_pct: float
    p95_latency_delta_pct: float
    avg_latency_delta_pct: float
    error_rate_delta_pct: float
    performance_verdict: str  # IMPROVEMENT, REGRESSION, STABLE, INCOMPARABLE
