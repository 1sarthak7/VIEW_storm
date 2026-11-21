"""Synthetic Playback Event Ingestion Endpoints."""

from fastapi import APIRouter, status
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
def ingest_playback_event(event: PlaybackEventCreate) -> PlaybackEventResponse:
    """
    Accept synthetic playback event from virtual viewer load generator.
    Validates payload, enforces run status, and ensures idempotency.
    """
    return event_service.ingest_event(event)


@router.post(
    "/events/playback/batch",
    response_model=PlaybackEventBatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Playback Events"],
)
def ingest_playback_events_batch(batch: PlaybackEventBatchCreate) -> PlaybackEventBatchResponse:
    """
    Accept high-rate batch of synthetic playback events.
    Optimized for distributed worker throughput.
    """
    return event_service.ingest_batch(batch)
