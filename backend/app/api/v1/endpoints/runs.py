"""Simulation Runs API Endpoints with Locust Runner Integration."""

from typing import List
from fastapi import APIRouter, Depends, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.redis import get_redis
from app.database.session import get_db
from app.schemas.run import SimulationRunCreate, SimulationRunResponse
from app.services.locust_runner_service import locust_runner_service
from app.services.simulation_service import simulation_service

router = APIRouter()


@router.post(
    "/runs",
    response_model=SimulationRunResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Simulations"],
)
async def create_simulation_run(
    payload: SimulationRunCreate,
    db: AsyncSession = Depends(get_db),
) -> SimulationRunResponse:
    """Create and persist a new simulation run configuration."""
    return await simulation_service.create_run(payload, db=db)


@router.get(
    "/runs",
    response_model=List[SimulationRunResponse],
    tags=["Simulations"],
)
async def list_simulation_runs(
    db: AsyncSession = Depends(get_db),
) -> List[SimulationRunResponse]:
    """List historical and active simulation runs from PostgreSQL."""
    return await simulation_service.list_runs(db=db)


@router.get(
    "/runs/{run_id}",
    response_model=SimulationRunResponse,
    tags=["Simulations"],
)
async def get_simulation_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
) -> SimulationRunResponse:
    """Retrieve details for a specific simulation run."""
    return await simulation_service.get_run(run_id, db=db)


@router.post(
    "/runs/{run_id}/start",
    response_model=SimulationRunResponse,
    tags=["Simulations"],
)
async def start_simulation_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> SimulationRunResponse:
    """Start an authorized simulation run and launch the Locust runner subprocess."""
    started_run = await simulation_service.start_run(run_id, db=db, redis=redis)
    try:
        await locust_runner_service.start_runner(started_run, db=db)
    except Exception:
        # If runner launch fails, safely stop run
        await simulation_service.stop_run(run_id, db=db, redis=redis)
        raise
    return started_run


@router.post(
    "/runs/{run_id}/stop",
    response_model=SimulationRunResponse,
    tags=["Simulations"],
)
async def stop_simulation_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> SimulationRunResponse:
    """Safely stop an active simulation run and terminate the Locust runner subprocess."""
    await locust_runner_service.stop_runner(run_id)
    return await simulation_service.stop_run(run_id, db=db, redis=redis)
