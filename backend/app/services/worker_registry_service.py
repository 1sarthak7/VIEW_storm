"""Worker Node Registry and Heartbeat Service."""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import ViewStormException
from app.core.logging import logger
from app.core.runner_config import runner_settings
from app.database.redis import redis_client
from app.database.session import AsyncSessionLocal
from app.models.worker_node import LoadGeneratorNode
from app.repositories.simulation_repository import SimulationRepository
from app.repositories.worker_repository import WorkerRepository
from app.schemas.run import SimulationStatus
from app.schemas.worker import (
    WorkerHeartbeatRequest,
    WorkerHeartbeatResponse,
    WorkerNodeResponse,
    WorkerNodeStatus,
    WorkerRegisterRequest,
    WorkerRegisterResponse,
)


def worker_heartbeat_key(node_id: str) -> str:
    return f"viewstorm:workers:{node_id}:heartbeat"


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class WorkerRegistryService:
    """Manages worker node registration, heartbeat leases in Redis, and staleness checks."""

    @staticmethod
    def _entity_to_response(entity: LoadGeneratorNode) -> WorkerNodeResponse:
        return WorkerNodeResponse(
            id=entity.id,
            worker_identifier=entity.worker_identifier,
            worker_name=entity.worker_name,
            hostname=entity.hostname,
            platform=entity.platform,
            cpu_cores=entity.cpu_cores,
            total_memory_bytes=entity.total_memory_bytes,
            available_memory_bytes=entity.available_memory_bytes,
            locust_version=entity.locust_version,
            software_version=entity.software_version,
            status=WorkerNodeStatus(entity.status) if entity.status in [s.value for s in WorkerNodeStatus] else WorkerNodeStatus.ONLINE,
            capacity=entity.capacity,
            last_heartbeat=entity.last_heartbeat,
            registered_at=entity.registered_at,
        )

    async def register_node(
        self,
        payload: WorkerRegisterRequest,
        db: Optional[AsyncSession] = None,
        redis: Optional[Redis] = None,
    ) -> WorkerRegisterResponse:
        """Register a new or returning worker node and store Redis lease."""
        r = redis or redis_client

        # Validate Locust version compatibility
        status = WorkerNodeStatus.ONLINE
        if payload.locust_version != runner_settings.pinned_locust_version:
            logger.warning(
                "Worker '%s' Locust version mismatch: reported '%s', expected '%s'",
                payload.worker_identifier,
                payload.locust_version,
                runner_settings.pinned_locust_version,
            )
            status = WorkerNodeStatus.INCOMPATIBLE

        # Token hashing
        token_hash = hash_token(payload.auth_token)

        async def _register(session: AsyncSession) -> Tuple[str, str, WorkerNodeStatus, datetime]:
            repo = WorkerRepository(session)
            existing = await repo.get_node_by_identifier(payload.worker_identifier)
            node_id = existing.id if existing else f"node-{uuid.uuid4().hex[:12]}"

            node = await repo.register_or_update_node(
                node_id=node_id,
                worker_identifier=payload.worker_identifier,
                worker_name=payload.worker_name,
                hostname=payload.hostname,
                platform=payload.platform,
                cpu_cores=payload.cpu_cores,
                total_memory_bytes=payload.total_memory_bytes,
                available_memory_bytes=payload.available_memory_bytes,
                locust_version=payload.locust_version,
                software_version=payload.software_version,
                build_identifier=payload.build_identifier,
                auth_token_hash=token_hash,
                capacity=payload.capacity,
                status=status.value,
            )
            return node.id, node.worker_identifier, WorkerNodeStatus(node.status), node.registered_at

        if db is not None:
            node_id, identifier, node_status, reg_at = await _register(db)
        else:
            async with AsyncSessionLocal() as session:
                node_id, identifier, node_status, reg_at = await _register(session)

        # Update Redis heartbeat lease
        lease_key = worker_heartbeat_key(node_id)
        await r.set(lease_key, node_status.value, ex=runner_settings.worker_heartbeat_timeout_seconds)

        logger.info("Worker node registered: id=%s identifier=%s status=%s", node_id, identifier, node_status.value)
        return WorkerRegisterResponse(
            worker_id=node_id,
            worker_identifier=identifier,
            status=node_status,
            registered_at=reg_at,
            message="Worker registered successfully" if node_status == WorkerNodeStatus.ONLINE else "Worker registered with version warning",
        )

    async def record_heartbeat(
        self,
        payload: WorkerHeartbeatRequest,
        db: Optional[AsyncSession] = None,
        redis: Optional[Redis] = None,
    ) -> WorkerHeartbeatResponse:
        """Process heartbeat from WorkerAgent, refresh Redis lease, check active run state."""
        r = redis or redis_client
        lease_key = worker_heartbeat_key(payload.worker_id)
        await r.set(lease_key, payload.status.value, ex=runner_settings.worker_heartbeat_timeout_seconds)

        should_stop = False

        async def _heartbeat(session: AsyncSession) -> None:
            nonlocal should_stop
            repo = WorkerRepository(session)
            await repo.update_node_heartbeat(
                node_id=payload.worker_id,
                status=payload.status.value,
                available_memory_bytes=payload.available_memory_bytes,
            )

            # If worker reports an active run, verify whether that run is still RUNNING
            if payload.active_run_id:
                sim_repo = SimulationRepository(session)
                run = await sim_repo.get_by_id(payload.active_run_id)
                if not run or run.status in [
                    SimulationStatus.STOPPED.value,
                    SimulationStatus.COMPLETED.value,
                    SimulationStatus.FAILED.value,
                    SimulationStatus.INTERRUPTED.value,
                ]:
                    should_stop = True

        if db is not None:
            await _heartbeat(db)
        else:
            async with AsyncSessionLocal() as session:
                await _heartbeat(session)

        return WorkerHeartbeatResponse(
            acknowledged=True,
            status=payload.status,
            active_run_id=payload.active_run_id,
            should_stop_run=should_stop,
        )

    async def get_node(
        self,
        node_id: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[WorkerNodeResponse]:
        """Fetch worker node by ID."""
        async def _get(session: AsyncSession) -> Optional[WorkerNodeResponse]:
            repo = WorkerRepository(session)
            node = await repo.get_node_by_id(node_id)
            return self._entity_to_response(node) if node else None

        if db is not None:
            return await _get(db)
        async with AsyncSessionLocal() as session:
            return await _get(session)

    async def list_active_nodes(
        self,
        status: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> List[WorkerNodeResponse]:
        """List registered worker nodes."""
        async def _list(session: AsyncSession) -> List[WorkerNodeResponse]:
            repo = WorkerRepository(session)
            nodes = await repo.list_nodes(status=status)
            return [self._entity_to_response(n) for n in nodes]

        if db is not None:
            return await _list(db)
        async with AsyncSessionLocal() as session:
            return await _list(session)

    async def mark_stale_workers(
        self,
        db: Optional[AsyncSession] = None,
    ) -> int:
        """Scan and flag workers as stale when their heartbeat exceeds timeout."""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=runner_settings.worker_heartbeat_timeout_seconds)

        async def _mark(session: AsyncSession) -> int:
            repo = WorkerRepository(session)
            return await repo.mark_stale_nodes(cutoff)

        if db is not None:
            return await _mark(db)
        async with AsyncSessionLocal() as session:
            return await _mark(session)


worker_registry_service = WorkerRegistryService()
