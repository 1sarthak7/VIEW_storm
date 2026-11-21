"""Simulation Repository for PostgreSQL Operations."""

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.event_summary import EventSummary
from app.models.metrics import SimulationMetric
from app.models.simulation import SimulationRun
from app.schemas.run import SimulationRunCreate, SimulationStatus


class SimulationRepository:
    """Encapsulates durable PostgreSQL queries and writes for simulation runs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, run_id: str, payload: SimulationRunCreate) -> SimulationRun:
        """Insert a new simulation run entity."""
        run = SimulationRun(
            id=run_id,
            name=payload.name,
            target_environment=payload.target_environment,
            virtual_users=payload.virtual_users,
            spawn_rate=payload.spawn_rate,
            duration_seconds=payload.duration_seconds,
            event_type=payload.event_type,
            watch_duration_min=payload.watch_duration_min,
            watch_duration_max=payload.watch_duration_max,
            status=SimulationStatus.PENDING.value,
        )
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def get_by_id(self, run_id: str) -> Optional[SimulationRun]:
        """Fetch simulation run by ID."""
        stmt = select(SimulationRun).where(SimulationRun.id == run_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> List[SimulationRun]:
        """Fetch all simulation runs ordered by creation timestamp descending."""
        stmt = select(SimulationRun).order_by(SimulationRun.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        run_id: str,
        status: SimulationStatus,
        started_at: Optional[datetime] = None,
        finished_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
    ) -> Optional[SimulationRun]:
        """Update simulation lifecycle state and timestamps."""
        values = {"status": status.value}
        if started_at is not None:
            values["started_at"] = started_at
        if finished_at is not None:
            values["finished_at"] = finished_at
        if error_message is not None:
            values["error_message"] = error_message

        stmt = (
            update(SimulationRun)
            .where(SimulationRun.id == run_id)
            .values(**values)
            .returning(SimulationRun)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def add_metric(self, metric: SimulationMetric) -> SimulationMetric:
        """Record a time-series metric snapshot."""
        self.session.add(metric)
        await self.session.commit()
        await self.session.refresh(metric)
        return metric

    async def list_metrics(self, run_id: str, limit: int = 100) -> List[SimulationMetric]:
        """Fetch historical time-series metric points."""
        stmt = (
            select(SimulationMetric)
            .where(SimulationMetric.run_id == run_id)
            .order_by(SimulationMetric.timestamp.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def save_event_summary(self, summary: EventSummary) -> EventSummary:
        """Persist aggregated event summary record."""
        self.session.add(summary)
        await self.session.commit()
        await self.session.refresh(summary)
        return summary
