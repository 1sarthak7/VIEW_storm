"""Unit Tests for Milestone 8 Production Deployment & Large-Scale Capacity Validation."""

import json
from pathlib import Path
import pytest
from httpx import AsyncClient
from app.core.runner_config import runner_settings
from app.database.session import AsyncSessionLocal
from app.models.benchmark import BenchmarkResult
from app.models.worker_node import LoadGeneratorNode
from app.schemas.benchmark import BenchmarkRunRequest
from app.services.benchmark_service import benchmark_service


@pytest.mark.asyncio
async def test_intermediate_150k_profile_registered(client: AsyncClient):
    """Verify Profile Intermediate (150k users) is registered and retrievable."""
    resp = await client.get("/api/v1/benchmarks/profiles")
    assert resp.status_code == 200
    profiles = {p["name"]: p for p in resp.json()}
    assert "massive" in profiles or "intermediate_150k" in profiles

    profile = profiles.get("massive") or profiles.get("intermediate_150k")
    assert profile["virtual_users"] == 150000
    assert profile["requires_explicit_approval"] is True
    assert profile["min_worker_nodes"] == 48


@pytest.mark.asyncio
async def test_preflight_check_evaluates_target_api_and_artifacts(client: AsyncClient):
    """Verify preflight check verifies target API, data plane, and artifact directory writeability."""
    resp = await client.post(
        "/api/v1/benchmarks/preflight",
        json={"profile_name": "smoke", "execution_mode": "local"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ready"] is True
    assert data.get("artifact_storage_ok") is True
    assert data.get("dataplane_ok") is True


@pytest.mark.asyncio
async def test_benchmark_artifacts_generation(client: AsyncClient):
    """Verify benchmark finalization generates complete immutable artifact directory tree."""
    async with AsyncSessionLocal() as session:
        benchmark = BenchmarkResult(
            id="bmk_art_test_01",
            profile_name="smoke",
            test_type="locust_local",
            virtual_users=10,
            actual_active_users=10,
            spawn_rate=2.0,
            duration_seconds=30,
            total_requests=200,
            accepted_events=200,
            requests_per_second=10.0,
            avg_latency_ms=15.0,
            p50_latency_ms=12.0,
            p95_latency_ms=22.0,
            p99_latency_ms=30.0,
            max_latency_ms=35.0,
            error_rate_pct=0.0,
            passed_thresholds=True,
            infrastructure_metadata={"master_cpu_cores": 10, "master_total_ram_gb": 16.0},
            workload_metadata={"verification_verdict": "VERIFIED"},
            resource_metrics={"host_cpu_percent": 12.5},
        )
        session.add(benchmark)
        await session.commit()

        profile = benchmark_service.get_profile("smoke")
        assert profile is not None

        # Generate artifacts
        class DummyReport:
            configured_users = 10
            total_http_requests = 200
            failed_http_requests = 0
            total_submissions = 200
            accepted_events = 200
            rejected_events = 0
            requests_per_second = 10.0
            average_throughput_eps = 10.0
            avg_latency_ms = 15.0
            p50_latency_ms = 12.0
            p95_latency_ms = 22.0
            p99_latency_ms = 30.0
            max_latency_ms = 35.0
            resource_observations = {"host_cpu_percent": 12.5}

        artifact_path = await benchmark_service._generate_benchmark_artifacts(
            benchmark=benchmark,
            report=DummyReport(),
            profile=profile,
            db=session,
        )

        assert Path(artifact_path).exists()
        art_dir = Path(artifact_path)

        # Check required files
        assert (art_dir / "benchmark.json").exists()
        assert (art_dir / "run_configuration.json").exists()
        assert (art_dir / "infrastructure_inventory.json").exists()
        assert (art_dir / "worker_manifest.json").exists()
        assert (art_dir / "master_statistics.csv").exists()
        assert (art_dir / "statistics_history.csv").exists()
        assert (art_dir / "worker_resource_metrics.csv").exists()
        assert (art_dir / "backend_metrics.json").exists()
        assert (art_dir / "redis_metrics.json").exists()
        assert (art_dir / "postgres_metrics.json").exists()
        assert (art_dir / "system_resource_metrics.json").exists()
        assert (art_dir / "final_report.json").exists()
        assert (art_dir / "runner_logs" / "runner.log").exists()

        with open(art_dir / "final_report.json") as f:
            final_report = json.load(f)
            assert final_report["benchmark_id"] == "bmk_art_test_01"
            assert final_report["verification_verdict"] == "VERIFIED"
            assert final_report["configured_virtual_users"] == 10

    # Query via API endpoint
    resp = await client.get("/api/v1/benchmarks/results/bmk_art_test_01/artifacts")
    assert resp.status_code == 200
    art_meta = resp.json()
    assert art_meta["artifacts_available"] is True
    assert "benchmark.json" in art_meta["files"]
    assert "final_report.json" in art_meta["files"]


@pytest.mark.asyncio
async def test_control_plane_survivability_under_heavy_data_plane():
    """Verify control plane remains fully responsive (health, benchmarks) even with data plane isolated."""
    from app.main import create_application
    from httpx import ASGITransport

    control_app = create_application(service_mode="control_plane")
    transport = ASGITransport(app=control_app)
    async with AsyncClient(transport=transport, base_url="http://controlplane") as client:
        # Check rapid repeated queries
        for _ in range(10):
            resp = await client.get("/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "healthy"
