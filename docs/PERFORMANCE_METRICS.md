# Performance Metrics & Telemetry Specification

ViewStorm strictly separates client-side HTTP traffic metrics from backend playback telemetry counters:

## 1. Metric Distinctions
- **`total_http_requests`**: Total raw HTTP network requests sent by the Locust load generator.
- **`successful_http_requests`**: HTTP requests returning status 200/202 from the API.
- **`failed_http_requests`**: HTTP requests returning 4xx/5xx or experiencing socket timeouts.
- **`total_submissions`**: Raw playback events received by the backend ingestion handler.
- **`accepted_events`**: Unique playback events verified, deduplicated via Redis Lua script, and counted.
- **`duplicate_events`**: Submissions dropped due to identical `event_id` values.
- **`unique_viewers`**: Distinct synthetic viewer identifiers (`viewer_id`) active in the simulation.
- **`total_watch_duration_ms`**: Simulated watch duration accumulated across accepted events.

## 2. Latency Percentiles (Calculated by Locust)
- **Min Response Time**: Lowest latency recorded during test run.
- **Average Response Time**: Mean request duration in milliseconds.
- **Median (P50)**: 50th percentile of response latency.
- **P90**: 90% of requests responded within this threshold.
- **P95**: 95% of requests responded within this threshold.
- **P99**: 99th percentile latency measurement.
- **Max Response Time**: Peak latency outlier.

## 3. System Resource Utilization
Captured at runtime via `psutil`:
- `cpu_percent`: Instantaneous backend CPU utilization.
- `ram_percent`: System memory consumption percentage.
- `disk_usage_percent`: Local storage capacity utilization.
