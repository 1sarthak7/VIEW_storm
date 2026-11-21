"""Simulation Runs Management API Endpoints."""

from typing import List
from fastapi import APIRouter, status
from app.schemas.run import SimulationRunCreate, SimulationRunResponse
from app.services.simulation_service import simulation_service

router = APIRouter()


@router.post(
    "/runs",
    response_model=SimulationRunResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Simulations"],
)
def create_simulation_run(payload: SimulationRunCreate) -> SimulationRunResponse:
    """Create and validate a new simulation run configuration."""
    return simulation_service.create_run(payload)


@router.get(
    "/runs",
    response_model=List[SimulationRunResponse],
    tags=["Simulations"],
)
def list_simulation_runs() -> List[SimulationRunResponse]:
    """List historical and active simulation runs."""
    return simulation_service.list_runs()


@router.get(
    "/runs/{run_id}",
    response_model=SimulationRunResponse,
    tags=["Simulations"],
)
def get_simulation_run(run_id: str) -> SimulationRunResponse:
    """Retrieve details for a specific simulation run."""
    return simulation_service.get_run(run_id)


@router.post(
    "/runs/{run_id}/start",
    response_model=SimulationRunResponse,
    tags=["Simulations"],
)
def start_simulation_run(run_id: str) -> SimulationRunResponse:
    """Start an authorized simulation run."""
    return simulation_service.start_run(run_id)


@router.post(
    "/runs/{run_id}/stop",
    response_model=SimulationRunResponse,
    tags=["Simulations"],
)
def stop_simulation_run(run_id: str) -> SimulationRunResponse:
    """Safely stop an active simulation run."""
    return simulation_service.stop_run(run_id)
