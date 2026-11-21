"""Health Check Schemas."""

from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    """System health check response."""
    status: str = Field(..., description="Overall service status (e.g., 'healthy', 'degraded')")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Target execution environment")
    redis_status: str = Field("ready_for_milestone_2", description="Redis connection status")
    database_status: str = Field("ready_for_milestone_2", description="PostgreSQL connection status")
    uptime_seconds: float = Field(..., description="Seconds since application startup")
