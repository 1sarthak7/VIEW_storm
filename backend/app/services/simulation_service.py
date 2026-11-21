"""Simulation Lifecycle and Configuration Service."""

import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from app.core.config import settings
from app.core.errors import (
    ExceededUserLimitError,
    SimulationInvalidStateTransitionError,
    SimulationNotFoundError,
    UnauthorizedTargetError,
)
from app.schemas.run import SimulationRunCreate, SimulationRunResponse, SimulationStatus


class SimulationService:
    """Manages simulation run lifecycle, configurations, and state transitions."""

    def __init__(self) -> None:
        self._runs: Dict[str, SimulationRunResponse] = {}
        self._lock = threading.RLock()

    def create_run(self, payload: SimulationRunCreate) -> SimulationRunResponse:
        """Validate and register a new simulation run configuration."""
        # 1. Target environment validation
        if payload.target_environment not in settings.allowed_target_environments:
            raise UnauthorizedTargetError(
                target=payload.target_environment,
                allowed=settings.allowed_target_environments,
            )

        # 2. Local concurrency limit validation
        if (
            payload.target_environment == "local"
            and payload.virtual_users > settings.max_local_virtual_users
        ):
            raise ExceededUserLimitError(
                requested=payload.virtual_users,
                maximum=settings.max_local_virtual_users,
            )

        run_id = f"run-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        run = SimulationRunResponse(
            id=run_id,
            name=payload.name,
            target_environment=payload.target_environment,
            virtual_users=payload.virtual_users,
            spawn_rate=payload.spawn_rate,
            duration_seconds=payload.duration_seconds,
            event_type=payload.event_type,
            watch_duration_min=payload.watch_duration_min,
            watch_duration_max=payload.watch_duration_max,
            status=SimulationStatus.PENDING,
            created_at=now,
        )

        with self._lock:
            self._runs[run_id] = run

        return run

    def get_run(self, run_id: str) -> SimulationRunResponse:
        """Retrieve simulation run metadata by ID."""
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                raise SimulationNotFoundError(run_id)
            return run

    def list_runs(self) -> List[SimulationRunResponse]:
        """List all registered simulation runs sorted by creation time descending."""
        with self._lock:
            return sorted(
                list(self._runs.values()),
                key=lambda r: r.created_at,
                reverse=True,
            )

    def start_run(self, run_id: str) -> SimulationRunResponse:
        """Transition simulation run from PENDING to RUNNING."""
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                raise SimulationNotFoundError(run_id)

            if run.status != SimulationStatus.PENDING:
                raise SimulationInvalidStateTransitionError(
                    run_id=run_id,
                    current_status=run.status.value,
                    target_status=SimulationStatus.RUNNING.value,
                )

            now = datetime.now(timezone.utc)
            updated = run.model_copy(
                update={"status": SimulationStatus.RUNNING, "started_at": now}
            )
            self._runs[run_id] = updated
            return updated

    def stop_run(self, run_id: str) -> SimulationRunResponse:
        """Transition active simulation to STOPPED."""
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                raise SimulationNotFoundError(run_id)

            if run.status != SimulationStatus.RUNNING:
                raise SimulationInvalidStateTransitionError(
                    run_id=run_id,
                    current_status=run.status.value,
                    target_status=SimulationStatus.STOPPED.value,
                )

            now = datetime.now(timezone.utc)
            updated = run.model_copy(
                update={"status": SimulationStatus.STOPPED, "finished_at": now}
            )
            self._runs[run_id] = updated
            return updated

    def complete_run(self, run_id: str) -> SimulationRunResponse:
        """Mark simulation completed after timer expires."""
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                raise SimulationNotFoundError(run_id)

            now = datetime.now(timezone.utc)
            updated = run.model_copy(
                update={"status": SimulationStatus.COMPLETED, "finished_at": now}
            )
            self._runs[run_id] = updated
            return updated


simulation_service = SimulationService()
