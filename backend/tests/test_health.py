"""Tests for health check endpoints with live Redis & PostgreSQL verification."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_root_health_endpoint(client: AsyncClient):
    """Verify GET /health returns 200 with live dependency checks."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert data["version"] == "1.0.0"
    assert data["environment"] == "local"
    assert data["redis_status"] == "healthy"
    assert data["database_status"] == "healthy"
    assert "uptime_seconds" in data
    assert data["uptime_seconds"] >= 0


async def test_v1_health_endpoint(client: AsyncClient):
    """Verify GET /api/v1/health returns matching health status."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["redis_status"] == "healthy"
    assert data["database_status"] == "healthy"


async def test_prometheus_metrics_exposition(client: AsyncClient):
    """Verify GET /metrics exports Prometheus formatted metrics."""
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    content = response.text
    assert "viewstorm_http_requests_total" in content
    assert "viewstorm_active_simulations" in content
    assert "viewstorm_emergency_stop_active" in content
