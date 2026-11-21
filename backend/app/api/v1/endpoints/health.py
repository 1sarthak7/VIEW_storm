"""Health Check API Endpoint."""

import time
from fastapi import APIRouter
from app.core.config import settings
from app.schemas.health import HealthResponse

router = APIRouter()
START_TIME = time.time()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
def get_health() -> HealthResponse:
    """Service health and component availability status."""
    uptime = time.time() - START_TIME
    return HealthResponse(
        status="healthy",
        version=settings.version,
        environment=settings.environment,
        redis_status="ready_for_milestone_2",
        database_status="ready_for_milestone_2",
        uptime_seconds=round(uptime, 2),
    )
