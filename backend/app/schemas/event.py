"""Playback Event Schemas for Synthetic Viewer Load Generation."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class PlaybackEventType(str, Enum):
    """Supported playback event types."""
    PLAYBACK_START = "playback_start"
    PLAYBACK_PROGRESS = "playback_progress"
    PLAYBACK_COMPLETE = "playback_complete"
    PLAYBACK_EXIT = "playback_exit"


class PlaybackEventCreate(BaseModel):
    """Synthetic playback event ingestion payload."""
    event_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Unique synthetic event identifier"
    )
    run_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Associated simulation run identifier"
    )
    viewer_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Unique synthetic viewer identifier"
    )
    video_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Synthetic video identifier"
    )
    event_type: PlaybackEventType = Field(
        ...,
        description="Playback lifecycle event type"
    )
    watch_duration_ms: int = Field(
        default=0,
        ge=0,
        le=86400000,
        description="Watch duration in milliseconds (max 24 hours)"
    )
    timestamp: datetime = Field(
        ...,
        description="ISO-8601 timestamp of the synthetic event"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional synthetic client metadata"
    )

    @field_validator("event_id", "run_id", "viewer_id", "video_id")
    @classmethod
    def validate_non_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Field cannot be empty or whitespace only")
        return stripped


class PlaybackEventResponse(BaseModel):
    """Response returned upon processing a playback event."""
    status: str = Field(..., description="'accepted' | 'duplicate' | 'rejected'")
    event_id: str
    run_id: str
    received_at: datetime
    message: Optional[str] = None


class PlaybackEventBatchCreate(BaseModel):
    """Batch ingestion payload for high-throughput load generators."""
    events: List[PlaybackEventCreate] = Field(..., min_length=1, max_length=1000)


class PlaybackEventBatchResponse(BaseModel):
    """Batch ingestion outcome summary."""
    total: int
    accepted: int
    duplicates: int
    rejected: int
