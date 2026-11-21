"""Tests for statistics aggregation, time-series metrics, and reports."""

from datetime import datetime, timezone
from fastapi.testclient import TestClient


def test_statistics_aggregation_accuracy(client: TestClient):
    """Verify statistics accurately count unique viewers, watch duration, and event breakdown."""
    # 1. Create and start run
    run_res = client.post(
        "/api/v1/runs",
        json={"name": "Stats Test", "virtual_users": 10, "duration_seconds": 60},
    )
    run_id = run_res.json()["id"]
    client.post(f"/api/v1/runs/{run_id}/start")

    # 2. Ingest events: 2 viewers, 3 events
    now = datetime.now(timezone.utc).isoformat()
    events = [
        {
            "event_id": "stat-evt-1",
            "run_id": run_id,
            "viewer_id": "v-1",
            "video_id": "vid-1",
            "event_type": "playback_start",
            "watch_duration_ms": 10000,
            "timestamp": now,
        },
        {
            "event_id": "stat-evt-2",
            "run_id": run_id,
            "viewer_id": "v-1",
            "video_id": "vid-1",
            "event_type": "playback_complete",
            "watch_duration_ms": 20000,
            "timestamp": now,
        },
        {
            "event_id": "stat-evt-3",
            "run_id": run_id,
            "viewer_id": "v-2",
            "video_id": "vid-1",
            "event_type": "playback_start",
            "watch_duration_ms": 30000,
            "timestamp": now,
        },
    ]

    for ev in events:
        res = client.post("/api/v1/events/playback", json=ev)
        assert res.status_code == 202

    # 3. Check statistics
    stats_res = client.get(f"/api/v1/runs/{run_id}/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["run_id"] == run_id
    assert stats["accepted_events"] == 3
    assert stats["unique_viewers_count"] == 2  # v-1 and v-2
    assert stats["total_watch_duration_ms"] == 60000
    assert stats["average_watch_duration_ms"] == 20000.0
    assert stats["events_by_type"]["playback_start"] == 2
    assert stats["events_by_type"]["playback_complete"] == 1


def test_metrics_and_report_endpoints(client: TestClient):
    """Verify metrics and final summary report endpoints return expected data."""
    run_res = client.post(
        "/api/v1/runs",
        json={"name": "Report Test", "virtual_users": 10, "duration_seconds": 30},
    )
    run_id = run_res.json()["id"]
    client.post(f"/api/v1/runs/{run_id}/start")

    # Ingest one event
    client.post(
        "/api/v1/events/playback",
        json={
            "event_id": "report-evt-1",
            "run_id": run_id,
            "viewer_id": "viewer-rpt",
            "video_id": "vid-1",
            "event_type": "playback_start",
            "watch_duration_ms": 12000,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    # Metrics
    metrics_res = client.get(f"/api/v1/runs/{run_id}/metrics")
    assert metrics_res.status_code == 200
    metrics_data = metrics_res.json()
    assert metrics_data["run_id"] == run_id
    assert len(metrics_data["metrics"]) > 0

    # Stop run
    client.post(f"/api/v1/runs/{run_id}/stop")

    # Report
    report_res = client.get(f"/api/v1/runs/{run_id}/report")
    assert report_res.status_code == 200
    report = report_res.json()
    assert report["run_id"] == run_id
    assert report["status"] == "stopped"
    assert report["accepted_events"] == 1
    assert report["unique_viewers"] == 1
    assert report["total_watch_duration_ms"] == 12000
