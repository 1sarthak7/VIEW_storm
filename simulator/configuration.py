"""Locust Simulation Configuration Parser."""

import os
from dataclasses import dataclass


@dataclass
class SimulationConfig:
    """Extracts simulation parameters passed via environment variables."""
    run_id: str
    target_host: str
    event_type: str
    watch_duration_min: int
    watch_duration_max: int

    @classmethod
    def from_env(cls) -> "SimulationConfig":
        return cls(
            run_id=os.getenv("VIEWSTORM_RUN_ID", "default-run"),
            target_host=os.getenv("VIEWSTORM_TARGET_HOST", "http://127.0.0.1:8000"),
            event_type=os.getenv("VIEWSTORM_EVENT_TYPE", "playback_start"),
            watch_duration_min=int(os.getenv("VIEWSTORM_WATCH_MIN", "5")),
            watch_duration_max=int(os.getenv("VIEWSTORM_WATCH_MAX", "60")),
        )


config = SimulationConfig.from_env()
