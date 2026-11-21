"""Simulation Run Schemas and Lifecycle Models."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, model_validator


class SimulationStatus(str, Enum):
    """Simulation run lifecycle states."""
    PENDING = "pending"
    RUNNING = "running"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


class SimulationRunCreate(BaseModel):
    """Configuration to create a new simulation run."""
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Human-readable simulation name"
    )
    target_environment: str = Field(
        default="local",
        description="Target environment name (must be allowlisted)"
    )
    virtual_users: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Target number of concurrent virtual users (max 1000 for local mode)"
    )
    spawn_rate: float = Field(
        default=10.0,
        gt=0.0,
        le=500.0,
        description="Users spawned per second"
    )
    duration_seconds: int = Field(
        default=60,
        ge=5,
        le=86400,
        description="Simulation run duration in seconds"
    )
    event_type: str = Field(
        default="playback_start",
        description="Primary event pattern or mix specification"
    )
    watch_duration_min: int = Field(
        default=5,
        ge=0,
        description="Minimum simulated watch duration in seconds"
    )
    watch_duration_max: int = Field(
        default=60,
        ge=0,
        description="Maximum simulated watch duration in seconds"
    )

    @model_validator(mode="after")
    def validate_duration_range(self) -> "SimulationRunCreate":
        if self.watch_duration_max < self.watch_duration_min:
            raise ValueError(
                f"watch_duration_max ({self.watch_duration_max}) must be >= watch_duration_min ({self.watch_duration_min})"
            )
        return self


class SimulationRunResponse(BaseModel):
    """Simulation run details returned by the API."""
    id: str
    name: str
    target_environment: str
    virtual_users: int
    spawn_rate: float
    duration_seconds: int
    event_type: str
    watch_duration_min: int
    watch_duration_max: int
    status: SimulationStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None
