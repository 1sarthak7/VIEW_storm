"""Worker Assignment and Capacity-Aware Workload Distribution Service."""

import json
import math
from typing import Dict, List, Optional, Tuple
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import ViewStormException
from app.core.logging import logger
from app.core.runner_config import runner_settings
from app.database.redis import redis_client
from app.database.session import AsyncSessionLocal
from app.models.worker_node import LoadGeneratorNode
from app.repositories.worker_repository import WorkerRepository
from app.schemas.run import SimulationRunResponse
from app.schemas.worker import (
    WorkerAssignment,
    WorkerAssignmentAcknowledgeRequest,
    WorkerAssignmentResponse,
    WorkerNodeStatus,
)
from app.services.worker_registry_service import worker_heartbeat_key


def worker_assignment_key(worker_id: str) -> str:
    return f"viewstorm:workers:{worker_id}:assignment"


class NoActiveWorkersAvailableError(ViewStormException):
    def __init__(self, run_id: str):
        super().__init__(
            message=f"No active online worker nodes available to execute distributed simulation '{run_id}'.",
            status_code=400,
            details={"run_id": run_id},
        )


class InsufficientWorkerCapacityError(ViewStormException):
    def __init__(self, requested: int, total_capacity: int):
        super().__init__(
            message=f"Requested {requested} virtual users exceeds total available worker cluster capacity of {total_capacity}.",
            status_code=400,
            details={"requested": requested, "total_capacity": total_capacity},
        )


