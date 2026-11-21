"""Unit Tests for Standardized Benchmarking Framework."""

import pytest
from httpx import AsyncClient
from app.database.session import AsyncSessionLocal
from app.models.benchmark import BenchmarkResult
from app.services.benchmark_service import benchmark_service


@pytest.mark.asyncio
async def test_list_benchmark_profiles(client: AsyncClient):
    """Verify retrieving predefined benchmark profiles."""
    resp = await client.get("/api/v1/benchmarks/profiles")
    assert resp.status_code == 200
    profiles = resp.json()
    profile_names = [p["name"] for p in profiles]
    assert "smoke" in profile_names
    assert "baseline" in profile_names
    assert "medium" in profile_names
    assert "high" in profile_names
    assert "distributed" in profile_names


@pytest.mark.asyncio
async def test_compare_benchmarks_improvement_verdict(client: AsyncClient):
    """Verify benchmark comparison delta calculations and verdict logic."""
    async with AsyncSessionLocal() as session:
        b1 = BenchmarkResult(
            id="bmk_base_test",
            profile_name="baseline",
            test_type="locust_local",
            virtual_users=50,
            spawn_rate=5.0,
            duration_seconds=60,
            total_requests=1000,
            requests_per_second=50.0,
            avg_latency_ms=25.0,
            p50_latency_ms=20.0,
            p95_latency_ms=45.0,
            p99_latency_ms=75.0,
            error_rate_pct=1.0,
            passed_thresholds=True,
        )
        b2 = BenchmarkResult(
            id="bmk_cand_test",
            profile_name="baseline",
            test_type="locust_local",
            virtual_users=50,
            spawn_rate=5.0,
            duration_seconds=60,
            total_requests=1200,
            requests_per_second=60.0,  # +20% RPS
            avg_latency_ms=22.0,
            p50_latency_ms=18.0,
            p95_latency_ms=40.0,
            p99_latency_ms=65.0,
            error_rate_pct=0.8,
            passed_thresholds=True,
        )
        session.add_all([b1, b2])
        await session.commit()

    resp = await client.get(
        "/api/v1/benchmarks/compare",
        params={"baseline_id": "bmk_base_test", "candidate_id": "bmk_cand_test"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["rps_delta_pct"] == 20.0
    assert data["performance_verdict"] == "IMPROVEMENT"


@pytest.mark.asyncio
async def test_compare_benchmarks_regression_verdict(client: AsyncClient):
    """Verify benchmark comparison flags latency degradation as REGRESSION."""
    async with AsyncSessionLocal() as session:
        b1 = BenchmarkResult(
            id="bmk_reg_base",
            profile_name="baseline",
            test_type="locust_local",
            virtual_users=50,
            spawn_rate=5.0,
            duration_seconds=60,
            total_requests=1000,
            requests_per_second=50.0,
            avg_latency_ms=20.0,
            p50_latency_ms=15.0,
            p95_latency_ms=30.0,
            p99_latency_ms=50.0,
            error_rate_pct=0.5,
            passed_thresholds=True,
        )
        b2 = BenchmarkResult(
            id="bmk_reg_cand",
            profile_name="baseline",
            test_type="locust_local",
            virtual_users=50,
            spawn_rate=5.0,
            duration_seconds=60,
            total_requests=800,
            requests_per_second=40.0,
            avg_latency_ms=35.0,
            p50_latency_ms=30.0,
            p95_latency_ms=65.0,  # >100% latency regression
            p99_latency_ms=95.0,
            error_rate_pct=3.5,
            passed_thresholds=False,
        )
        session.add_all([b1, b2])
        await session.commit()

    resp = await client.get(
        "/api/v1/benchmarks/compare",
        params={"baseline_id": "bmk_reg_base", "candidate_id": "bmk_reg_cand"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["performance_verdict"] == "REGRESSION"
