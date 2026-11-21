"""Controlled Performance Benchmarking API Endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import require_operator, require_viewer
from app.core.errors import SimulationNotFoundError
from app.database.session import get_db
from app.models.user import User
from app.schemas.benchmark import (
    BenchmarkComparisonResponse,
    BenchmarkProfile,
    BenchmarkResultResponse,
    BenchmarkRunRequest,
)
from app.services.benchmark_service import benchmark_service

router = APIRouter(prefix="/benchmarks", tags=["Benchmarking Framework"])


@router.get("/profiles", response_model=List[BenchmarkProfile])
async def list_benchmark_profiles(
    _: User = Depends(require_viewer),
) -> List[BenchmarkProfile]:
    """Retrieve predefined standardized benchmark profiles (Smoke, Baseline, Medium, High, Distributed)."""
    return benchmark_service.get_profiles()


@router.post("/run", response_model=BenchmarkResultResponse, status_code=status.HTTP_201_CREATED)
async def run_benchmark(
    payload: BenchmarkRunRequest,
    current_user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
) -> BenchmarkResultResponse:
    """Trigger a controlled benchmark experiment with automated SLA guardrails."""
    return await benchmark_service.run_benchmark(payload, db=db, operator=current_user.username)


@router.get("/results", response_model=List[BenchmarkResultResponse])
async def list_benchmark_results(
    profile_name: Optional[str] = Query(None, description="Filter by benchmark profile name"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_viewer),
) -> List[BenchmarkResultResponse]:
    """List historical benchmark runs with SLA pass/fail determinations."""
    return await benchmark_service.list_results(db, profile_name=profile_name, limit=limit, offset=offset)


@router.get("/results/{benchmark_id}", response_model=BenchmarkResultResponse)
async def get_benchmark_result(
    benchmark_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_viewer),
) -> BenchmarkResultResponse:
    """Retrieve single benchmark record with SLA evaluation."""
    result = await benchmark_service.get_result(db, benchmark_id)
    if not result:
        raise SimulationNotFoundError(f"Benchmark record '{benchmark_id}' not found.")
    return result


@router.get("/compare", response_model=BenchmarkComparisonResponse)
async def compare_benchmarks(
    baseline_id: str = Query(..., description="ID of baseline benchmark run"),
    candidate_id: str = Query(..., description="ID of candidate benchmark run"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_viewer),
) -> BenchmarkComparisonResponse:
    """Compare performance metrics between baseline and candidate benchmark executions."""
    return await benchmark_service.compare_results(db, baseline_id=baseline_id, candidate_id=candidate_id)
