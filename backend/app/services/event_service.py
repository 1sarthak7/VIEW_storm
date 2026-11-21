"""High-Throughput Synthetic Event Ingestion Service with Idempotency."""

import threading
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Dict, List, Set, Tuple
from app.core.errors import SimulationNotActiveError, SimulationNotFoundError
from app.schemas.event import (
    PlaybackEventBatchCreate,
    PlaybackEventBatchResponse,
    PlaybackEventCreate,
    PlaybackEventResponse,
)
from app.schemas.run import SimulationStatus
from app.services.simulation_service import simulation_service


class RunEventAggregator:
    """Thread-safe statistics collector for a single simulation run."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.lock = threading.Lock()
        self.total_submissions: int = 0
        self.accepted_events: int = 0
        self.duplicate_events: int = 0
        self.rejected_events: int = 0
        self.unique_viewers: Set[str] = set()
        self.events_by_type: Dict[str, int] = defaultdict(int)
        self.total_watch_duration_ms: int = 0
        # Rolling recent event timestamps for RPS calculation
        self.recent_timestamps: deque = deque(maxlen=2000)
        # Deduplication cache per run: set of event_id strings
        self.seen_event_ids: Set[str] = set()


class EventService:
    """Processes synthetic playback events, performs idempotency checks, and updates counters."""

    def __init__(self) -> None:
        self._aggregators: Dict[str, RunEventAggregator] = {}
        self._global_lock = threading.Lock()

    def _get_or_create_aggregator(self, run_id: str) -> RunEventAggregator:
        with self._global_lock:
            if run_id not in self._aggregators:
                self._aggregators[run_id] = RunEventAggregator(run_id)
            return self._aggregators[run_id]

    def ingest_event(self, event: PlaybackEventCreate) -> PlaybackEventResponse:
        """Validate, deduplicate, and record a single synthetic playback event."""
        # 1. Verify simulation exists and check status
        run = simulation_service.get_run(event.run_id)
        aggregator = self._get_or_create_aggregator(event.run_id)
        now = datetime.now(timezone.utc)

        with aggregator.lock:
            aggregator.total_submissions += 1

            if run.status != SimulationStatus.RUNNING:
                aggregator.rejected_events += 1
                raise SimulationNotActiveError(run_id=event.run_id, current_status=run.status.value)

            # 2. Idempotency Check
            if event.event_id in aggregator.seen_event_ids:
                aggregator.duplicate_events += 1
                return PlaybackEventResponse(
                    status="duplicate",
                    event_id=event.event_id,
                    run_id=event.run_id,
                    received_at=now,
                    message="Duplicate event ignored (idempotent submission)",
                )

            # 3. Accept and aggregate unique synthetic event
            aggregator.seen_event_ids.add(event.event_id)
            aggregator.accepted_events += 1
            aggregator.unique_viewers.add(event.viewer_id)
            aggregator.events_by_type[event.event_type.value] += 1
            aggregator.total_watch_duration_ms += event.watch_duration_ms
            aggregator.recent_timestamps.append(now.timestamp())

        return PlaybackEventResponse(
            status="accepted",
            event_id=event.event_id,
            run_id=event.run_id,
            received_at=now,
            message="Synthetic event accepted",
        )

    def ingest_batch(self, batch: PlaybackEventBatchCreate) -> PlaybackEventBatchResponse:
        """Batch ingestion optimization for high-rate synthetic workers."""
        accepted = 0
        duplicates = 0
        rejected = 0

        for event in batch.events:
            try:
                res = self.ingest_event(event)
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

    def get_aggregator(self, run_id: str) -> RunEventAggregator:
        """Retrieve event statistics collector for a given simulation run."""
        return self._get_or_create_aggregator(run_id)


event_service = EventService()
