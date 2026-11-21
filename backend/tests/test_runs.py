"""Tests for simulation run creation and lifecycle transitions with PostgreSQL persistence."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_create_valid_simulation_run(client: AsyncClient):
    """Test creating a valid simulation run configuration persisted in PostgreSQL."""
    payload = {
        "name": "Local Video Test",
        "target_environment": "local",
        "virtual_users": 50,
        "spawn_rate": 5.0,
        "duration_seconds": 30,
        "event_type": "playback_start",
        "watch_duration_min": 10,
        "watch_duration_max": 45,
    }
    response = await client.post("/api/v1/runs", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Local Video Test"
    assert data["status"] == "pending"
    assert data["virtual_users"] == 50
    assert data["id"].startswith("run-")
    assert data["created_at"] is not None


async def test_reject_unauthorized_target_environment(client: AsyncClient):
    """Test that non-allowlisted target environments are strictly rejected."""
    payload = {
        "name": "Unauthorized Target Test",
        "target_environment": "unauthorized-external-domain",
        "virtual_users": 10,
        "spawn_rate": 1.0,
        "duration_seconds": 20,
    }
    response = await client.post("/api/v1/runs", json=payload)
    assert response.status_code == 403
    data = response.json()
    assert "not permitted" in data["error"]["message"]


async def test_reject_excessive_local_virtual_users(client: AsyncClient):
    """Test that local environment enforces safety ceiling."""
    payload = {
        "name": "Overloaded Local Test",
        "target_environment": "local",
        "virtual_users": 5000,
        "spawn_rate": 50.0,
        "duration_seconds": 60,
    }
    response = await client.post("/api/v1/runs", json=payload)
    assert response.status_code in [400, 422]


async def test_reject_invalid_watch_duration_range(client: AsyncClient):
    """Test validation failure when watch_duration_max < watch_duration_min."""
    payload = {
        "name": "Inverted Duration Test",
        "target_environment": "local",
        "virtual_users": 10,
        "watch_duration_min": 50,
        "watch_duration_max": 10,
    }
    response = await client.post("/api/v1/runs", json=payload)
    assert response.status_code == 422


async def test_simulation_lifecycle_transitions(client: AsyncClient):
    """Test standard progression: Create -> Start -> Stop in PostgreSQL."""
    create_res = await client.post(
        "/api/v1/runs",
        json={"name": "Lifecycle Test", "virtual_users": 20, "duration_seconds": 60},
    )
    assert create_res.status_code == 201
    run_id = create_res.json()["id"]

    # Retrieve run
    get_res = await client.get(f"/api/v1/runs/{run_id}")
    assert get_res.status_code == 200
    assert get_res.json()["status"] == "pending"

    # Start run
    start_res = await client.post(f"/api/v1/runs/{run_id}/start")
    assert start_res.status_code == 200
    assert start_res.json()["status"] == "running"
    assert start_res.json()["started_at"] is not None

    # Invalid: Cannot start an already running simulation
    invalid_start = await client.post(f"/api/v1/runs/{run_id}/start")
    assert invalid_start.status_code == 400

    # Stop run
    stop_res = await client.post(f"/api/v1/runs/{run_id}/stop")
    assert stop_res.status_code == 200
    assert stop_res.json()["status"] == "stopped"
    assert stop_res.json()["finished_at"] is not None

    # Invalid: Cannot stop an already stopped simulation
    invalid_stop = await client.post(f"/api/v1/runs/{run_id}/stop")
    assert invalid_stop.status_code == 400
