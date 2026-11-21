"""Simulation Lifecycle Service with PostgreSQL Persistence and Redis Scaffolding."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.errors import (
    ExceededUserLimitError,
    SimulationInvalidStateTransitionError,
    SimulationNotFoundError,
    UnauthorizedTargetError,
)
from app.database.redis import redis_client, run_stats_key
from app.database.session import AsyncSessionLocal
from app.models.simulation import SimulationRun
from app.repositories.simulation_repository import SimulationRepository
from app.schemas.run import SimulationRunCreate, SimulationRunResponse, SimulationStatus


class SimulationService:
    """Manages simulation run lifecycle, parameters, and PostgreSQL persistence."""

    def _entity_to_response(self, entity: SimulationRun) -> SimulationRunResponse:
        return SimulationRunResponse(
            id=entity.id,
            name=entity.name,
            target_environment=entity.target_environment,
            virtual_users=entity.virtual_users,
            spawn_rate=entity.spawn_rate,
            duration_seconds=entity.duration_seconds,
            event_type=entity.event_type,
            watch_duration_min=entity.watch_duration_min,
            watch_duration_max=entity.watch_duration_max,
            status=SimulationStatus(entity.status),
            created_at=entity.created_at,
            started_at=entity.started_at,
            finished_at=entity.finished_at,
            error_message=entity.error_message,
        )

    async def create_run(
        self,
        payload: SimulationRunCreate,
        db: Optional[AsyncSession] = None,
    ) -> SimulationRunResponse:
        """Validate parameters and persist a new simulation run."""
        if payload.target_environment not in settings.allowed_target_environments:
            raise UnauthorizedTargetError(
                target=payload.target_environment,
                allowed=settings.allowed_target_environments,
            )

        if (
            payload.target_environment == "local"
            and payload.virtual_users > settings.max_local_virtual_users
        ):
            raise ExceededUserLimitError(
                requested=payload.virtual_users,
                maximum=settings.max_local_virtual_users,
            )

        run_id = f"run-{uuid.uuid4().hex[:12]}"

        if db is not None:
            repo = SimulationRepository(db)
            entity = await repo.create(run_id, payload)
            return self._entity_to_response(entity)

        async with AsyncSessionLocal() as session:
            repo = SimulationRepository(session)
            entity = await repo.create(run_id, payload)
            return self._entity_to_response(entity)

    async def get_run(
        self,
        run_id: str,
        db: Optional[AsyncSession] = None,
    ) -> SimulationRunResponse:
        """Retrieve simulation run metadata from PostgreSQL."""
        if db is not None:
            repo = SimulationRepository(db)
            entity = await repo.get_by_id(run_id)
            if not entity:
                raise SimulationNotFoundError(run_id)
            return self._entity_to_response(entity)

        async with AsyncSessionLocal() as session:
            repo = SimulationRepository(session)
            entity = await repo.get_by_id(run_id)
            if not entity:
                raise SimulationNotFoundError(run_id)
            return self._entity_to_response(entity)

    async def list_runs(
        self,
        db: Optional[AsyncSession] = None,
    ) -> List[SimulationRunResponse]:
        """List historical and active simulation runs from PostgreSQL."""
        if db is not None:
            repo = SimulationRepository(db)
            entities = await repo.list_all()
            return [self._entity_to_response(e) for e in entities]

        async with AsyncSessionLocal() as session:
            repo = SimulationRepository(session)
            entities = await repo.list_all()
            return [self._entity_to_response(e) for e in entities]

    async def start_run(
        self,
        run_id: str,
        db: Optional[AsyncSession] = None,
        redis: Optional[Redis] = None,
    ) -> SimulationRunResponse:
        """Transition simulation run from PENDING to RUNNING and initialize Redis stats."""
        r = redis or redis_client
        now = datetime.now(timezone.utc)

        async def _execute(session: AsyncSession) -> SimulationRunResponse:
            repo = SimulationRepository(session)
            entity = await repo.get_by_id(run_id)
            if not entity:
                raise SimulationNotFoundError(run_id)

            if entity.status != SimulationStatus.PENDING.value:
                raise SimulationInvalidStateTransitionError(
                    run_id=run_id,
                    current_status=entity.status,
                    target_status=SimulationStatus.RUNNING.value,
                )

            updated = await repo.update_status(
                run_id=run_id,
                status=SimulationStatus.RUNNING,
                started_at=now,
            )

            # Initialize Redis counters for this run
            stats_key = run_stats_key(run_id)
            await r.hset(
                stats_key,
                mapping={
                    "total_submissions": 0,
                    "accepted_events": 0,
                    "rejected_events": 0,
                    "duplicate_events": 0,
                    "total_watch_duration_ms": 0,
                },
            )
            await r.expire(stats_key, settings.stats_retention_ttl_seconds)

            return self._entity_to_response(updated)

        if db is not None:
            return await _execute(db)

        async with AsyncSessionLocal() as session:
            return await _execute(session)

    async def stop_run(
        self,
        run_id: str,
        db: Optional[AsyncSession] = None,
        redis: Optional[Redis] = None,
    ) -> SimulationRunResponse:
        """Safely transition active simulation to STOPPED and sync final summary."""
        now = datetime.now(timezone.utc)
        r = redis or redis_client

        async def _execute(session: AsyncSession) -> SimulationRunResponse:
            repo = SimulationRepository(session)
            entity = await repo.get_by_id(run_id)
            if not entity:
                raise SimulationNotFoundError(run_id)

            if entity.status != SimulationStatus.RUNNING.value:
                raise SimulationInvalidStateTransitionError(
                    run_id=run_id,
                    current_status=entity.status,
                    target_status=SimulationStatus.STOPPED.value,
                )

            updated = await repo.update_status(
                run_id=run_id,
                status=SimulationStatus.STOPPED,
                finished_at=now,
            )

            # Sync Redis statistics to PostgreSQL summaries
            from app.services.aggregation_service import aggregation_service
            await aggregation_service.sync_run_summary_to_postgres(run_id, r, session)

            return self._entity_to_response(updated)

        if db is not None:
            return await _execute(db)

        async with AsyncSessionLocal() as session:
            return await _execute(session)


simulation_service = SimulationService()
