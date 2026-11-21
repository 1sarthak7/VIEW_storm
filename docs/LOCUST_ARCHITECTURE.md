# Locust Simulation Engine Architecture

## 1. Overview
ViewStorm Milestone 3 integrates Locust as an external, headless load-testing subprocess managed directly by the FastAPI backend. It avoids running gevent inside the asyncio event loop by isolating the runner in a separate process.

```
+-------------------------------------------------------------------------------+
| FastAPI Backend                                                               |
|                                                                               |
|  POST /api/v1/runs/{id}/start                                                 |
|               |                                                               |
|               v                                                               |
|  +--------------------------------+                                           |
|  | LocustRunnerService            |                                           |
|  | - Pre-launch validation        |                                           |
|  | - Target URL allowlist check   |                                           |
|  | - Process creation via         |                                           |
|  |   asyncio.create_subprocess    |                                           |
|  +--------------------------------+                                           |
+---------------|---------------------------------------------------------------+
                |
                | Spawns independent subprocess
                v
+-------------------------------------------------------------------------------+
| Locust Subprocess (simulator/locustfile.py)                                   |
|                                                                               |
|   VirtualViewer (HttpUser)                                                    |
|     - Unique viewer_id (UUID)                                                 |
|     - Unique video_id                                                         |
|     - Lifecycle tasks:                                                        |
|         * on_start: playback_start                                            |
|         * @task(3): playback_progress                                         |
|         * @task(1): playback_complete                                         |
|         * on_stop:  playback_exit                                             |
|                                                                               |
|   HTTP POST /api/v1/events/playback (Target Host)                             |
|                                                                               |
|   Outputs:                                                                    |
|     artifacts/runs/{run_id}/stats_stats.csv                                   |
|     artifacts/runs/{run_id}/stats_stats_history.csv                           |
|     artifacts/runs/{run_id}/runner.log                                        |
+-------------------------------------------------------------------------------+
                |
                | Output files monitored periodically (every 2s)
                v
+-------------------------------------------------------------------------------+
| LocustMetricsCollector                                                        |
| - Parses CSV latency percentiles (Min, Avg, P50, P90, P95, P99, Max)          |
| - Extracts real requests/sec, failure counts, and active users                |
| - Persists snapshots into PostgreSQL `simulation_metrics`                     |
| - On termination: syncs final aggregates to `event_summaries`                 |
+-------------------------------------------------------------------------------+
```

## 2. VirtualViewer Design
Each virtual user is an instance of `VirtualViewer(HttpUser)` with configurable wait intervals:
- Each user maintains an internal watch timer.
- Submits telemetry to `/api/v1/events/playback` using standard JSON payloads matching `PlaybackEventCreate`.
- Captures and records HTTP errors directly into Locust's failure statistics without crashing the worker.
