"""Tests for synthetic playback event ingestion, validation, and Redis atomic idempotency."""

from datetime import datetime, timezone
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _create_and_start_run(client: AsyncClient) -> str:
    res = await client.post(
        "/api/v1/runs",
        json={"name": "Event Ingestion Test", "virtual_users": 10, "duration_seconds": 60},
    )
    run_id = res.json()["id"]
    await client.post(f"/api/v1/runs/{run_id}/start")
    return run_id


async def test_ingest_valid_playback_event(client: AsyncClient):
    """Test submitting a valid synthetic playback event to a running simulation."""
    run_id = await _create_and_start_run(client)
    payload = {
        "event_id": "evt-001",
        "run_id": run_id,
        "viewer_id": "viewer-001",
        "video_id": "video-100",
        "event_type": "playback_start",
        "watch_duration_ms": 15000,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": {"device": "synthetic_client_1"},
    }
    response = await client.post("/api/v1/events/playback", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert data["event_id"] == "evt-001"
    assert data["run_id"] == run_id


async def test_idempotency_duplicate_event_handling(client: AsyncClient):
    """Test that submitting duplicate event IDs does not increment accepted count."""
    run_id = await _create_and_start_run(client)
    payload = {
        "event_id": "evt-duplicate-check",
        "run_id": run_id,
        "viewer_id": "viewer-002",
        "video_id": "video-100",
        "event_type": "playback_progress",
        "watch_duration_ms": 20000,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # First submission -> accepted
    res1 = await client.post("/api/v1/events/playback", json=payload)
    assert res1.status_code == 202
    assert res1.json()["status"] == "accepted"

    # Second submission (identical event_id) -> duplicate
    res2 = await client.post("/api/v1/events/playback", json=payload)
    assert res2.status_code == 202
    assert res2.json()["status"] == "duplicate"

    # Check stats: accepted should be 1, duplicate should be 1, total should be 2
    stats_res = await client.get(f"/api/v1/runs/{run_id}/stats")
    stats = stats_res.json()
    assert stats["accepted_events"] == 1
    assert stats["duplicate_events"] == 1
    assert stats["total_events"] == 2


async def test_reject_event_for_inactive_simulation(client: AsyncClient):
    """Test that events cannot be submitted to pending or stopped simulations."""
    res = await client.post(
        "/api/v1/runs",
        json={"name": "Pending Run Test", "virtual_users": 5, "duration_seconds": 30},
    )
    pending_run_id = res.json()["id"]

    payload = {
        "event_id": "evt-rejected-1",
        "run_id": pending_run_id,
        "viewer_id": "viewer-003",
        "video_id": "video-100",
        "event_type": "playback_start",
        "watch_duration_ms": 5000,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    response = await client.post("/api/v1/events/playback", json=payload)
    assert response.status_code == 409
    assert "is not active" in response.json()["error"]["message"]


async def test_reject_event_with_invalid_payload(client: AsyncClient):
    """Test rejection when payload is missing required fields or has invalid values."""
    run_id = await _create_and_start_run(client)

    bad_payload = {
        "event_id": "evt-bad",
        "run_id": run_id,
        "video_id": "video-100",
        "event_type": "playback_start",
        "watch_duration_ms": -100,
        "timestamp": "not-a-timestamp",
    }
    response = await client.post("/api/v1/events/playback", json=bad_payload)
    assert response.status_code == 422


async def test_batch_event_ingestion(client: AsyncClient):
    """Test batch ingestion endpoint with Redis counters."""
    run_id = await _create_and_start_run(client)
    now = datetime.now(timezone.utc).isoformat()
    batch = {
        "events": [
            {
                "event_id": f"batch-evt-{i}",
                "run_id": run_id,
                "viewer_id": f"viewer-{i}",
                "video_id": "vid-1",
                "event_type": "playback_start",
                "watch_duration_ms": 1000 * i,
                "timestamp": now,
            }
            for i in range(1, 6)
        ]
    }
    response = await client.post("/api/v1/events/playback/batch", json=batch)
    assert response.status_code == 202
    data = response.json()
    assert data["total"] == 5
    assert data["accepted"] == 5
    assert data["duplicates"] == 0
    assert data["rejected"] == 0
