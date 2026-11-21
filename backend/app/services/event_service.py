"""High-Throughput Synthetic Event Ingestion Service with Redis Atomic Lua Scripts."""

from datetime import datetime, timezone
from typing import Optional
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.errors import SimulationNotActiveError
from app.database.redis import (
    INGEST_EVENT_LUA,
    redis_client,
    run_event_types_key,
    run_events_key,
    run_stats_key,
    run_timestamps_key,
    run_viewers_key,
)
from app.schemas.event import (
    PlaybackEventBatchCreate,
    PlaybackEventBatchResponse,
    PlaybackEventCreate,
    PlaybackEventResponse,
)
from app.schemas.run import SimulationStatus
from app.services.simulation_service import simulation_service


class EventService:
    """Processes synthetic playback events atomically using Redis."""

    def __init__(self) -> None:
        self._lua_script_sha: Optional[str] = None

    async def _ensure_lua_script(self, r: Redis) -> str:
        """Load and cache the atomic ingestion Lua script SHA."""
        if not self._lua_script_sha:
            self._lua_script_sha = await r.script_load(INGEST_EVENT_LUA)
        return self._lua_script_sha

    async def ingest_event(
        self,
        event: PlaybackEventCreate,
        redis: Optional[Redis] = None,
        db: Optional[AsyncSession] = None,
    ) -> PlaybackEventResponse:
        """
        Atomically validate, deduplicate, and record a single synthetic playback event in Redis.
        """
        r = redis or redis_client
        now = datetime.now(timezone.utc)

        # 1. Verify simulation exists and is actively running
        run = await simulation_service.get_run(event.run_id, db=db)
        if run.status != SimulationStatus.RUNNING:
            # Increment rejected counter in Redis
            stats_key = run_stats_key(event.run_id)
            await r.hincrby(stats_key, "total_submissions", 1)
            await r.hincrby(stats_key, "rejected_events", 1)
            raise SimulationNotActiveError(run_id=event.run_id, current_status=run.status.value)

        # 2. Execute Atomic Redis Lua Script for Deduplication and Increments
        keys = [
            run_events_key(event.run_id),
            run_stats_key(event.run_id),
            run_event_types_key(event.run_id),
            run_viewers_key(event.run_id),
            run_timestamps_key(event.run_id),
        ]
        args = [
            event.event_id,
            event.event_type.value,
            event.viewer_id,
            event.watch_duration_ms,
            event.timestamp.timestamp(),
            settings.stats_retention_ttl_seconds,
        ]

        try:
            sha = await self._ensure_lua_script(r)
            result = await r.evalsha(sha, len(keys), *keys, *args)
        except Exception:
            # Fallback to direct eval if script SHA expired or flush occurred
            result = await r.eval(INGEST_EVENT_LUA, len(keys), *keys, *args)

        # Lua returns 1 for accepted, 0 for duplicate
        if result == 1:
            return PlaybackEventResponse(
                status="accepted",
                event_id=event.event_id,
                run_id=event.run_id,
                received_at=now,
                message="Synthetic event accepted",
            )
        else:
            return PlaybackEventResponse(
                status="duplicate",
                event_id=event.event_id,
                run_id=event.run_id,
                received_at=now,
                message="Duplicate event ignored (idempotent submission)",
            )

    async def ingest_batch(
        self,
        batch: PlaybackEventBatchCreate,
        redis: Optional[Redis] = None,
        db: Optional[AsyncSession] = None,
    ) -> PlaybackEventBatchResponse:
        """Batch ingestion for high-rate synthetic workers."""
        accepted = 0
        duplicates = 0
        rejected = 0

        for event in batch.events:
            try:
                res = await self.ingest_event(event, redis=redis, db=db)
                if res.status == "accepted":
                    accepted += 1
                elif res.status == "duplicate":
                    duplicates += 1
            except SimulationNotActiveError:
                rejected += 1

        return PlaybackEventBatchResponse(
            total=len(batch.events),
            accepted=accepted,
            duplicates=duplicates,
            rejected=rejected,
        )


event_service = EventService()
