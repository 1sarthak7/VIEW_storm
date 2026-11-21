"""Statistics and Metrics Schemas."""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from app.schemas.run import SimulationStatus


class SimulationStatsResponse(BaseModel):
    """Aggregated real-time statistics for a simulation run."""
    run_id: str
    status: SimulationStatus
    total_events: int = Field(..., description="Total event submissions received")
    accepted_events: int = Field(..., description="Count of valid, accepted unique events")
    rejected_events: int = Field(..., description="Count of rejected events (e.g. inactive run)")
    duplicate_events: int = Field(..., description="Count of duplicate events dropped via idempotency")
    unique_viewers_count: int = Field(..., description="Number of distinct synthetic viewers")
    events_by_type: Dict[str, int] = Field(default_factory=dict, description="Count breakdown by event type")
    total_watch_duration_ms: int = Field(0, description="Sum of watch duration across accepted events")
    average_watch_duration_ms: float = Field(0.0, description="Average watch duration per event")
    started_at: Optional[datetime] = None
    elapsed_seconds: float = Field(0.0, description="Seconds elapsed since run start")
    current_rps: float = Field(0.0, description="Estimated current requests/events per second")


class MetricPoint(BaseModel):
    """Snapshot time-series data point for analytics charts."""
    timestamp: datetime
    active_users: int = 0
    requests_per_second: float = 0.0
    successful_requests: int = 0
    failed_requests: int = 0
    average_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0


class SimulationMetricsResponse(BaseModel):
    """Historical time-series metrics collection."""
    run_id: str
    metrics: List[MetricPoint]


class SimulationReportResponse(BaseModel):
    """Comprehensive summary report for an executed simulation run."""
    run_id: str
    name: str
    target_environment: str
    status: SimulationStatus
    configured_users: int
    duration_seconds: int
    actual_duration_seconds: float
    total_submissions: int
    accepted_events: int
    rejected_events: int
    duplicate_events: int
    unique_viewers: int
    total_watch_duration_ms: int
    average_watch_duration_ms: float
    events_breakdown: Dict[str, int]
    average_throughput_eps: float
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
