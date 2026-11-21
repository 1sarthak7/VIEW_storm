"""Unit Tests for Worker Capacity Calibration Service and API Endpoints."""

from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient
from app.database.session import AsyncSessionLocal
from app.models.worker_calibration import WorkerCalibration
from app.models.worker_node import LoadGeneratorNode
from app.schemas.stats import SimulationReportResponse
from app.schemas.worker_calibration import (
    CalibrationStepResult,
    WorkerCalibrationRequest,
)
from app.services.worker_calibration_service import worker_calibration_service


@pytest.mark.asyncio
async def test_worker_calibration_saturation_detection():
    """Verify saturation bottleneck detection when CPU threshold is exceeded."""
    req = WorkerCalibrationRequest(
        steps=[10, 25, 50],
        step_duration_seconds=5,
        max_cpu_pct_threshold=80.0,
    )

    # Mock _execute_step to simulate stable at 10 and 25, then saturated at 50
    step10 = CalibrationStepResult(
        users=10, duration_seconds=5, requests_per_second=20.0, total_requests=100,
        accepted_events=100, error_rate_pct=0.0, avg_latency_ms=15.0, p50_latency_ms=12.0,
        p95_latency_ms=25.0, p99_latency_ms=35.0, worker_cpu_pct=35.0, worker_ram_mb=500.0,
        worker_ram_pct=30.0, is_saturated=False,
    )
    step25 = CalibrationStepResult(
        users=25, duration_seconds=5, requests_per_second=50.0, total_requests=250,
        accepted_events=250, error_rate_pct=0.0, avg_latency_ms=18.0, p50_latency_ms=15.0,
        p95_latency_ms=30.0, p99_latency_ms=45.0, worker_cpu_pct=60.0, worker_ram_mb=650.0,
        worker_ram_pct=35.0, is_saturated=False,
    )
    step50 = CalibrationStepResult(
        users=50, duration_seconds=5, requests_per_second=70.0, total_requests=350,
        accepted_events=340, error_rate_pct=0.0, avg_latency_ms=45.0, p50_latency_ms=35.0,
        p95_latency_ms=90.0, p99_latency_ms=150.0, worker_cpu_pct=88.5, worker_ram_mb=900.0,  # CPU > 80%
        worker_ram_pct=50.0, is_saturated=False,
    )

    with patch.object(worker_calibration_service, "_execute_step", side_effect=[step10, step25, step50]):
        async with AsyncSessionLocal() as session:
            result = await worker_calibration_service.calibrate_worker(
                worker_node_id=None,
                request=req,
                db=session,
            )

    assert result.max_stable_users == 25
    assert result.max_stable_rps == 50.0
    assert result.recommended_capacity == 18  # 75% of 25
    assert result.saturation_bottleneck is not None
    assert "CPU utilization (88.5%) exceeded" in result.saturation_bottleneck


@pytest.mark.asyncio
async def test_worker_calibration_api_endpoints(client: AsyncClient):
    """Verify listing and retrieving calibration records through API."""
    async with AsyncSessionLocal() as session:
        cal = WorkerCalibration(
            worker_node_id="test_node_1",
            worker_identifier="worker-agent-alpha",
            cpu_cores=8,
            total_memory_mb=16384.0,
            max_stable_users=250,
            max_stable_rps=320.0,
            recommended_capacity=187,
            saturation_bottleneck="CPU utilization (89.2%) exceeded 85.0%",
        )
        session.add(cal)
        await session.commit()

    # List calibrations
    list_res = await client.get("/api/v1/worker-nodes/calibrations")
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) >= 1
    assert items[0]["worker_identifier"] == "worker-agent-alpha"

    # Get single node calibration
    node_res = await client.get("/api/v1/worker-nodes/test_node_1/calibration")
    assert node_res.status_code == 200
    data = node_res.json()
    assert data["recommended_capacity"] == 187
    assert data["max_stable_users"] == 250
