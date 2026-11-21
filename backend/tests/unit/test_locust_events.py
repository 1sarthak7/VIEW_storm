"""Unit Tests for Synthetic Playback Event Generation for Virtual Viewers."""

import sys
from pathlib import Path

# Ensure simulator is in sys.path
simulator_path = Path(__file__).resolve().parent.parent.parent.parent / "simulator"
if str(simulator_path) not in sys.path:
    sys.path.insert(0, str(simulator_path))

from events import generate_playback_event


def test_generate_playback_event_structure():
    """Verify generated event payload matches required PlaybackEventCreate schema."""
    event = generate_playback_event(
        run_id="run-test-100",
        viewer_id="viewer-test-01",
        video_id="video-test-01",
        event_type="playback_start",
        watch_duration_ms=5000,
    )

    assert event["run_id"] == "run-test-100"
    assert event["viewer_id"] == "viewer-test-01"
    assert event["video_id"] == "video-test-01"
    assert event["event_type"] == "playback_start"
    assert event["watch_duration_ms"] == 5000
    assert event["event_id"].startswith("evt-")
    assert "timestamp" in event
    assert "metadata" in event


def test_generate_playback_event_uniqueness():
    """Verify each invocation generates a globally unique event_id."""
    events = [
        generate_playback_event(
            run_id="run-test-100",
            viewer_id="viewer-test-01",
            video_id="video-test-01",
            event_type="playback_progress",
        )
        for _ in range(50)
    ]

    event_ids = [e["event_id"] for e in events]
    assert len(event_ids) == len(set(event_ids))
