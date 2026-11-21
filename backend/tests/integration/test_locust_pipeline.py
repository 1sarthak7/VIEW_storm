"""Integration Test: Real Locust Subprocess Traffic Generation and Ingestion Pipeline."""

import asyncio
import os
import signal
import socket
import sys
from pathlib import Path
import pytest
from httpx import AsyncClient
import uvicorn
from app.core.runner_config import runner_settings
from app.database.redis import redis_client
from app.database.session import AsyncSessionLocal
from app.main import app
from app.models.simulation import SimulationRun
from app.repositories.simulation_repository import SimulationRepository
from app.schemas.run import SimulationRunCreate
from app.services.locust_runner_service import locust_runner_service
from app.services.simulation_service import simulation_service

pytestmark = pytest.mark.asyncio


def get_free_port() -> int:
    """Find a free TCP port for live integration server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_server_port():
    return get_free_port()


@pytest.fixture(scope="module")
def live_server_url(live_server_port):
    return f"http://127.0.0.1:{live_server_port}"


@pytest.fixture(scope="module", autouse=True)
def run_live_uvicorn_server(live_server_port, live_server_url):
    """Launch a background uvicorn server on a dedicated port for real Locust traffic."""
    import subprocess
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--app-dir",
        "backend",
        "--host",
        "127.0.0.1",
        "--port",
        str(live_server_port),
    ]
    env = os.environ.copy()
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    import time
    time.sleep(1.2)  # Wait for startup
    runner_settings.allowed_target_hosts.append(live_server_url)

    yield proc

    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()


async def test_live_locust_simulation_execution(live_server_url):
    """
    Run a real 3-second Locust simulation with 2 virtual users.
    Verify that real HTTP requests hit the live API, populate Redis counters, and save CSV stats.
    """
    run_id = "run-live-locust-01"

    # 1. Create Run in DB
    async with AsyncSessionLocal() as session:
        repo = SimulationRepository(session)
        payload = SimulationRunCreate(
            name="Live Locust Engine Test",
            target_environment="local",
            virtual_users=2,
            spawn_rate=2.0,
            duration_seconds=5,
            event_type="playback_start",
            watch_duration_min=1,
            watch_duration_max=5,
        )
        run_entity = await repo.create(run_id, payload)
        run_resp = simulation_service._entity_to_response(run_entity)

    # 2. Start Run in Redis & PostgreSQL
    await simulation_service.start_run(run_id)

    # 3. Launch Locust Subprocess targeting the live server
    metadata = await locust_runner_service.start_runner(
        run=run_resp,
        target_host=live_server_url,
    )

    assert metadata.pid is not None
    assert locust_runner_service.is_runner_active(run_id) is True

    # 4. Wait for Locust simulation to generate traffic and conclude
    proc = locust_runner_service._active_runners.get(run_id)
    if proc:
        await asyncio.wait_for(proc.wait(), timeout=12.0)

    # Allow monitor task to finalize stats flush
    await asyncio.sleep(1.5)

    # 5. Verify Redis Event Counters were incremented by real Locust requests
    stats_data = await redis_client.hgetall(f"viewstorm:run:{run_id}:stats")
    accepted_events = int(stats_data.get("accepted_events", 0))
    total_submissions = int(stats_data.get("total_submissions", 0))

    assert total_submissions > 0, "Locust should have submitted playback events"
    assert accepted_events > 0, "API should have accepted synthetic playback events"

    # Verify unique viewers were registered
    unique_viewers = await redis_client.scard(f"viewstorm:run:{run_id}:viewers")
    assert unique_viewers >= 1

    # 6. Verify Artifacts were created
    artifacts_dir = runner_settings.artifacts_dir / run_id
    assert (artifacts_dir / "runner.log").exists()
    assert (artifacts_dir / "stats_stats.csv").exists()

    # 7. Verify Final Run Status in PostgreSQL
    async with AsyncSessionLocal() as session:
        repo = SimulationRepository(session)
        final_run = await repo.get_by_id(run_id)
        assert final_run.status in ("completed", "stopped")
