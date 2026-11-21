"""Integration Tests for End-to-End Pipeline, Concurrency, and Restart Persistence."""

import asyncio
from datetime import datetime, timezone
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.main import app
from app.models.event_summary import EventSummary

pytestmark = pytest.mark.asyncio


async def test_full_pipeline_event_ingestion_and_postgres_flush(client: AsyncClient):
    """Verify complete flow: Create -> Start -> Ingest -> Stats -> Stop -> DB Persistence."""
    # 1. Create Run
    create_res = await client.post(
        "/api/v1/runs",
        json={"name": "End-to-End Test", "virtual_users": 15, "duration_seconds": 60},
    )
    assert create_res.status_code == 201
    run_id = create_res.json()["id"]

    # 2. Start Run
    start_res = await client.post(f"/api/v1/runs/{run_id}/start")
    assert start_res.status_code == 200

    # 3. Ingest Events
    now = datetime.now(timezone.utc).isoformat()
    for i in range(1, 6):
        res = await client.post(
            "/api/v1/events/playback",
            json={
                "event_id": f"pipeline-evt-{i}",
                "run_id": run_id,
                "viewer_id": f"viewer-{i % 2}",  # 2 unique viewers
                "video_id": "vid-pipeline",
                "event_type": "playback_start" if i % 2 == 1 else "playback_complete",
                "watch_duration_ms": 10000 * i,
                "timestamp": now,
            },
        )
        assert res.status_code == 202
        assert res.json()["status"] == "accepted"

    # 4. Check Redis Live Stats
    stats_res = await client.get(f"/api/v1/runs/{run_id}/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["accepted_events"] == 5
    assert stats["unique_viewers_count"] == 2
    assert stats["total_watch_duration_ms"] == 150000

    # 5. Stop Run (triggers PostgreSQL sync)
    stop_res = await client.post(f"/api/v1/runs/{run_id}/stop")
    assert stop_res.status_code == 200
    assert stop_res.json()["status"] == "stopped"

    # 6. Verify Durable Summary in PostgreSQL
    async with AsyncSessionLocal() as session:
        stmt = select(EventSummary).where(EventSummary.run_id == run_id)
        result = await session.execute(stmt)
        summaries = list(result.scalars().all())
        assert len(summaries) >= 1
        total_accepted = sum(s.accepted_count for s in summaries)
        assert total_accepted == 5


async def test_concurrent_duplicate_submission_race_protection(client: AsyncClient):
    """Verify that multiple concurrent identical event submissions result in exactly ONE accepted event."""
    create_res = await client.post(
        "/api/v1/runs",
        json={"name": "Race Condition Test", "virtual_users": 5, "duration_seconds": 30},
    )
    run_id = create_res.json()["id"]
    await client.post(f"/api/v1/runs/{run_id}/start")

    shared_event_id = "race-event-shared-999"
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "event_id": shared_event_id,
        "run_id": run_id,
        "viewer_id": "viewer-race",
        "video_id": "vid-race",
        "event_type": "playback_progress",
        "watch_duration_ms": 25000,
        "timestamp": now,
    }

    # Dispatch 10 simultaneous identical requests
    tasks = [client.post("/api/v1/events/playback", json=payload) for _ in range(10)]
    responses = await asyncio.gather(*tasks)

    statuses = [r.json()["status"] for r in responses]
    accepted_count = statuses.count("accepted")
    duplicate_count = statuses.count("duplicate")

    # Exactly 1 request must be accepted, 9 flagged as duplicates
    assert accepted_count == 1
    assert duplicate_count == 9

    # Verify Redis counter integrity
    stats_res = await client.get(f"/api/v1/runs/{run_id}/stats")
    stats = stats_res.json()
    assert stats["accepted_events"] == 1
    assert stats["duplicate_events"] == 9
    assert stats["total_events"] == 10


async def test_backend_restart_persistence():
    """Verify that simulation records and reports persist across completely new client sessions."""
    run_id = None
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client1:
        create_res = await client1.post(
            "/api/v1/runs",
            json={"name": "Restart Persistence Run", "virtual_users": 10, "duration_seconds": 30},
        )
        run_id = create_res.json()["id"]
        await client1.post(f"/api/v1/runs/{run_id}/start")
        await client1.post(f"/api/v1/runs/{run_id}/stop")

    # Simulate fresh backend connection (client2)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client2:
        get_res = await client2.get(f"/api/v1/runs/{run_id}")
        assert get_res.status_code == 200
        data = get_res.json()
        assert data["id"] == run_id
        assert data["name"] == "Restart Persistence Run"
        assert data["status"] == "stopped"

        report_res = await client2.get(f"/api/v1/runs/{run_id}/report")
        assert report_res.status_code == 200
        assert report_res.json()["run_id"] == run_id
