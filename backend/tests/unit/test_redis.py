"""Unit Tests for Redis Connection, Key Scoping, Atomic Deduplication and Operations."""

from datetime import datetime, timezone
import pytest
from redis.asyncio import Redis
from app.database.redis import (
    INGEST_EVENT_LUA,
    check_redis_health,
    redis_client,
    run_event_types_key,
    run_events_key,
    run_stats_key,
    run_timestamps_key,
    run_viewers_key,
)

pytestmark = pytest.mark.asyncio


async def test_redis_connection_establishment():
    """Verify live Redis ping succeeds."""
    is_healthy = await check_redis_health()
    assert is_healthy is True


async def test_key_naming_convention_and_isolation():
    """Verify key names are properly scoped per simulation run."""
    run_1 = "run-001"
    run_2 = "run-002"

    assert run_stats_key(run_1) == "viewstorm:run:run-001:stats"
    assert run_events_key(run_1) == "viewstorm:run:run-001:processed_events"
    assert run_viewers_key(run_1) == "viewstorm:run:run-001:viewers"
    assert run_event_types_key(run_1) == "viewstorm:run:run-001:event_types"
    assert run_timestamps_key(run_1) == "viewstorm:run:run-001:recent_timestamps"

    assert run_stats_key(run_1) != run_stats_key(run_2)


async def test_redis_lua_atomic_event_ingestion_and_deduplication():
    """Verify atomic Lua script accepts unique events and flags duplicates."""
    run_id = "test-atomic-run"
    keys = [
        run_events_key(run_id),
        run_stats_key(run_id),
        run_event_types_key(run_id),
        run_viewers_key(run_id),
        run_timestamps_key(run_id),
    ]

    # Clean keys for this test
    await redis_client.delete(*keys)

    epoch = datetime.now(timezone.utc).timestamp()
    args_event_1 = ["evt-lua-1", "playback_start", "viewer-A", 15000, epoch, 3600]

    # First execution -> Accepted (1)
    res1 = await redis_client.eval(INGEST_EVENT_LUA, len(keys), *keys, *args_event_1)
    assert res1 == 1

    # Verify counters
    stats = await redis_client.hgetall(run_stats_key(run_id))
    assert int(stats["total_submissions"]) == 1
    assert int(stats["accepted_events"]) == 1
    assert int(stats["total_watch_duration_ms"]) == 15000

    # Verify unique viewers
    viewers_count = await redis_client.scard(run_viewers_key(run_id))
    assert viewers_count == 1
    is_member = await redis_client.sismember(run_viewers_key(run_id), "viewer-A")
    assert is_member == 1

    # Second execution (Identical Event ID) -> Duplicate (0)
    res2 = await redis_client.eval(INGEST_EVENT_LUA, len(keys), *keys, *args_event_1)
    assert res2 == 0

    # Verify duplicate counter updated, accepted counter untouched
    updated_stats = await redis_client.hgetall(run_stats_key(run_id))
    assert int(updated_stats["total_submissions"]) == 2
    assert int(updated_stats["accepted_events"]) == 1
    assert int(updated_stats["duplicate_events"]) == 1
    assert int(updated_stats["total_watch_duration_ms"]) == 15000


async def test_redis_run_key_isolation():
    """Verify counters in one run do not mutate counters in another run."""
    run_a = "run-iso-A"
    run_b = "run-iso-B"

    keys_a = [
        run_events_key(run_a),
        run_stats_key(run_a),
        run_event_types_key(run_a),
        run_viewers_key(run_a),
        run_timestamps_key(run_a),
    ]
    keys_b = [
        run_events_key(run_b),
        run_stats_key(run_b),
        run_event_types_key(run_b),
        run_viewers_key(run_b),
        run_timestamps_key(run_b),
    ]

    await redis_client.delete(*(keys_a + keys_b))

    epoch = datetime.now(timezone.utc).timestamp()
    await redis_client.eval(INGEST_EVENT_LUA, len(keys_a), *keys_a, "evt-1", "playback_start", "v-1", 5000, epoch, 3600)

    stats_a = await redis_client.hgetall(run_stats_key(run_a))
    stats_b = await redis_client.hgetall(run_stats_key(run_b))

    assert int(stats_a.get("accepted_events", 0)) == 1
    assert int(stats_b.get("accepted_events", 0)) == 0


async def test_redis_unavailable_handling(mocker):
    """Verify health check gracefully handles Redis connection failures."""
    mocker.patch.object(redis_client, "ping", side_effect=Exception("Redis Connection Refused"))
    is_healthy = await check_redis_health()
    assert is_healthy is False
