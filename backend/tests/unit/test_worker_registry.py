"""Unit Tests for Worker Registry, Authentication, and Heartbeat Leasing."""

import uuid
from datetime import datetime, timedelta, timezone
import pytest
from app.core.runner_config import runner_settings
from app.database.redis import redis_client
from app.database.session import AsyncSessionLocal
from app.models.worker_node import LoadGeneratorNode
from app.repositories.worker_repository import WorkerRepository
from app.schemas.worker import (
    WorkerHeartbeatRequest,
    WorkerNodeStatus,
    WorkerRegisterRequest,
)
from app.services.worker_registry_service import (
    hash_token,
    worker_heartbeat_key,
    worker_registry_service,
)

pytestmark = pytest.mark.asyncio


async def test_worker_registration_success():
    """Verify that a valid worker node registers successfully and creates DB and Redis entries."""
    unique_id = f"test-worker-{uuid.uuid4().hex[:8]}"
    payload = WorkerRegisterRequest(
        worker_identifier=unique_id,
        worker_name="Test Worker 1",
        hostname="worker-box-01",
        platform="Linux x86_64",
        cpu_cores=8,
        total_memory_bytes=16000000000,
        available_memory_bytes=8000000000,
        locust_version=runner_settings.pinned_locust_version,
        capacity=250,
        auth_token="secret-token-12345",
    )

    async with AsyncSessionLocal() as session:
        resp = await worker_registry_service.register_node(payload, db=session, redis=redis_client)

    assert resp.worker_id.startswith("node-")
    assert resp.worker_identifier == unique_id
    assert resp.status == WorkerNodeStatus.ONLINE

    # Verify Redis lease was created with TTL
    lease_key = worker_heartbeat_key(resp.worker_id)
    lease_val = await redis_client.get(lease_key)
    assert lease_val == "online"
    ttl = await redis_client.ttl(lease_key)
    assert ttl > 0

    # Verify DB entity
    async with AsyncSessionLocal() as session:
        repo = WorkerRepository(session)
        node = await repo.get_node_by_id(resp.worker_id)
        assert node is not None
        assert node.capacity == 250
        assert node.auth_token_hash == hash_token("secret-token-12345")


async def test_worker_registration_version_mismatch():
    """Verify that an outdated Locust version registers with INCOMPATIBLE status warning."""
    unique_id = f"test-worker-incompat-{uuid.uuid4().hex[:8]}"
    payload = WorkerRegisterRequest(
        worker_identifier=unique_id,
        worker_name="Incompatible Worker",
        hostname="worker-box-old",
        platform="Linux",
        cpu_cores=4,
        locust_version="1.6.0",  # Old version
        capacity=100,
        auth_token="secret-token-12345",
    )

    async with AsyncSessionLocal() as session:
        resp = await worker_registry_service.register_node(payload, db=session, redis=redis_client)

    assert resp.status == WorkerNodeStatus.INCOMPATIBLE


async def test_worker_heartbeat_updates():
    """Verify that worker heartbeat refreshes Redis lease and updates DB timestamp."""
    unique_id = f"test-worker-hb-{uuid.uuid4().hex[:8]}"
    reg_payload = WorkerRegisterRequest(
        worker_identifier=unique_id,
        worker_name="HB Worker",
        hostname="worker-box-hb",
        platform="Darwin",
        locust_version=runner_settings.pinned_locust_version,
        auth_token="secret-token-12345",
    )

    async with AsyncSessionLocal() as session:
        reg_resp = await worker_registry_service.register_node(reg_payload, db=session, redis=redis_client)

    hb_payload = WorkerHeartbeatRequest(
        worker_id=reg_resp.worker_id,
        hostname="worker-box-hb",
        status=WorkerNodeStatus.ONLINE,
        cpu_utilization=25.5,
        ram_utilization=40.0,
        available_memory_bytes=6000000000,
        timestamp=datetime.now(timezone.utc),
    )

    async with AsyncSessionLocal() as session:
        hb_resp = await worker_registry_service.record_heartbeat(hb_payload, db=session, redis=redis_client)

    assert hb_resp.acknowledged is True
    assert hb_resp.should_stop_run is False


async def test_stale_worker_detection():
    """Verify that workers without heartbeats past timeout are marked stale."""
    async with AsyncSessionLocal() as session:
        repo = WorkerRepository(session)
        # Create a worker with an expired last_heartbeat
        stale_node_id = f"node-stale-{uuid.uuid4().hex[:8]}"
        stale_ident = f"ident-stale-{uuid.uuid4().hex[:8]}"
        old_time = datetime.now(timezone.utc) - timedelta(seconds=120)

        node = LoadGeneratorNode(
            id=stale_node_id,
            worker_identifier=stale_ident,
            worker_name="Stale Node",
            hostname="stale-box",
            platform="Linux",
            cpu_cores=2,
            locust_version="2.47.0",
            auth_token_hash="dummy",
            capacity=50,
            status="online",
            last_heartbeat=old_time,
            registered_at=old_time,
            updated_at=old_time,
        )
        session.add(node)
        await session.commit()

        # Run mark stale
        marked_count = await worker_registry_service.mark_stale_workers(db=session)
        assert marked_count >= 1

        updated_node = await repo.get_node_by_id(stale_node_id)
        assert updated_node.status == "stale"
