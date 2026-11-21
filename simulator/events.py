"""Synthetic Playback Event Factory for Virtual Viewers."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid


def generate_playback_event(
    run_id: str,
    viewer_id: str,
    video_id: str,
    event_type: str,
    watch_duration_ms: int = 0,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate synthetic playback event compatible with PlaybackEventCreate schema.
    Guarantees unique event_id per submission.
    """
    return {
        "event_id": f"evt-{uuid.uuid4().hex}",
        "run_id": run_id,
        "viewer_id": viewer_id,
        "video_id": video_id,
        "event_type": event_type,
        "watch_duration_ms": max(0, watch_duration_ms),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {"client": "locust_virtual_viewer", "os": "darwin"},
    }
