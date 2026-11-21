"""Unit Tests for LocustRunnerService Process Orchestration."""

from datetime import datetime, timezone
from pathlib import Path
import pytest
from app.core.runner_config import runner_settings
from app.database.session import AsyncSessionLocal
from app.repositories.simulation_repository import SimulationRepository
from app.schemas.run import SimulationRunCreate, SimulationRunResponse, SimulationStatus
from app.schemas.runner import RunnerProcessStatus
from app.services.locust_runner_service import (
    LocustRunnerService,
    RunnerAlreadyActiveError,
    RunnerLaunchError,
)

pytestmark = pytest.mark.asyncio


async def test_duplicate_runner_launch_prevention(mocker):
    """Verify that attempting to launch a runner for an already active run raises 409 conflict."""
    runner = LocustRunnerService()
    run = SimulationRunResponse(
        id="run-dup-check",
        name="Dup Test",
        target_environment="local",
        virtual_users=10,
        spawn_rate=2.0,
        duration_seconds=30,
        event_type="playback_start",
        watch_duration_min=5,
        watch_duration_max=60,
        status=SimulationStatus.RUNNING,
        created_at=datetime.now(timezone.utc),
    )

    # Mock active process
    mock_proc = mocker.MagicMock()
    mock_proc.returncode = None
    runner._active_runners[run.id] = mock_proc

    with pytest.raises(RunnerAlreadyActiveError):
        await runner.start_runner(run)


async def test_runner_unauthorized_target_rejected():
    """Verify runner rejects target URLs outside allowlist."""
    runner = LocustRunnerService()
    run = SimulationRunResponse(
        id="run-bad-target",
        name="Bad Target Test",
        target_environment="local",
        virtual_users=5,
        spawn_rate=1.0,
        duration_seconds=10,
        event_type="playback_start",
        watch_duration_min=5,
        watch_duration_max=60,
        status=SimulationStatus.RUNNING,
        created_at=datetime.now(timezone.utc),
    )

    with pytest.raises(Exception) as exc_info:
        await runner.start_runner(run, target_host="http://malicious-external-target.com")
    assert "not in authorized" in str(exc_info.value)


async def test_runner_stop_and_graceful_shutdown(mocker):
    """Verify stop_runner sends SIGTERM and updates status."""
    runner = LocustRunnerService()
    run_id = "run-stop-test"

    mock_proc = mocker.AsyncMock()
    mock_proc.pid = 99999
    mock_proc.returncode = None
    mock_proc.wait = mocker.AsyncMock(return_value=0)

    runner._active_runners[run_id] = mock_proc
    from app.schemas.runner import RunnerMetadata
    runner._runner_metadata[run_id] = RunnerMetadata(
        run_id=run_id,
        pid=99999,
        status=RunnerProcessStatus.RUNNING,
        artifacts_dir="/tmp",
    )

    metadata = await runner.stop_runner(run_id)
    assert mock_proc.terminate.called
    assert metadata.status == RunnerProcessStatus.STOPPED
