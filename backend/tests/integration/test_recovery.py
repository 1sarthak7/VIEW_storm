"""Integration Tests for Startup Lifecycle Reconciliation and Failure Recovery."""

import pytest
from app.database.session import AsyncSessionLocal
from app.models.simulation import SimulationRun
from app.schemas.run import SimulationRunCreate, SimulationStatus
from app.services.lifecycle_reconciliation_service import (
    lifecycle_reconciliation_service,
)
from app.services.simulation_service import simulation_service


@pytest.mark.asyncio
async def test_startup_reconciliation_cleans_zombie_runs():
    """Verify that runs left in active state prior to restart are transitioned to INTERRUPTED."""
    from app.repositories.simulation_repository import SimulationRepository

    async with AsyncSessionLocal() as session:
        # Create runs left in zombie states
        payload1 = SimulationRunCreate(
            name="Zombie Run 1",
            target_environment="local",
            virtual_users=10,
            spawn_rate=2.0,
            duration_seconds=30,
        )
        payload2 = SimulationRunCreate(
            name="Zombie Run 2",
            target_environment="local",
            virtual_users=15,
            spawn_rate=3.0,
            duration_seconds=30,
        )
        run1 = await simulation_service.create_run(payload1, db=session)
        run2 = await simulation_service.create_run(payload2, db=session)

        # Simulate that server crashed while run1 was running and run2 was starting
        repo = SimulationRepository(session)
        await repo.update_status(run1.id, SimulationStatus.RUNNING)
        await repo.update_status(run2.id, SimulationStatus.STARTING)

        # Execute reconciliation hook
        reconciled = await lifecycle_reconciliation_service.reconcile_interrupted_runs(session)
        assert reconciled == 2

        # Verify states are INTERRUPTED
        refreshed1 = await simulation_service.get_run(run1.id, db=session)
        refreshed2 = await simulation_service.get_run(run2.id, db=session)

        assert refreshed1.status == SimulationStatus.INTERRUPTED
        assert refreshed2.status == SimulationStatus.INTERRUPTED
        assert "interrupted due to backend restart" in refreshed1.error_message
        assert refreshed1.finished_at is not None
