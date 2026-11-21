"""Integration Test: Real Distributed Locust Master-Worker Simulation Execution."""

import asyncio
import os
import signal
import socket
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
import pytest
from httpx import AsyncClient
from app.core.runner_config import runner_settings
from app.database.redis import redis_client
from app.database.session import AsyncSessionLocal
from app.models.simulation import SimulationRun
from app.repositories.simulation_repository import SimulationRepository
from app.repositories.worker_repository import WorkerRepository
from app.schemas.run import SimulationRunCreate
from app.schemas.worker import (
    WorkerHeartbeatRequest,
    WorkerNodeStatus,
    WorkerRegisterRequest,
)
from app.services.distributed_runner_service import distributed_runner_service
from app.services.simulation_service import simulation_service
from app.services.worker_assignment_service import worker_assignment_service
from app.services.worker_registry_service import worker_registry_service

pytestmark = pytest.mark.asyncio


def get_free_port() -> int:
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
    """Launch background uvicorn server for real traffic generation."""
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
    time.sleep(1.2)
    runner_settings.allowed_target_hosts.append(live_server_url)

    yield proc

    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()


async def test_live_distributed_simulation_execution(live_server_url):
    """
    Run an end-to-end distributed simulation with 1 central master and 2 worker subprocesses.
    Validates ZeroMQ master-worker synchronization, traffic generation, and stats reconciliation.
    """
    master_zmq_port = get_free_port()
    run_id = f"run-dist-{uuid.uuid4().hex[:8]}"

    # 1. Register 2 Worker Nodes in DB and Redis
    w1_ident = f"worker-node-1-{uuid.uuid4().hex[:6]}"
    w2_ident = f"worker-node-2-{uuid.uuid4().hex[:6]}"

    async with AsyncSessionLocal() as session:
        reg1 = await worker_registry_service.register_node(
            WorkerRegisterRequest(
                worker_identifier=w1_ident,
                worker_name="Worker 1",
                hostname="worker-box-1",
                platform="Darwin",
                locust_version=runner_settings.pinned_locust_version,
                capacity=100,
                auth_token="secret-token-12345",
            ),
            db=session,
            redis=redis_client,
        )
        reg2 = await worker_registry_service.register_node(
            WorkerRegisterRequest(
                worker_identifier=w2_ident,
                worker_name="Worker 2",
                hostname="worker-box-2",
                platform="Darwin",
                locust_version=runner_settings.pinned_locust_version,
                capacity=100,
                auth_token="secret-token-12345",
            ),
            db=session,
            redis=redis_client,
        )

    # 2. Create Distributed Simulation Run
    async with AsyncSessionLocal() as session:
        repo = SimulationRepository(session)
        payload = SimulationRunCreate(
            name="Distributed Live Master-Worker Test",
            target_environment="local",
            execution_mode="distributed",
            virtual_users=4,
            spawn_rate=4.0,
            duration_seconds=5,
            event_type="playback_start",
            watch_duration_min=1,
            watch_duration_max=5,
        )
        run_entity = await repo.create(run_id, payload)
        run_resp = simulation_service._entity_to_response(run_entity)

    # 3. Start Run in Redis & PostgreSQL
    await simulation_service.start_run(run_id)

    # 4. Allocate Workers for Run
    async with AsyncSessionLocal() as session:
        assignments = await worker_assignment_service.allocate_workers_for_run(
            run=run_resp,
            db=session,
            redis=redis_client,
            target_host=live_server_url,
            master_host="127.0.0.1",
            master_port=master_zmq_port,
        )

    assert len(assignments) == 2
    assigned_sum = sum(a.assigned_users for a in assignments)
    assert assigned_sum == 4

    # 5. Start Central Locust Master Subprocess
    master_metadata = await distributed_runner_service.start_master(
        run=run_resp,
        expected_workers=2,
        target_host=live_server_url,
        bind_host="127.0.0.1",
        bind_port=master_zmq_port,
        max_wait_seconds=15,
    )

    assert master_metadata.pid is not None
    assert distributed_runner_service.is_master_active(run_id) is True

    # 6. Launch 2 Real Worker Subprocesses connected to master via ZeroMQ
    locustfile = runner_settings.locustfile_path
    worker_procs = []

    for assignment in assignments:
        worker_cmd = [
            sys.executable,
            "-m",
            "locust",
            "-f",
            str(locustfile),
            "--worker",
            "--master-host",
            "127.0.0.1",
            "--master-port",
            str(master_zmq_port),
        ]
        w_env = os.environ.copy()
        w_env["VIEWSTORM_RUN_ID"] = run_id
        w_env["VIEWSTORM_EVENT_TYPE"] = assignment.event_type
        w_env["VIEWSTORM_WATCH_MIN"] = str(assignment.watch_duration_min)
        w_env["VIEWSTORM_WATCH_MAX"] = str(assignment.watch_duration_max)
        w_env["VIEWSTORM_TARGET_HOST"] = live_server_url

        proc = await asyncio.create_subprocess_exec(
            *worker_cmd,
            env=w_env,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        worker_procs.append(proc)

    try:
        # 7. Wait for Master to complete the 5-second distributed test
        master_proc = distributed_runner_service._active_masters.get(run_id)
        if master_proc:
            await asyncio.wait_for(master_proc.wait(), timeout=15.0)

        # Allow final monitor flush
        await asyncio.sleep(1.5)

        # 8. Assertions: Redis event counters incremented by worker-generated traffic
        stats_data = await redis_client.hgetall(f"viewstorm:run:{run_id}:stats")
        accepted_events = int(stats_data.get("accepted_events", 0))
        total_submissions = int(stats_data.get("total_submissions", 0))

        assert total_submissions > 0, "Distributed workers should have submitted traffic"
        assert accepted_events > 0, "API should have accepted distributed events"

        # Check unique viewers
        unique_viewers = await redis_client.scard(f"viewstorm:run:{run_id}:viewers")
        assert unique_viewers >= 2

        # 9. Master Artifacts
        artifacts_dir = runner_settings.artifacts_dir / run_id
        assert (artifacts_dir / "master.log").exists()
        assert (artifacts_dir / "stats_stats.csv").exists()

        # 10. Check PostgreSQL DB State
        async with AsyncSessionLocal() as session:
            repo = SimulationRepository(session)
            worker_repo = WorkerRepository(session)

            final_run = await repo.get_by_id(run_id)
            assert final_run.status in ("completed", "stopped")

            workers = await worker_repo.get_assignments_for_run(run_id)
            assert len(workers) == 2
            assert sum(w.assigned_users for w in workers) == 4

    finally:
        # Clean up worker subprocesses
        for wp in worker_procs:
            if wp.returncode is None:
                try:
                    wp.terminate()
                except ProcessLookupError:
                    pass
