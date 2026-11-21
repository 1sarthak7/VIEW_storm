"""Locust Runner Service: Subprocess Orchestration and Lifecycle Management."""

import asyncio
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import ViewStormException
from app.core.logging import logger
from app.core.runner_config import runner_settings
from app.database.redis import redis_client
from app.database.session import AsyncSessionLocal
from app.repositories.simulation_repository import SimulationRepository
from app.schemas.run import SimulationRunResponse, SimulationStatus
from app.schemas.runner import RunnerMetadata, RunnerProcessStatus
from app.services.aggregation_service import aggregation_service
from app.services.locust_metrics_collector import locust_metrics_collector


class RunnerAlreadyActiveError(ViewStormException):
    def __init__(self, run_id: str):
        super().__init__(
            message=f"Locust runner for simulation '{run_id}' is already active.",
            status_code=409,
            details={"run_id": run_id},
        )


class RunnerLaunchError(ViewStormException):
    def __init__(self, run_id: str, reason: str):
        super().__init__(
            message=f"Failed to launch Locust runner for simulation '{run_id}': {reason}",
            status_code=500,
            details={"run_id": run_id, "reason": reason},
        )


class LocustRunnerService:
    """Manages the lifecycle of separate Locust load-generator subprocesses."""

    def __init__(self) -> None:
        self._active_runners: Dict[str, asyncio.subprocess.Process] = {}
        self._runner_metadata: Dict[str, RunnerMetadata] = {}
        self._monitor_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        self.cleanup_orphaned_runners()

    def cleanup_orphaned_runners(self) -> None:
        """Terminate any orphaned locust subprocesses matching simulator/locustfile.py."""
        import psutil
        current_pid = os.getpid()
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmd = proc.info.get("cmdline") or []
                if proc.info["pid"] != current_pid and any("locust" in c for c in cmd) and any("locustfile.py" in c for c in cmd):
                    logger.warning("Terminating orphaned Locust process PID=%s", proc.info["pid"])
                    proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    def is_runner_active(self, run_id: str) -> bool:
        """Check if a Locust subprocess is currently running for this run_id."""
        proc = self._active_runners.get(run_id)
        return proc is not None and proc.returncode is None

    def get_runner_metadata(self, run_id: str) -> Optional[RunnerMetadata]:
        """Retrieve runtime metadata for a runner."""
        return self._runner_metadata.get(run_id)

    async def start_runner(
        self,
        run: SimulationRunResponse,
        target_host: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> RunnerMetadata:
        """Launch Locust in a separate subprocess with isolated artifacts."""
        async with self._lock:
            if self.is_runner_active(run.id):
                raise RunnerAlreadyActiveError(run.id)

            host = target_host or runner_settings.target_local_url
            if host not in runner_settings.allowed_target_hosts:
                raise ViewStormException(
                    message=f"Target host '{host}' is not in authorized local list: {runner_settings.allowed_target_hosts}",
                    status_code=403,
                )

            # 1. Prepare run artifacts directory
            artifacts_dir = runner_settings.artifacts_dir / run.id
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            log_path = artifacts_dir / "runner.log"
            csv_prefix = artifacts_dir / "stats"

            # 2. Build subprocess arguments safely without shell strings
            locustfile = runner_settings.locustfile_path
            if not locustfile.exists():
                raise RunnerLaunchError(run.id, f"locustfile not found at {locustfile}")

            cmd = [
                sys.executable,
                "-m",
                "locust",
                "-f",
                str(locustfile),
                "--headless",
                "-u",
                str(run.virtual_users),
                "-r",
                str(run.spawn_rate),
                "-t",
                f"{run.duration_seconds}s",
                "--host",
                host,
                "--csv",
                str(csv_prefix),
                "--csv-full-history",
                "--logfile",
                str(log_path),
            ]

            # 3. Build process environment
            env = os.environ.copy()
            env["VIEWSTORM_RUN_ID"] = run.id
            env["VIEWSTORM_EVENT_TYPE"] = run.event_type
            env["VIEWSTORM_WATCH_MIN"] = str(run.watch_duration_min)
            env["VIEWSTORM_WATCH_MAX"] = str(run.watch_duration_max)
            env["VIEWSTORM_TARGET_HOST"] = host

            # 4. Launch subprocess
            try:
                log_file = open(log_path, "a", encoding="utf-8")
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    env=env,
                    stdout=log_file,
                    stderr=log_file,
                )
            except Exception as exc:
                logger.error("Failed to execute Locust subprocess: %s", exc)
                raise RunnerLaunchError(run.id, str(exc))

            now = datetime.now(timezone.utc)
            metadata = RunnerMetadata(
                run_id=run.id,
                pid=proc.pid,
                status=RunnerProcessStatus.RUNNING,
                started_at=now,
                artifacts_dir=str(artifacts_dir),
            )

            self._active_runners[run.id] = proc
            self._runner_metadata[run.id] = metadata

            # 5. Spawn background monitor task
            monitor_task = asyncio.create_task(
                self._monitor_runner(run.id, proc, artifacts_dir, run.duration_seconds)
            )
            self._monitor_tasks[run.id] = monitor_task

            logger.info("Launched Locust runner PID=%s for run=%s", proc.pid, run.id)
            return metadata

    async def stop_runner(self, run_id: str) -> Optional[RunnerMetadata]:
        """Safely terminate a running Locust process with escalation if needed."""
        proc = self._active_runners.get(run_id)
        metadata = self._runner_metadata.get(run_id)

        if not proc or proc.returncode is not None:
            return metadata

        logger.info("Initiating graceful shutdown for Locust runner PID=%s (run=%s)", proc.pid, run_id)
        if metadata:
            metadata.status = RunnerProcessStatus.STOPPING

        try:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=runner_settings.stop_grace_period_seconds)
            except asyncio.TimeoutError:
                logger.warning("Locust PID=%s did not exit within grace period. Escalating to SIGKILL.", proc.pid)
                proc.kill()
                await proc.wait()
        except ProcessLookupError:
            pass

        now = datetime.now(timezone.utc)
        if metadata:
            metadata.status = RunnerProcessStatus.STOPPED
            metadata.finished_at = now
            metadata.exit_code = proc.returncode

        # Cancel background monitor if still scheduled
        task = self._monitor_tasks.get(run_id)
        if task and not task.done():
            task.cancel()

        logger.info("Locust runner PID=%s stopped successfully (exit_code=%s)", proc.pid, proc.returncode)
        return metadata

    async def _monitor_runner(
        self,
        run_id: str,
        proc: asyncio.subprocess.Process,
        artifacts_dir: Path,
        duration_seconds: int,
    ) -> None:
        """Monitor running Locust process, collect periodic metrics, and handle termination."""
        poll_interval = runner_settings.metrics_poll_interval_seconds
        start_time = asyncio.get_event_loop().time()

        try:
            while proc.returncode is None:
                await asyncio.sleep(poll_interval)
                if proc.returncode is not None:
                    break

                # Periodic snapshot persistence
                try:
                    async with AsyncSessionLocal() as session:
                        await locust_metrics_collector.record_metrics_snapshot(
                            run_id=run_id,
                            artifacts_dir=artifacts_dir,
                            db=session,
                        )
                except Exception as exc:
                    logger.debug("Periodic metrics poll error (run=%s): %s", run_id, exc)

            # Wait for exit code
            await proc.wait()
            exit_code = proc.returncode
            now = datetime.now(timezone.utc)
            metadata = self._runner_metadata.get(run_id)

            logger.info("Locust runner finished PID=%s with exit_code=%s", proc.pid, exit_code)

            # Final metrics collection and DB flush
            async with AsyncSessionLocal() as session:
                repo = SimulationRepository(session)
                # Final snapshot
                await locust_metrics_collector.record_metrics_snapshot(
                    run_id=run_id,
                    artifacts_dir=artifacts_dir,
                    db=session,
                )
                # Flush Redis totals to PostgreSQL EventSummary
                await aggregation_service.sync_run_summary_to_postgres(
                    run_id=run_id,
                    redis=redis_client,
                    db=session,
                )

                if exit_code == 0:
                    await repo.update_status(
                        run_id=run_id,
                        status=SimulationStatus.COMPLETED,
                        finished_at=now,
                    )
                    if metadata:
                        metadata.status = RunnerProcessStatus.COMPLETED
                        metadata.finished_at = now
                        metadata.exit_code = 0
                else:
                    err_msg = f"Locust exited unexpectedly with code {exit_code}"
                    await repo.update_status(
                        run_id=run_id,
                        status=SimulationStatus.FAILED,
                        finished_at=now,
                        error_message=err_msg,
                    )
                    if metadata:
                        metadata.status = RunnerProcessStatus.FAILED
                        metadata.finished_at = now
                        metadata.exit_code = exit_code
                        metadata.error_message = err_msg

        except asyncio.CancelledError:
            logger.debug("Runner monitor task cancelled for run=%s", run_id)
        except Exception as exc:
            logger.error("Error in runner monitor for run=%s: %s", run_id, exc)
        finally:
            self._active_runners.pop(run_id, None)
            self._monitor_tasks.pop(run_id, None)


locust_runner_service = LocustRunnerService()
