"""Worker and Load Generator Node Repository for PostgreSQL."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.worker import SimulationWorker
from app.models.worker_node import LoadGeneratorNode


class WorkerRepository:
    """Encapsulates durable PostgreSQL queries and writes for worker nodes and assignments."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def register_or_update_node(
        self,
        node_id: str,
        worker_identifier: str,
        worker_name: str,
        hostname: str,
        platform: str,
        cpu_cores: int,
        total_memory_bytes: int,
        available_memory_bytes: int,
        locust_version: str,
        software_version: str,
        build_identifier: str,
        auth_token_hash: str,
        capacity: int,
        status: str = "online",
    ) -> LoadGeneratorNode:
        """Register a new node or update existing node by worker_identifier."""
        stmt = select(LoadGeneratorNode).where(LoadGeneratorNode.worker_identifier == worker_identifier)
        result = await self.session.execute(stmt)
        node = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)

        if node:
            node.worker_name = worker_name
            node.hostname = hostname
            node.platform = platform
            node.cpu_cores = cpu_cores
            node.total_memory_bytes = total_memory_bytes
            node.available_memory_bytes = available_memory_bytes
            node.locust_version = locust_version
            node.software_version = software_version
            node.build_identifier = build_identifier
            node.auth_token_hash = auth_token_hash
            node.capacity = capacity
            node.status = status
            node.last_heartbeat = now
            node.updated_at = now
        else:
            node = LoadGeneratorNode(
                id=node_id,
                worker_identifier=worker_identifier,
                worker_name=worker_name,
                hostname=hostname,
                platform=platform,
                cpu_cores=cpu_cores,
                total_memory_bytes=total_memory_bytes,
                available_memory_bytes=available_memory_bytes,
                locust_version=locust_version,
                software_version=software_version,
                build_identifier=build_identifier,
                auth_token_hash=auth_token_hash,
                capacity=capacity,
                status=status,
                last_heartbeat=now,
                registered_at=now,
                updated_at=now,
            )
            self.session.add(node)

        await self.session.commit()
        await self.session.refresh(node)
        return node

    async def get_node_by_id(self, node_id: str) -> Optional[LoadGeneratorNode]:
        """Fetch worker node by internal ID."""
        stmt = select(LoadGeneratorNode).where(LoadGeneratorNode.id == node_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_node_by_identifier(self, worker_identifier: str) -> Optional[LoadGeneratorNode]:
        """Fetch worker node by unique worker identifier."""
        stmt = select(LoadGeneratorNode).where(LoadGeneratorNode.worker_identifier == worker_identifier)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_nodes(self, status: Optional[str] = None) -> List[LoadGeneratorNode]:
        """Fetch worker nodes, optionally filtered by status."""
        stmt = select(LoadGeneratorNode)
        if status:
            stmt = stmt.where(LoadGeneratorNode.status == status)
        stmt = stmt.order_by(LoadGeneratorNode.registered_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_node_heartbeat(
        self,
        node_id: str,
        status: str,
        available_memory_bytes: Optional[int] = None,
    ) -> Optional[LoadGeneratorNode]:
        """Update worker node heartbeat timestamp and status."""
        now = datetime.now(timezone.utc)
        values: Dict[str, Any] = {
            "last_heartbeat": now,
            "status": status,
            "updated_at": now,
        }
        if available_memory_bytes is not None:
            values["available_memory_bytes"] = available_memory_bytes

        stmt = (
            update(LoadGeneratorNode)
            .where(LoadGeneratorNode.id == node_id)
            .values(**values)
            .returning(LoadGeneratorNode)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def update_node_status(self, node_id: str, status: str) -> Optional[LoadGeneratorNode]:
        """Update node status."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(LoadGeneratorNode)
            .where(LoadGeneratorNode.id == node_id)
            .values(status=status, updated_at=now)
            .returning(LoadGeneratorNode)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def mark_stale_nodes(self, cutoff_time: datetime) -> int:
        """Mark online nodes as stale if their last heartbeat is older than cutoff_time."""
        stmt = (
            update(LoadGeneratorNode)
            .where(
                LoadGeneratorNode.status.in_(["online", "busy"]),
                LoadGeneratorNode.last_heartbeat < cutoff_time,
            )
            .values(status="stale", updated_at=datetime.now(timezone.utc))
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

    # SimulationWorker Assignments

    async def create_assignment(
        self,
        run_id: str,
        worker_node_id: Optional[str],
        worker_identifier: str,
        assigned_users: int,
        worker_process_count: int = 1,
    ) -> SimulationWorker:
        """Record a worker assignment for a simulation run."""
        now = datetime.now(timezone.utc)
        worker = SimulationWorker(
            run_id=run_id,
            worker_node_id=worker_node_id,
            worker_identifier=worker_identifier,
            status="assigned",
            assigned_users=assigned_users,
            active_users=0,
            worker_process_count=worker_process_count,
            last_heartbeat=now,
        )
        self.session.add(worker)
        await self.session.commit()
        await self.session.refresh(worker)
        return worker

    async def get_assignment_by_run_and_worker(
        self,
        run_id: str,
        worker_node_id: str,
    ) -> Optional[SimulationWorker]:
        """Fetch worker assignment by run_id and worker_node_id."""
        stmt = select(SimulationWorker).where(
            SimulationWorker.run_id == run_id,
            SimulationWorker.worker_node_id == worker_node_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_assignments_for_run(self, run_id: str) -> List[SimulationWorker]:
        """Fetch all worker assignments for a run."""
        stmt = select(SimulationWorker).where(SimulationWorker.run_id == run_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_pending_or_active_assignment_for_node(
        self,
        worker_node_id: str,
    ) -> Optional[SimulationWorker]:
        """Get current assigned or running task for a worker node."""
        stmt = (
            select(SimulationWorker)
            .where(
                SimulationWorker.worker_node_id == worker_node_id,
                SimulationWorker.status.in_(["assigned", "running"]),
            )
            .order_by(SimulationWorker.id.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_assignment_status(
        self,
        run_id: str,
        worker_node_id: str,
        status: str,
        active_users: Optional[int] = None,
        started_at: Optional[datetime] = None,
        finished_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
        resource_info: Optional[Dict[str, Any]] = None,
    ) -> Optional[SimulationWorker]:
        """Update simulation worker status and metrics."""
        now = datetime.now(timezone.utc)
        values: Dict[str, Any] = {
            "status": status,
            "last_heartbeat": now,
        }
        if active_users is not None:
            values["active_users"] = active_users
        if started_at is not None:
            values["started_at"] = started_at
        if finished_at is not None:
            values["finished_at"] = finished_at
        if error_message is not None:
            values["error_message"] = error_message
        if resource_info is not None:
            values["resource_information"] = resource_info

        stmt = (
            update(SimulationWorker)
            .where(
                SimulationWorker.run_id == run_id,
                SimulationWorker.worker_node_id == worker_node_id,
            )
            .values(**values)
            .returning(SimulationWorker)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()
