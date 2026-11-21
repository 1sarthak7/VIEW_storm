# ViewStorm Load Testing Simulator

This directory contains the headless Locust test suite and VirtualViewer synthetic viewer traffic generator.

## Components
- `locustfile.py`: Main Locust HttpUser task definition (`VirtualViewer`).
- `events.py`: Synthetic playback event generation factory ensuring unique event IDs.
- `configuration.py`: Environment variable configuration reader (`VIEWSTORM_RUN_ID`, `VIEWSTORM_TARGET_HOST`, etc.).

## Manual Execution (Testing Only)
Although ViewStorm's backend manages Locust automatically via `POST /api/v1/runs/{run_id}/start`, you can run standalone tests directly:

```bash
locust -f simulator/locustfile.py --headless -u 10 -r 2 -t 30s --host http://127.0.0.1:8000
```
