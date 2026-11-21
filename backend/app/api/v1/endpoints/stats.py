"""Statistics, Metrics, and Reporting Endpoints with Redis & PostgreSQL Integration."""

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.redis import get_redis
from app.database.session import get_db
from app.schemas.stats import (
    SimulationMetricsResponse,
    SimulationReportResponse,
    SimulationStatsResponse,
)
from app.services.stats_service import stats_service

router = APIRouter()


@router.get(
    "/runs/{run_id}/stats",
    response_model=SimulationStatsResponse,
    tags=["Analytics & Reports"],
)
async def get_run_statistics(
    run_id: str,
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
) -> SimulationStatsResponse:
    """Retrieve real-time aggregated metrics directly from Redis counters."""
    return await stats_service.get_current_stats(run_id, redis=redis, db=db)


@router.get(
    "/runs/{run_id}/metrics",
    response_model=SimulationMetricsResponse,
    tags=["Analytics & Reports"],
)
async def get_run_metrics(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> SimulationMetricsResponse:
    """Retrieve historical time-series performance data points."""
    return await stats_service.get_metrics(run_id, db=db, redis=redis)


@router.get(
    "/runs/{run_id}/report",
    response_model=SimulationReportResponse,
    tags=["Analytics & Reports"],
)
async def get_run_report(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> SimulationReportResponse:
    """Generate final comprehensive summary report for a simulation."""
    return await stats_service.generate_report(run_id, db=db, redis=redis)
