"""Synthetic Playback Event Ingestion Endpoints with Redis Atomic Execution."""

from fastapi import APIRouter, Depends, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.redis import get_redis
from app.database.session import get_db
from app.schemas.event import (
    PlaybackEventBatchCreate,
    PlaybackEventBatchResponse,
    PlaybackEventCreate,
    PlaybackEventResponse,
)
from app.services.event_service import event_service

router = APIRouter()


@router.post(
    "/events/playback",
    response_model=PlaybackEventResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Playback Events"],
)
async def ingest_playback_event(
    event: PlaybackEventCreate,
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
) -> PlaybackEventResponse:
    """
    Accept synthetic playback event from virtual viewer load generator.
    Enforces active run status, atomic deduplication, and high-speed Redis counting.
    """
    return await event_service.ingest_event(event, redis=redis, db=db)


@router.post(
    "/events/playback/batch",
    response_model=PlaybackEventBatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Playback Events"],
)
async def ingest_playback_events_batch(
    batch: PlaybackEventBatchCreate,
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
) -> PlaybackEventBatchResponse:
    """
    High-rate batch event ingestion for distributed load generator workers.
    """
    return await event_service.ingest_batch(batch, redis=redis, db=db)
