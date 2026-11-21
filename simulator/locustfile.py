"""Locust Load Test Script: VirtualViewer Synthetic Traffic Generator."""

import random
import uuid
import sys
from pathlib import Path

# Add simulator folder to sys.path so helper modules resolve correctly
simulator_dir = Path(__file__).resolve().parent
if str(simulator_dir) not in sys.path:
    sys.path.insert(0, str(simulator_dir))

from configuration import config
from events import generate_playback_event
from locust import HttpUser, between, task


class VirtualViewer(HttpUser):
    """
    Represents an independent synthetic video playback user session.
    Generates realistic playback telemetry events targeting the ViewStorm ingestion API.
    """

    wait_time = between(0.5, 2.0)

    def on_start(self) -> None:
        """Initialize viewer session, assign unique synthetic IDs, and post playback_start."""
        self.viewer_id = f"vwr-{uuid.uuid4().hex[:12]}"
        self.video_id = f"vid-{random.randint(1, 100):04d}"
        self.current_watch_ms = 0
        self.run_id = config.run_id

        # Fire initial playback_start event
        start_payload = generate_playback_event(
            run_id=self.run_id,
            viewer_id=self.viewer_id,
            video_id=self.video_id,
            event_type="playback_start",
            watch_duration_ms=0,
        )
        self._post_event(start_payload, name="/api/v1/events/playback [start]")

    @task(3)
    def progress_playback(self) -> None:
        """Simulate ongoing playback progress with incremental watch duration."""
        step_min = config.watch_duration_min * 1000
        step_max = max(step_min, (config.watch_duration_max * 1000) // 2)
        increment = random.randint(step_min, step_max)
        self.current_watch_ms += increment

        payload = generate_playback_event(
            run_id=self.run_id,
            viewer_id=self.viewer_id,
            video_id=self.video_id,
            event_type="playback_progress",
            watch_duration_ms=self.current_watch_ms,
        )
        self._post_event(payload, name="/api/v1/events/playback [progress]")

    @task(1)
    def complete_playback(self) -> None:
        """Simulate playback completion event."""
        self.current_watch_ms += random.randint(1000, 5000)
        payload = generate_playback_event(
            run_id=self.run_id,
            viewer_id=self.viewer_id,
            video_id=self.video_id,
            event_type="playback_complete",
            watch_duration_ms=self.current_watch_ms,
        )
        self._post_event(payload, name="/api/v1/events/playback [complete]")

    def on_stop(self) -> None:
        """Simulate viewer exit event when session terminates."""
        payload = generate_playback_event(
            run_id=self.run_id,
            viewer_id=self.viewer_id,
            video_id=self.video_id,
            event_type="playback_exit",
            watch_duration_ms=self.current_watch_ms,
        )
        self._post_event(payload, name="/api/v1/events/playback [exit]")

    def _post_event(self, payload: dict, name: str) -> None:
        """Send synthetic event to ViewStorm API with error trapping."""
        headers = {"Content-Type": "application/json"}
        with self.client.post(
            "/api/v1/events/playback",
            json=payload,
            headers=headers,
            name=name,
            catch_response=True,
        ) as response:
            if response.status_code in (200, 202):
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}: {response.text}")
