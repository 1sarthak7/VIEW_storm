"""Unit Tests for PostgreSQL Models, Repository, and Foreign Key Cascades."""

from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from app.database.session import AsyncSessionLocal, check_db_health
from app.models.event_summary import EventSummary
from app.models.metrics import SimulationMetric
from app.models.simulation import SimulationRun
from app.repositories.simulation_repository import SimulationRepository
from app.schemas.run import SimulationRunCreate, SimulationStatus

pytestmark = pytest.mark.asyncio


async def test_postgres_connection_establishment():
    """Verify live PostgreSQL SELECT 1 probe succeeds."""
    is_healthy = await check_db_health()
    assert is_healthy is True


async def test_postgres_model_creation_and_retrieval():
    """Verify SimulationRun entity creation and querying via repository."""
    async with AsyncSessionLocal() as session:
        repo = SimulationRepository(session)
        payload = SimulationRunCreate(
            name="Unit DB Test",
            target_environment="local",
            virtual_users=25,
            spawn_rate=2.5,
            duration_seconds=45,
            event_type="playback_start",
        )
        created = await repo.create("run-db-unit-1", payload)
        assert created.id == "run-db-unit-1"
        assert created.name == "Unit DB Test"
        assert created.status == "pending"

        retrieved = await repo.get_by_id("run-db-unit-1")
        assert retrieved is not None
        assert retrieved.id == "run-db-unit-1"
        assert retrieved.virtual_users == 25


async def test_postgres_status_update():
    """Verify repository updates status and timestamps correctly."""
    async with AsyncSessionLocal() as session:
        repo = SimulationRepository(session)
        payload = SimulationRunCreate(
            name="Status Transition Test",
            target_environment="local",
            virtual_users=10,
        )
        await repo.create("run-db-unit-2", payload)

        now = datetime.now(timezone.utc)
        updated = await repo.update_status(
            run_id="run-db-unit-2",
            status=SimulationStatus.RUNNING,
            started_at=now,
        )
        assert updated.status == "running"
        assert updated.started_at is not None


async def test_postgres_metrics_and_cascade_delete():
    """Verify metrics relationship and foreign key cascade deletion."""
    async with AsyncSessionLocal() as session:
        repo = SimulationRepository(session)
        run_id = "run-db-unit-3"
        payload = SimulationRunCreate(name="Cascade Test", target_environment="local")
        run = await repo.create(run_id, payload)

        # Add metric
        metric = SimulationMetric(
            run_id=run_id,
            timestamp=datetime.now(timezone.utc),
            active_users=10,
            requests_per_second=5.5,
            successful_requests=100,
            failed_requests=0,
            average_latency=12.0,
            p95_latency=25.0,
            p99_latency=50.0,
        )
        await repo.add_metric(metric)

        # Add event summary
        summary = EventSummary(
            run_id=run_id,
            event_type="playback_start",
            accepted_count=100,
            rejected_count=0,
            duplicate_count=2,
            total_watch_duration_ms=50000,
        )
        await repo.save_event_summary(summary)

        # Verify records exist
        metrics = await repo.list_metrics(run_id)
        assert len(metrics) == 1

        # Delete simulation run
        await session.delete(run)
        await session.commit()

        # Verify cascading deletion removed metrics and summaries
        stmt_m = select(SimulationMetric).where(SimulationMetric.run_id == run_id)
        res_m = await session.execute(stmt_m)
        assert res_m.scalars().first() is None

        stmt_s = select(EventSummary).where(EventSummary.run_id == run_id)
        res_s = await session.execute(stmt_s)
        assert res_s.scalars().first() is None


async def test_postgres_unavailable_handling(mocker):
    """Verify check_db_health returns False when database is unreachable."""
    mocker.patch(
        "app.database.session.AsyncSessionLocal",
        side_effect=Exception("Database Connection Timeout"),
    )
    is_healthy = await check_db_health()
    assert is_healthy is False
