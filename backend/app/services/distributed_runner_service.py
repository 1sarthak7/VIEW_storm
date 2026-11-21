"""Distributed Locust Master Runner Service."""

import asyncio
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import ViewStormException
from app.core.logging import logger
from app.core.runner_config import runner_settings
from app.database.redis import redis_client
from app.database.session import AsyncSessionLocal
from app.repositories.simulation_repository import SimulationRepository
from app.repositories.worker_repository import WorkerRepository
from app.schemas.run import SimulationRunResponse, SimulationStatus
from app.schemas.runner import RunnerMetadata, RunnerProcessStatus
from app.services.aggregation_service import aggregation_service
from app.services.locust_metrics_collector import locust_metrics_collector


class DistributedMasterAlreadyActiveError(ViewStormException):
    def __init__(self, run_id: str):
        super().__init__(
            message=f"Locust master runner for simulation '{run_id}' is already active.",
            status_code=409,
            details={"run_id": run_id},
        )


class DistributedMasterLaunchError(ViewStormException):
    def __init__(self, run_id: str, reason: str):
        super().__init__(
            message=f"Failed to launch Locust master runner for simulation '{run_id}': {reason}",
            status_code=500,
            details={"run_id": run_id, "reason": reason},
        )


class DistributedRunnerService:
    """Manages the lifecycle of the centralized Locust master coordination process."""

    def __init__(self) -> None:
        self._active_masters: Dict[str, asyncio.subprocess.Process] = {}
        self._master_metadata: Dict[str, RunnerMetadata] = {}
        self._monitor_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    def is_master_active(self, run_id: str) -> bool:
        """Check if a Locust master process is currently active."""
        proc = self._active_masters.get(run_id)
        return proc is not None and proc.returncode is None

    def get_master_metadata(self, run_id: str) -> Optional[RunnerMetadata]:
        """Retrieve runtime metadata for active master."""
        return self._master_metadata.get(run_id)

    async def start_master(
        self,
        run: SimulationRunResponse,
        expected_workers: int,
        target_host: Optional[str] = None,
        bind_host: Optional[str] = None,
        bind_port: Optional[int] = None,
        max_wait_seconds: Optional[int] = None,
    ) -> RunnerMetadata:
        """Launch central Locust master in a separate subprocess."""
        async with self._lock:
            if self.is_master_active(run.id):
                raise DistributedMasterAlreadyActiveError(run.id)

            host = target_host or runner_settings.target_local_url
            if host not in runner_settings.allowed_target_hosts:
                raise ViewStormException(
                    message=f"Target host '{host}' is not in authorized local list: {runner_settings.allowed_target_hosts}",
                    status_code=403,
                )

            # 1. Prepare run artifacts directory
            artifacts_dir = runner_settings.artifacts_dir / run.id
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            log_path = artifacts_dir / "master.log"
            csv_prefix = artifacts_dir / "stats"

            locustfile = runner_settings.locustfile_path
            if not locustfile.exists():
                raise DistributedMasterLaunchError(run.id, f"locustfile not found at {locustfile}")

            b_host = bind_host or runner_settings.master_bind_host
            b_port = bind_port or runner_settings.master_bind_port
            wait_sec = max_wait_seconds or runner_settings.expect_workers_max_wait

            cmd = [
                sys.executable,
                "-m",
                "locust",
                "-f",
                str(locustfile),
                "--headless",
                "--master",
                "--master-bind-host",
                b_host,
                "--master-bind-port",
                str(b_port),
                "--expect-workers",
                str(expected_workers),
                "--expect-workers-max-wait",
                str(wait_sec),
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

            env = os.environ.copy()
            env["VIEWSTORM_RUN_ID"] = run.id
            env["VIEWSTORM_EVENT_TYPE"] = run.event_type
            env["VIEWSTORM_WATCH_MIN"] = str(run.watch_duration_min)
            env["VIEWSTORM_WATCH_MAX"] = str(run.watch_duration_max)
            env["VIEWSTORM_TARGET_HOST"] = host

            try:
                log_file = open(log_path, "a", encoding="utf-8")
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    env=env,
                    stdout=log_file,
                    stderr=log_file,
                )
            except Exception as exc:
                logger.error("Failed to execute Locust master subprocess: %s", exc)
                raise DistributedMasterLaunchError(run.id, str(exc))

            now = datetime.now(timezone.utc)
            metadata = RunnerMetadata(
                run_id=run.id,
                pid=proc.pid,
                status=RunnerProcessStatus.RUNNING,
                started_at=now,
                artifacts_dir=str(artifacts_dir),
            )

            self._active_masters[run.id] = proc
            self._master_metadata[run.id] = metadata

            # Spawn background monitor task
            monitor_task = asyncio.create_task(
                self._monitor_master(run.id, proc, artifacts_dir)
            )
            self._monitor_tasks[run.id] = monitor_task

            logger.info("Launched Locust Master PID=%s for run=%s expecting %s workers", proc.pid, run.id, expected_workers)
            return metadata

    async def stop_master(self, run_id: str) -> Optional[RunnerMetadata]:
        """Safely terminate a running Locust master process."""
        proc = self._active_masters.get(run_id)
        metadata = self._master_metadata.get(run_id)

        if not proc or proc.returncode is not None:
            return metadata

        logger.info("Initiating graceful shutdown for Locust master PID=%s (run=%s)", proc.pid, run_id)
        if metadata:
            metadata.status = RunnerProcessStatus.STOPPING

        try:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=runner_settings.stop_grace_period_seconds)
            except asyncio.TimeoutError:
                logger.warning("Locust master PID=%s did not exit in time. Escalating to SIGKILL.", proc.pid)
                proc.kill()
                await proc.wait()
        except ProcessLookupError:
            pass

        now = datetime.now(timezone.utc)
        if metadata:
            metadata.status = RunnerProcessStatus.STOPPED
            metadata.finished_at = now
            metadata.exit_code = proc.returncode

        task = self._monitor_tasks.get(run_id)
        if task and not task.done():
            task.cancel()

        logger.info("Locust master PID=%s stopped (exit_code=%s)", proc.pid, proc.returncode)
        return metadata

    async def _monitor_master(
        self,
        run_id: str,
        proc: asyncio.subprocess.Process,
        artifacts_dir: Path,
    ) -> None:
        """Monitor running Locust master, collect periodic metrics, and handle termination."""
        poll_interval = runner_settings.metrics_poll_interval_seconds

        try:
            while proc.returncode is None:
                await asyncio.sleep(poll_interval)
                if proc.returncode is not None:
                    break

                try:
                    async with AsyncSessionLocal() as session:
                        await locust_metrics_collector.record_metrics_snapshot(
                            run_id=run_id,
                            artifacts_dir=artifacts_dir,
                            db=session,
                        )
                except Exception as exc:
                    logger.debug("Periodic metrics poll error (run=%s): %s", run_id, exc)

            await proc.wait()
            exit_code = proc.returncode
            now = datetime.now(timezone.utc)
            metadata = self._master_metadata.get(run_id)

            logger.info("Locust master finished PID=%s with exit_code=%s", proc.pid, exit_code)

            async with AsyncSessionLocal() as session:
                repo = SimulationRepository(session)
                worker_repo = WorkerRepository(session)

                # Final metrics snapshot
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

                # Update workers assigned to this run
                workers = await worker_repo.get_assignments_for_run(run_id)
                final_worker_status = "completed" if exit_code == 0 else "failed"
                for w in workers:
                    if w.worker_node_id:
                        await worker_repo.update_assignment_status(
                            run_id=run_id,
                            worker_node_id=w.worker_node_id,
                            status=final_worker_status,
                            finished_at=now,
                        )
                        # Revert node status back to online
                        await worker_repo.update_node_status(w.worker_node_id, "online")

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
                    err_msg = f"Locust master exited unexpectedly with code {exit_code}"
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
            logger.debug("Master monitor task cancelled for run=%s", run_id)
        except Exception as exc:
            logger.error("Error in master monitor for run=%s: %s", run_id, exc)
        finally:
            self._active_masters.pop(run_id, None)
            self._monitor_tasks.pop(run_id, None)


distributed_runner_service = DistributedRunnerService()
