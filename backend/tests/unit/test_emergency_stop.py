"""Unit Tests for Global Emergency Stop Subsystem."""

import pytest
from httpx import AsyncClient
from app.api.deps import SYSTEM_DEV_USER, get_current_user
from app.database.session import AsyncSessionLocal
from app.main import app
from app.models.simulation import SimulationRun
from app.schemas.run import SimulationRunCreate, SimulationStatus
from app.services.emergency_service import emergency_service
from app.services.simulation_service import simulation_service


@pytest.mark.asyncio
async def test_emergency_stop_lifecycle(client: AsyncClient):
    """Verify emergency stop engages, reports status, and clears cleanly."""
    # Ensure starting clean
    await emergency_service.clear_emergency_stop(operator="test")
    status = await emergency_service.get_status()
    assert status["active"] is False

    # Trigger emergency stop via API
    resp = await client.post(
        "/api/v1/admin/emergency-stop",
        json={"reason": "Safety threshold exceeded on staging cluster"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "engaged"
    assert data["reason"] == "Safety threshold exceeded on staging cluster"

    # Status reflects active
    status_resp = await client.get("/api/v1/admin/emergency-stop/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["active"] is True

    # Clearing emergency stop
    clear_resp = await client.post("/api/v1/admin/emergency-stop/clear")
    assert clear_resp.status_code == 200
    assert clear_resp.json()["status"] == "cleared"

    status_resp2 = await client.get("/api/v1/admin/emergency-stop/status")
    assert status_resp2.json()["active"] is False


@pytest.mark.asyncio
async def test_simulation_creation_blocked_under_emergency_stop(client: AsyncClient):
    """Verify simulation run creation and starting are locked while emergency stop is active."""
    await emergency_service.trigger_emergency_stop(
        reason="Manual lockdown for system maintenance",
        operator="admin",
    )

    try:
        # Creating a run should be rejected with HTTP 423
        resp = await client.post(
            "/api/v1/runs",
            json={
                "name": "Locked Run",
                "target_environment": "local",
                "virtual_users": 10,
                "spawn_rate": 2.0,
                "duration_seconds": 30,
            },
        )
        assert resp.status_code == 423
        assert "Emergency stop is active" in resp.json()["error"]["message"]
    finally:
        await emergency_service.clear_emergency_stop(operator="admin")


@pytest.mark.asyncio
async def test_emergency_stop_terminates_active_simulation():
    """Verify triggering emergency stop marks running DB simulations as interrupted."""
    from app.repositories.simulation_repository import SimulationRepository

    async with AsyncSessionLocal() as session:
        run_payload = SimulationRunCreate(
            name="Emergency Abort Run",
            target_environment="local",
            virtual_users=20,
            spawn_rate=5.0,
            duration_seconds=60,
        )
        run = await simulation_service.create_run(run_payload, db=session)
        repo = SimulationRepository(session)
        await repo.update_status(run.id, SimulationStatus.RUNNING)

        # Engage emergency stop with session
        await emergency_service.trigger_emergency_stop(
            reason="Immediate halt command",
            operator="admin_test",
            db=session,
        )

        # Verify run was marked INTERRUPTED
        updated_run = await simulation_service.get_run(run.id, db=session)
        assert updated_run.status == SimulationStatus.INTERRUPTED
        assert "Aborted by Emergency Stop" in updated_run.error_message

    await emergency_service.clear_emergency_stop(operator="admin_test")
