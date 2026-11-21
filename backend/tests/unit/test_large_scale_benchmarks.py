"""Unit Tests for Milestone 7 Large-Scale Benchmarking Framework."""

import pytest
from httpx import AsyncClient
from app.database.session import AsyncSessionLocal
from app.models.benchmark import BenchmarkResult
from app.models.worker_node import LoadGeneratorNode
from app.schemas.benchmark import BenchmarkRunRequest
from app.services.benchmark_service import benchmark_service
from app.services.emergency_service import emergency_service


@pytest.mark.asyncio
async def test_all_9_profiles_registered(client: AsyncClient):
    """Verify all 9 Milestone 7 standardized profiles are registered and retrievable."""
    resp = await client.get("/api/v1/benchmarks/profiles")
    assert resp.status_code == 200
    profiles = resp.json()
    profile_map = {p["name"]: p for p in profiles}

    expected_profiles = [
        "smoke",
        "baseline",
        "small",
        "medium",
        "large",
        "extended",
        "high_capacity",
        "extreme",
        "target",
    ]
    for expected in expected_profiles:
        assert expected in profile_map, f"Missing profile {expected}"

    assert profile_map["smoke"]["virtual_users"] == 10
    assert profile_map["baseline"]["virtual_users"] == 100
    assert profile_map["small"]["virtual_users"] == 1000
    assert profile_map["medium"]["virtual_users"] == 5000
    assert profile_map["large"]["virtual_users"] == 10000
    assert profile_map["extended"]["virtual_users"] == 25000
    assert profile_map["high_capacity"]["virtual_users"] == 50000
    assert profile_map["extreme"]["virtual_users"] == 100000
    assert profile_map["target"]["virtual_users"] == 200000

    # Profiles >= 25k require explicit operator approval
    assert profile_map["extended"]["requires_explicit_approval"] is True
    assert profile_map["target"]["requires_explicit_approval"] is True


@pytest.mark.asyncio
async def test_preflight_check_blocks_on_insufficient_worker_capacity(client: AsyncClient):
    """Verify preflight rejects distributed benchmark when worker capacity is below required virtual users."""
    # Ensure starting with no or low-capacity workers
    resp = await client.post(
        "/api/v1/benchmarks/preflight",
        json={"profile_name": "medium", "execution_mode": "distributed"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ready"] is False
    assert data["required_users"] == 5000
    assert any("worker capacity" in msg.lower() or "worker nodes" in msg.lower() for msg in data["messages"])


@pytest.mark.asyncio
async def test_preflight_check_blocks_under_emergency_stop(client: AsyncClient):
    """Verify preflight rejects any benchmark while emergency stop is active."""
    await emergency_service.trigger_emergency_stop(reason="Lockdown test", operator="admin")
    try:
        resp = await client.post(
            "/api/v1/benchmarks/preflight",
            json={"profile_name": "smoke", "execution_mode": "local"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ready"] is False
        assert any("emergency stop" in msg.lower() for msg in data["messages"])
    finally:
        await emergency_service.clear_emergency_stop(operator="admin")


@pytest.mark.asyncio
async def test_high_tier_profile_requires_explicit_approval(client: AsyncClient):
    """Verify high-capacity profiles (>=25k) reject runs if approval_confirmed is False."""
    async with AsyncSessionLocal() as session:
        # Register 8 mock workers so min_worker_nodes (8) and capacity (32k >= 25k) pass preflight
        nodes = [
            LoadGeneratorNode(
                id=f"node_mock_{i}",
                worker_identifier=f"worker_cluster_node_{i}",
                worker_name=f"Worker-Cluster-{i}",
                hostname=f"worker-{i}.internal",
                platform="Linux",
                cpu_cores=16,
                total_memory_bytes=32 * 1024 * 1024 * 1024,
                available_memory_bytes=24 * 1024 * 1024 * 1024,
                locust_version="2.47.0",
                auth_token_hash="fake",
                status="online",
                capacity=4000,
            )
            for i in range(8)
        ]
        session.add_all(nodes)
        await session.commit()

    # Attempting to run extended profile without approval_confirmed flag should return 403
    resp = await client.post(
        "/api/v1/benchmarks/run",
        json={
            "profile_name": "extended",
            "execution_mode": "distributed",
            "approval_confirmed": False,
        },
    )
    assert resp.status_code == 403
    assert "requires explicit operator authorization" in resp.json()["error"]["message"]


@pytest.mark.asyncio
async def test_benchmark_incomparable_verdict(client: AsyncClient):
    """Verify comparison between radically mismatched workloads returns INCOMPARABLE."""
    async with AsyncSessionLocal() as session:
        b1 = BenchmarkResult(
            id="bmk_smoke_exp",
            profile_name="smoke",
            test_type="locust_local",
            virtual_users=10,
            spawn_rate=2.0,
            duration_seconds=30,
            requests_per_second=20.0,
            avg_latency_ms=10.0,
            p95_latency_ms=25.0,
            error_rate_pct=0.0,
        )
        b2 = BenchmarkResult(
            id="bmk_target_exp",
            profile_name="target",
            test_type="locust_distributed",
            virtual_users=200000,
            spawn_rate=5000.0,
            duration_seconds=1800,
            requests_per_second=18000.0,
            avg_latency_ms=45.0,
            p95_latency_ms=120.0,
            error_rate_pct=1.2,
        )
        session.add_all([b1, b2])
        await session.commit()

    resp = await client.get(
        "/api/v1/benchmarks/compare",
        params={"baseline_id": "bmk_smoke_exp", "candidate_id": "bmk_target_exp"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_comparable"] is False
    assert data["performance_verdict"] == "INCOMPARABLE"
    assert "Workload scale mismatch" in data["incomparable_reason"]
