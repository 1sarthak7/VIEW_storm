"""Tests for health check endpoints."""

from fastapi.testclient import TestClient


def test_root_health_endpoint(client: TestClient):
    """Verify GET /health returns 200 with valid structure."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert data["environment"] == "local"
    assert "uptime_seconds" in data
    assert data["uptime_seconds"] >= 0


def test_v1_health_endpoint(client: TestClient):
    """Verify GET /api/v1/health returns matching health status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
