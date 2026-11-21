"""Prometheus Metrics Definitions and Exposition Registry."""

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

# HTTP Request metrics
HTTP_REQUESTS_TOTAL = Counter(
    "viewstorm_http_requests_total",
    "Total HTTP requests handled by ViewStorm API",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "viewstorm_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0),
)

# Domain & Simulation metrics
EVENTS_INGESTED_TOTAL = Counter(
    "viewstorm_events_ingested_total",
    "Total synthetic playback events ingested",
    ["event_type", "status"],
)

ACTIVE_SIMULATIONS_GAUGE = Gauge(
    "viewstorm_active_simulations",
    "Number of currently active simulation runs",
)

ACTIVE_WORKERS_GAUGE = Gauge(
    "viewstorm_active_worker_nodes",
    "Number of active load generator worker nodes",
)

EMERGENCY_STOP_GAUGE = Gauge(
    "viewstorm_emergency_stop_active",
    "Global emergency stop state (1 = active/engaged, 0 = normal)",
)


def get_metrics_payload() -> bytes:
    """Export all registered Prometheus metrics in Prometheus text format."""
    return generate_latest()


__all__ = [
    "CONTENT_TYPE_LATEST",
    "HTTP_REQUESTS_TOTAL",
    "HTTP_REQUEST_DURATION_SECONDS",
    "EVENTS_INGESTED_TOTAL",
    "ACTIVE_SIMULATIONS_GAUGE",
    "ACTIVE_WORKERS_GAUGE",
    "EMERGENCY_STOP_GAUGE",
    "get_metrics_payload",
]
