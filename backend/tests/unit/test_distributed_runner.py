"""Unit Tests for Distributed Locust Master Subprocess Service."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
from app.core.errors import ViewStormException
from app.schemas.run import SimulationRunResponse, SimulationStatus
from app.schemas.runner import RunnerMetadata, RunnerProcessStatus
from app.services.distributed_runner_service import (
    DistributedMasterAlreadyActiveError,
    DistributedRunnerService,
)

pytestmark = pytest.mark.asyncio


def make_dummy_run(run_id: str = "run-master-test") -> SimulationRunResponse:
    return SimulationRunResponse(
        id=run_id,
        name="Master Test",
        target_environment="local",
        execution_mode="distributed",
        virtual_users=100,
        spawn_rate=10.0,
        duration_seconds=30,
        event_type="playback_start",
        watch_duration_min=5,
        watch_duration_max=60,
        status=SimulationStatus.RUNNING,
        created_at=datetime.now(timezone.utc),
    )


async def test_distributed_master_launch_arguments(mocker):
    """Verify that start_master correctly formats --master and --expect-workers flags."""
    runner = DistributedRunnerService()
    run = make_dummy_run()

    mock_proc = MagicMock()
    mock_proc.pid = 99999
    mock_proc.returncode = None
    mock_proc.wait = AsyncMock(return_value=0)

    mock_exec = mocker.patch("asyncio.create_subprocess_exec", return_value=mock_proc)
    mocker.patch.object(runner, "_monitor_master", return_value=None)

    metadata = await runner.start_master(
        run=run,
        expected_workers=3,
        target_host="http://127.0.0.1:8000",
        bind_host="0.0.0.0",
        bind_port=5557,
        max_wait_seconds=15,
    )

    assert metadata.pid == 99999
    assert metadata.status == RunnerProcessStatus.RUNNING

    # Inspect call args to subprocess
    call_args = mock_exec.call_args[0]
    cmd = list(call_args)

    assert "--master" in cmd
    assert "--expect-workers" in cmd
    exp_idx = cmd.index("--expect-workers")
    assert cmd[exp_idx + 1] == "3"

    assert "--master-bind-port" in cmd
    port_idx = cmd.index("--master-bind-port")
    assert cmd[port_idx + 1] == "5557"

    assert "-u" in cmd
    u_idx = cmd.index("-u")
    assert cmd[u_idx + 1] == "100"


async def test_duplicate_master_prevention(mocker):
    """Verify that launching a master for an already active run raises 409 conflict."""
    runner = DistributedRunnerService()
    run = make_dummy_run("run-dup-master")

    mock_proc = MagicMock()
    mock_proc.pid = 1234
    mock_proc.returncode = None
    runner._active_masters[run.id] = mock_proc

    with pytest.raises(DistributedMasterAlreadyActiveError):
        await runner.start_master(run=run, expected_workers=2)


async def test_master_unauthorized_target_rejected():
    """Verify master runner rejects target URLs outside allowlist."""
    runner = DistributedRunnerService()
    run = make_dummy_run("run-bad-target-master")

    with pytest.raises(ViewStormException) as exc_info:
        await runner.start_master(
            run=run,
            expected_workers=2,
            target_host="http://malicious-external-site.com",
        )
    assert exc_info.value.status_code == 403


async def test_master_stop_graceful_shutdown():
    """Verify that stop_master initiates termination and updates metadata."""
    runner = DistributedRunnerService()
    run_id = "run-stop-master"

    mock_proc = MagicMock()
    mock_proc.pid = 8888
    mock_proc.returncode = None
    mock_proc.terminate = MagicMock()

    async def fake_wait():
        mock_proc.returncode = 0
        return 0

    mock_proc.wait = AsyncMock(side_effect=fake_wait)

    runner._active_masters[run_id] = mock_proc
    runner._master_metadata[run_id] = RunnerMetadata(
        run_id=run_id,
        pid=8888,
        status=RunnerProcessStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
        artifacts_dir="/tmp/artifacts",
    )

    metadata = await runner.stop_master(run_id)
    assert mock_proc.terminate.called
    assert metadata.status == RunnerProcessStatus.STOPPED
    assert metadata.exit_code == 0
