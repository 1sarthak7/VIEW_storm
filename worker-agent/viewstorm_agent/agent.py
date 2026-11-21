"""WorkerAgent: Outbound-Only Distributed Load Generator Agent."""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import httpx

from viewstorm_agent.configuration import AgentSettings, agent_settings
from viewstorm_agent.process_manager import WorkerProcessManager
from viewstorm_agent.system_metrics import collect_system_info, collect_utilization

logger = logging.getLogger("viewstorm.agent")


class WorkerAgent:
    """Independent agent process running on load generator nodes."""

    def __init__(self, settings: Optional[AgentSettings] = None) -> None:
        self.settings = settings or agent_settings
        self.worker_id: Optional[str] = None
        self.process_manager = WorkerProcessManager()
        self.is_running = False
        self._shutdown_event = asyncio.Event()

    async def register(self, client: httpx.AsyncClient) -> bool:
        """Register node with backend control plane."""
        system_info = collect_system_info()
        payload = {
            "worker_identifier": self.settings.worker_identifier,
            "worker_name": self.settings.worker_name,
            "hostname": system_info["hostname"],
            "platform": system_info["platform"],
            "cpu_cores": system_info["cpu_cores"],
            "total_memory_bytes": system_info["total_memory_bytes"],
            "available_memory_bytes": system_info["available_memory_bytes"],
            "locust_version": system_info["locust_version"],
            "software_version": system_info["software_version"],
            "build_identifier": system_info["build_identifier"],
            "capacity": self.settings.capacity,
            "auth_token": self.settings.auth_token,
        }

        url = f"{self.settings.server_url.rstrip('/')}/api/v1/worker-nodes/register"
        try:
            resp = await client.post(url, json=payload, timeout=10.0)
            if resp.status_code == 201:
                data = resp.json()
                self.worker_id = data["worker_id"]
                logger.info("Worker registered successfully. worker_id=%s, status=%s", self.worker_id, data["status"])
                return True
            else:
                logger.error("Failed to register worker: HTTP %s - %s", resp.status_code, resp.text)
                return False
        except Exception as exc:
            logger.error("Registration request error: %s", exc)
            return False

    async def _heartbeat_loop(self, client: httpx.AsyncClient) -> None:
        """Periodic heartbeat loop reporting resource utilization."""
        url = f"{self.settings.server_url.rstrip('/')}/api/v1/worker-nodes/heartbeat"

        while not self._shutdown_event.is_set():
            try:
                if self.worker_id:
                    util = collect_utilization()
                    payload = {
                        "worker_id": self.worker_id,
                        "hostname": collect_system_info()["hostname"],
                        "status": "busy" if self.process_manager.is_running() else "online",
                        "active_run_id": self.process_manager.current_run_id,
                        "active_worker_processes": 1 if self.process_manager.is_running() else 0,
                        "cpu_utilization": util["cpu_utilization"],
                        "ram_utilization": util["ram_utilization"],
                        "available_memory_bytes": util["available_memory_bytes"],
                        "software_version": "1.0.0",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    resp = await client.post(url, json=payload, timeout=5.0)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("should_stop_run") and self.process_manager.is_running():
                            logger.info("Control plane requested stop for run=%s", self.process_manager.current_run_id)
                            await self.process_manager.stop_worker()
            except Exception as exc:
                logger.debug("Heartbeat error: %s", exc)

            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self.settings.heartbeat_interval_seconds,
                )
            except asyncio.TimeoutError:
                pass

    async def _poll_assignment_loop(self, client: httpx.AsyncClient) -> None:
        """Poll control plane for workload assignments."""
        while not self._shutdown_event.is_set():
            try:
                if self.worker_id and not self.process_manager.is_running():
                    url = f"{self.settings.server_url.rstrip('/')}/api/v1/worker-nodes/{self.worker_id}/assignments"
                    resp = await client.get(url, timeout=5.0)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("has_assignment") and data.get("assignment"):
                            assignment = data["assignment"]
                            logger.info(
                                "Received assignment for run=%s (users=%s, master=%s:%s)",
                                assignment["run_id"],
                                assignment["assigned_users"],
                                assignment["master_host"],
                                assignment["master_port"],
                            )
                            # Start worker process
                            locustfile = self.settings.locustfile_path
                            if not locustfile or not locustfile.exists():
                                logger.error("Locustfile not found at %s", locustfile)
                            else:
                                await self.process_manager.start_worker(
                                    run_id=assignment["run_id"],
                                    master_host=assignment["master_host"],
                                    master_port=assignment["master_port"],
                                    target_host=assignment["target_host"],
                                    locustfile=locustfile,
                                    event_type=assignment.get("event_type", "playback_start"),
                                    watch_min=assignment.get("watch_duration_min", 5),
                                    watch_max=assignment.get("watch_duration_max", 60),
                                )
                                # Acknowledge
                                ack_url = f"{self.settings.server_url.rstrip('/')}/api/v1/worker-nodes/{self.worker_id}/assignments/{assignment['run_id']}/acknowledge"
                                ack_payload = {
                                    "run_id": assignment["run_id"],
                                    "worker_id": self.worker_id,
                                    "accepted": True,
                                    "worker_process_count": 1,
                                }
                                await client.post(ack_url, json=ack_payload, timeout=5.0)
            except Exception as exc:
                logger.debug("Poll assignment error: %s", exc)

            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self.settings.poll_interval_seconds,
                )
            except asyncio.TimeoutError:
                pass

    async def run(self) -> None:
        """Run worker agent lifecycle."""
        self.is_running = True
        logger.info("Starting ViewStorm Worker Agent (%s)...", self.settings.worker_name)

        async with httpx.AsyncClient() as client:
            registered = False
            while not registered and not self._shutdown_event.is_set():
                registered = await self.register(client)
                if not registered:
                    logger.info("Retrying registration in 3 seconds...")
                    try:
                        await asyncio.wait_for(self._shutdown_event.wait(), timeout=3.0)
                    except asyncio.TimeoutError:
                        pass

            if self._shutdown_event.is_set():
                return

            heartbeat_task = asyncio.create_task(self._heartbeat_loop(client))
            poll_task = asyncio.create_task(self._poll_assignment_loop(client))

            try:
                await self._shutdown_event.wait()
            finally:
                heartbeat_task.cancel()
                poll_task.cancel()
                await self.process_manager.stop_worker()
                logger.info("Worker Agent stopped.")

    def stop(self) -> None:
        """Signal shutdown to all agent loops."""
        self._shutdown_event.set()
