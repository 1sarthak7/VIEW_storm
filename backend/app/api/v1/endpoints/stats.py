"""Statistics, Metrics, and Reporting Endpoints."""

from fastapi import APIRouter
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
def get_run_statistics(run_id: str) -> SimulationStatsResponse:
    """Retrieve real-time aggregated metrics for a simulation run."""
    return stats_service.get_current_stats(run_id)


@router.get(
    "/runs/{run_id}/metrics",
    response_model=SimulationMetricsResponse,
    tags=["Analytics & Reports"],
)
def get_run_metrics(run_id: str) -> SimulationMetricsResponse:
    """Retrieve historical time-series metrics data points."""
    return stats_service.get_metrics(run_id)


@router.get(
    "/runs/{run_id}/report",
    response_model=SimulationReportResponse,
    tags=["Analytics & Reports"],
)
def get_run_report(run_id: str) -> SimulationReportResponse:
    """Generate final comprehensive summary report for a simulation."""
    return stats_service.generate_report(run_id)
