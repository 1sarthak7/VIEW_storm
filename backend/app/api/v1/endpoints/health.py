"""Real-Time Health Monitoring Endpoint."""

import time
from fastapi import APIRouter
from app.core.config import settings
from app.database.redis import check_redis_health
from app.database.session import check_db_health
from app.schemas.health import HealthResponse

router = APIRouter()
START_TIME = time.time()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def get_health() -> HealthResponse:
    """Check live service health and probe actual Redis and PostgreSQL connectivity."""
    uptime = time.time() - START_TIME
    db_healthy = await check_db_health()
    redis_healthy = await check_redis_health()

    redis_status = "healthy" if redis_healthy else "unreachable"
    db_status = "healthy" if db_healthy else "unreachable"

    overall_status = "healthy" if (db_healthy and redis_healthy) else "degraded"

    return HealthResponse(
        status=overall_status,
        version=settings.version,
        environment=settings.environment,
        redis_status=redis_status,
        database_status=db_status,
        uptime_seconds=round(uptime, 2),
    )
