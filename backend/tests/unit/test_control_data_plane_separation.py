"""Unit Tests for Milestone 8 Control-Plane and Data-Plane Isolation."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import create_application


@pytest.mark.asyncio
async def test_dataplane_mounts_ingestion_and_excludes_orchestration():
    """Verify Data-Plane mounts playback ingestion but does not expose control plane routes."""
    app = create_application(service_mode="data_plane")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Ingestion routes and health must exist
        health_resp = await client.get("/health")
        assert health_resp.status_code == 200

        # Control plane routes must NOT be mounted on Data Plane (404 Not Found)
        runs_resp = await client.get("/api/v1/runs")
        assert runs_resp.status_code == 404

        benchmarks_resp = await client.get("/api/v1/benchmarks/profiles")
        assert benchmarks_resp.status_code == 404

        workers_resp = await client.get("/api/v1/worker-nodes")
        assert workers_resp.status_code == 404


@pytest.mark.asyncio
async def test_controlplane_mounts_orchestration_and_excludes_ingestion():
    """Verify Control-Plane mounts runs, benchmarks, auth, but does not expose raw playback ingestion."""
    from app.api.deps import get_current_user
    from app.models.user import User

    mock_admin = User(id="u_admin", username="admin", email="admin@viewstorm.local", role="admin")
    app = create_application(service_mode="control_plane")
    app.dependency_overrides[get_current_user] = lambda: mock_admin

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Health and control endpoints must exist
        health_resp = await client.get("/health")
        assert health_resp.status_code == 200

        benchmarks_resp = await client.get("/api/v1/benchmarks/profiles")
        assert benchmarks_resp.status_code == 200

        # Ingestion endpoint must NOT be mounted on dedicated Control Plane
        event_resp = await client.post(
            "/api/v1/events/playback",
            json={"run_id": "dummy", "event_id": "dummy", "event_type": "play"},
        )
        assert event_resp.status_code == 404
