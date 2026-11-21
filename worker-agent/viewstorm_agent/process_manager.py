"""Subprocess Lifecycle Manager for Distributed Locust Workers."""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger("viewstorm.agent.process")


class WorkerProcessManager:
    """Manages spawning, tracking, and safely stopping locust worker subprocesses."""

    def __init__(self) -> None:
        self.process: Optional[asyncio.subprocess.Process] = None
        self.current_run_id: Optional[str] = None

    def is_running(self) -> bool:
        return self.process is not None and self.process.returncode is None

    async def start_worker(
        self,
        run_id: str,
        master_host: str,
        master_port: int,
        target_host: str,
        locustfile: Path,
        event_type: str = "playback_start",
        watch_min: int = 5,
        watch_max: int = 60,
    ) -> asyncio.subprocess.Process:
        """Spawn a new locust --worker process connected to the central master."""
        if self.is_running():
            await self.stop_worker()

        cmd = [
            sys.executable,
            "-m",
            "locust",
            "-f",
            str(locustfile),
            "--worker",
            "--master-host",
            master_host,
            "--master-port",
            str(master_port),
        ]

        env = os.environ.copy()
        env["VIEWSTORM_RUN_ID"] = run_id
        env["VIEWSTORM_EVENT_TYPE"] = event_type
        env["VIEWSTORM_WATCH_MIN"] = str(watch_min)
        env["VIEWSTORM_WATCH_MAX"] = str(watch_max)
        env["VIEWSTORM_TARGET_HOST"] = target_host

        logger.info("Spawning Locust worker cmd: %s (master=%s:%s)", " ".join(cmd), master_host, master_port)
        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self.current_run_id = run_id
        return self.process

    async def stop_worker(self, timeout_seconds: float = 5.0) -> None:
        """Gracefully terminate worker subprocess."""
        if not self.is_running() or not self.process:
            return

        logger.info("Stopping Locust worker PID=%s", self.process.pid)
        try:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                logger.warning("Locust worker PID=%s did not exit in time. Escalating to SIGKILL.", self.process.pid)
                self.process.kill()
                await self.process.wait()
        except ProcessLookupError:
            pass
        finally:
            self.process = None
            self.current_run_id = None
