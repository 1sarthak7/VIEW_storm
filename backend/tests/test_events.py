"""Tests for synthetic playback event ingestion, validation, and idempotency."""

from datetime import datetime, timezone
from fastapi.testclient import TestClient


def _create_and_start_run(client: TestClient) -> str:
    res = client.post(
        "/api/v1/runs",
        json={"name": "Event Ingestion Test", "virtual_users": 10, "duration_seconds": 60},
    )
    run_id = res.json()["id"]
    client.post(f"/api/v1/runs/{run_id}/start")
    return run_id


def test_ingest_valid_playback_event(client: TestClient):
    """Test submitting a valid synthetic playback event to a running simulation."""
    run_id = _create_and_start_run(client)
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
    response = client.post("/api/v1/events/playback", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert data["event_id"] == "evt-001"
    assert data["run_id"] == run_id


def test_idempotency_duplicate_event_handling(client: TestClient):
    """Test that submitting duplicate event IDs does not increment accepted count."""
    run_id = _create_and_start_run(client)
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
    res1 = client.post("/api/v1/events/playback", json=payload)
    assert res1.status_code == 202
    assert res1.json()["status"] == "accepted"

    # Second submission (identical event_id) -> duplicate
    res2 = client.post("/api/v1/events/playback", json=payload)
    assert res2.status_code == 202
    assert res2.json()["status"] == "duplicate"

    # Check stats: accepted should be 1, duplicate should be 1, total should be 2
    stats_res = client.get(f"/api/v1/runs/{run_id}/stats")
    stats = stats_res.json()
    assert stats["accepted_events"] == 1
    assert stats["duplicate_events"] == 1
    assert stats["total_events"] == 2


def test_reject_event_for_inactive_simulation(client: TestClient):
    """Test that events cannot be submitted to pending or stopped simulations."""
    res = client.post(
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
    response = client.post("/api/v1/events/playback", json=payload)
    assert response.status_code == 409
    assert "is not active" in response.json()["error"]["message"]


def test_reject_event_with_invalid_payload(client: TestClient):
    """Test rejection when payload is missing required fields or has invalid values."""
    run_id = _create_and_start_run(client)

    # Missing viewer_id
    bad_payload = {
        "event_id": "evt-bad",
        "run_id": run_id,
        "video_id": "video-100",
        "event_type": "playback_start",
        "watch_duration_ms": -100,  # Negative duration invalid
        "timestamp": "not-a-timestamp",
    }
    response = client.post("/api/v1/events/playback", json=bad_payload)
    assert response.status_code == 422


def test_batch_event_ingestion(client: TestClient):
    """Test batch ingestion endpoint."""
    run_id = _create_and_start_run(client)
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
    response = client.post("/api/v1/events/playback/batch", json=batch)
    assert response.status_code == 202
    data = response.json()
    assert data["total"] == 5
    assert data["accepted"] == 5
    assert data["duplicates"] == 0
    assert data["rejected"] == 0