class WorkerAssignmentService:
    """Calculates deterministic, capacity-aware user distribution and manages worker assignments."""

    def distribute_users(
        self,
        total_users: int,
        total_spawn_rate: float,
        workers: List[LoadGeneratorNode],
    ) -> List[Tuple[LoadGeneratorNode, int, float]]:
        """
        Deterministically distribute total virtual users across worker nodes proportional to capacity.
        Guarantees that the sum of assigned users strictly equals total_users.
        """
        k = len(workers)
        if k == 0:
            return []

        if total_users < k:
            # Fewer users than workers: assign 1 user each to the first k workers
            allocations = []
            users_left = total_users
            rate_per_user = total_spawn_rate / total_users
            for i, worker in enumerate(workers):
                u = 1 if i < total_users else 0
                r = round(rate_per_user * u, 2)
                allocations.append((worker, u, r))
            return allocations

        total_capacity = sum(w.capacity for w in workers)
        if total_capacity <= 0:
            total_capacity = k * 100

        # Initial proportional user allocation
        proportions = [w.capacity / total_capacity for w in workers]
        exact_users = [total_users * p for p in proportions]
        allocated_users = [max(1, math.floor(eu)) for eu in exact_users]

        remainder = total_users - sum(allocated_users)

        if remainder > 0:
            # Sort by fractional part descending
            fractions = sorted(
                range(k),
                key=lambda i: (exact_users[i] - math.floor(exact_users[i])),
                reverse=True,
            )
            for idx in range(remainder):
                worker_idx = fractions[idx % k]
                allocated_users[worker_idx] += 1
        elif remainder < 0:
            # If floor + max(1) produced an overshoot, decrement from workers with > 1 user
            deficit = abs(remainder)
            candidates = sorted(
                [i for i in range(k) if allocated_users[i] > 1],
                key=lambda i: allocated_users[i],
                reverse=True,
            )
            for idx in range(deficit):
                if candidates:
                    allocated_users[candidates[idx % len(candidates)]] -= 1

        # Calculate proportional spawn rates
        allocated_rates = []
        for i, u in enumerate(allocated_users):
            rate = round((u / total_users) * total_spawn_rate, 2)
            allocated_rates.append(rate)

        # Fix rounding difference in spawn rate
        rate_diff = round(total_spawn_rate - sum(allocated_rates), 2)
        if allocated_rates:
            allocated_rates[0] = round(allocated_rates[0] + rate_diff, 2)

        return [
            (workers[i], allocated_users[i], allocated_rates[i])
            for i in range(k)
        ]

    async def allocate_workers_for_run(
        self,
        run: SimulationRunResponse,
        db: AsyncSession,
        redis: Redis,
        target_host: str,
        master_host: Optional[str] = None,
        master_port: Optional[int] = None,
    ) -> List[WorkerAssignment]:
        """Select eligible online workers, distribute load, create DB assignments and Redis lease."""
        repo = WorkerRepository(db)
        candidate_nodes = await repo.list_nodes(status=WorkerNodeStatus.ONLINE.value)

        # Filter nodes that have an active heartbeat lease in Redis
        active_nodes: List[LoadGeneratorNode] = []
        for node in candidate_nodes:
            lease = await redis.get(worker_heartbeat_key(node.id))
            if lease is not None:
                active_nodes.append(node)

        if not active_nodes:
            logger.error("No active online worker nodes available for distributed run=%s", run.id)
            raise NoActiveWorkersAvailableError(run.id)

        m_host = master_host or runner_settings.master_advertise_host
        m_port = master_port or runner_settings.master_bind_port

        distributions = self.distribute_users(
            total_users=run.virtual_users,
            total_spawn_rate=run.spawn_rate,
            workers=active_nodes,
        )

        assignments: List[WorkerAssignment] = []
        ttl = run.duration_seconds + 300

        for node, assigned_users, spawn_rate in distributions:
            if assigned_users == 0:
                continue

            assignment = WorkerAssignment(
                run_id=run.id,
                master_host=m_host,
                master_port=m_port,
                assigned_users=assigned_users,
                spawn_rate=spawn_rate,
                duration_seconds=run.duration_seconds,
                target_host=target_host,
                event_type=run.event_type,
                watch_duration_min=run.watch_duration_min,
                watch_duration_max=run.watch_duration_max,
            )

            # Persist assignment in PostgreSQL
            await repo.create_assignment(
                run_id=run.id,
                worker_node_id=node.id,
                worker_identifier=node.worker_identifier,
                assigned_users=assigned_users,
                worker_process_count=1,
            )

            # Store assignment in Redis for worker agent polling
            key = worker_assignment_key(node.id)
            await redis.set(key, assignment.model_dump_json(), ex=ttl)
            assignments.append(assignment)

            logger.info(
                "Assigned distributed run=%s to worker=%s (%s users, spawn_rate=%s)",
                run.id,
                node.id,
                assigned_users,
                spawn_rate,
            )

        return assignments

    async def get_worker_assignment(
        self,
        worker_id: str,
        redis: Optional[Redis] = None,
    ) -> WorkerAssignmentResponse:
        """Poll current pending assignment for a worker node."""
        r = redis or redis_client
        key = worker_assignment_key(worker_id)
        data = await r.get(key)
        if not data:
            return WorkerAssignmentResponse(has_assignment=False)

        payload = json.loads(data)
        assignment = WorkerAssignment(**payload)
        return WorkerAssignmentResponse(has_assignment=True, assignment=assignment)

    async def clear_worker_assignment(
        self,
        worker_id: str,
        redis: Optional[Redis] = None,
    ) -> None:
        """Clear assignment lease in Redis."""
        r = redis or redis_client
        await r.delete(worker_assignment_key(worker_id))

    async def acknowledge_assignment(
        self,
        payload: WorkerAssignmentAcknowledgeRequest,
        db: Optional[AsyncSession] = None,
    ) -> bool:
        """Acknowledge worker launch and transition SimulationWorker to running or failed."""
        async def _ack(session: AsyncSession) -> bool:
            repo = WorkerRepository(session)
            status = "running" if payload.accepted else "failed"
            updated = await repo.update_assignment_status(
                run_id=payload.run_id,
                worker_node_id=payload.worker_id,
                status=status,
                error_message=payload.error_message,
            )
            if updated and payload.accepted:
                await repo.update_node_status(payload.worker_id, "busy")
            return updated is not None

        if db is not None:
            return await _ack(db)
        async with AsyncSessionLocal() as session:
            return await _ack(session)


worker_assignment_service = WorkerAssignmentService()
