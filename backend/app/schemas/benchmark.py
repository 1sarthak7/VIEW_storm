"""Pydantic Schemas for Controlled Benchmarking Framework."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


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


class BenchmarkRunRequest(BaseModel):
    """Execution request for a standardized benchmark."""
    profile_name: str = Field(..., pattern="^(smoke|baseline|medium|high|distributed)$")
    execution_mode: Optional[str] = Field(None, pattern="^(local|distributed)$")
    target_environment: str = Field("local")
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
    """Persistent benchmark execution outcome."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    profile_name: str
    test_type: str
    run_id: Optional[str]
    target_environment: str
    virtual_users: int
    spawn_rate: float
    duration_seconds: int
    total_requests: int
    requests_per_second: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    error_rate_pct: float
    passed_thresholds: bool
    abort_reason: Optional[str]
    notes: Optional[str]
    created_at: datetime
    threshold_evaluation: Optional[ThresholdEvaluation] = None


class BenchmarkComparisonResponse(BaseModel):
    """Comparative delta analysis between baseline and candidate benchmark runs."""
    baseline: BenchmarkResultResponse
    candidate: BenchmarkResultResponse
    rps_delta_pct: float
    p95_latency_delta_pct: float
    avg_latency_delta_pct: float
    error_rate_delta_pct: float
    performance_verdict: str
