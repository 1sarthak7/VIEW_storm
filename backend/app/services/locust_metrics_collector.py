"""Locust Performance Metrics Parser and PostgreSQL Collector."""

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import logger
from app.models.metrics import SimulationMetric
from app.repositories.simulation_repository import SimulationRepository
from app.schemas.runner import LocustPerformanceMetrics


class LocustMetricsCollector:
    """Parses actual Locust CSV output files and persists metrics to PostgreSQL."""

    def parse_locust_stats(self, artifacts_dir: Path) -> LocustPerformanceMetrics:
        """Parse Locust generated CSV files into a structured performance metrics model."""
        stats_file = artifacts_dir / "stats_stats.csv"
        history_file = artifacts_dir / "stats_stats_history.csv"

        metrics = LocustPerformanceMetrics()

        if not stats_file.exists():
            return metrics

        # 1. Parse main aggregate statistics
        try:
            with open(stats_file, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                aggregated_row = None
                for row in reader:
                    name = row.get("Name", "").strip().lower()
                    if name in ("aggregated", "total"):
                        aggregated_row = row
                        break

                if aggregated_row:
                    def _safe_float(val: Optional[str], default: float = 0.0) -> float:
                        try:
                            return float(val) if val is not None and val != "N/A" else default
                        except (ValueError, TypeError):
                            return default

                    def _safe_int(val: Optional[str], default: int = 0) -> int:
                        try:
                            return int(val) if val is not None and val != "N/A" else default
                        except (ValueError, TypeError):
                            return default

                    req_count = _safe_int(aggregated_row.get("Request Count"))
                    fail_count = _safe_int(aggregated_row.get("Failure Count"))
                    succ_count = max(0, req_count - fail_count)

                    med_resp = _safe_float(aggregated_row.get("Median Response Time"))

                    metrics.total_requests = req_count
                    metrics.failed_requests = fail_count
                    metrics.successful_requests = succ_count
                    metrics.requests_per_second = _safe_float(aggregated_row.get("Requests/s"))
                    metrics.failures_per_second = _safe_float(aggregated_row.get("Failures/s"))
                    metrics.min_latency_ms = _safe_float(aggregated_row.get("Min Response Time"))
                    metrics.avg_latency_ms = _safe_float(aggregated_row.get("Average Response Time"))
                    metrics.median_latency_ms = med_resp
                    metrics.p50_latency_ms = _safe_float(aggregated_row.get("50%"), med_resp)
                    metrics.p90_latency_ms = _safe_float(aggregated_row.get("90%"))
                    metrics.p95_latency_ms = _safe_float(aggregated_row.get("95%"))
                    metrics.p99_latency_ms = _safe_float(aggregated_row.get("99%"))
                    metrics.max_latency_ms = _safe_float(aggregated_row.get("Max Response Time"))
        except Exception as exc:
            logger.warning("Error reading Locust stats CSV from %s: %s", stats_file, exc)

        # 2. Parse active users from history CSV if available
        if history_file.exists():
            try:
                with open(history_file, mode="r", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    last_row = None
                    for row in reader:
                        last_row = row
                    if last_row and "User Count" in last_row:
                        metrics.active_users = int(last_row["User Count"])
            except Exception as exc:
                logger.debug("History CSV read note: %s", exc)

        return metrics

    async def record_metrics_snapshot(
        self,
        run_id: str,
        artifacts_dir: Path,
        db: AsyncSession,
        active_users_override: Optional[int] = None,
    ) -> Optional[SimulationMetric]:
        """Collect current metrics and persist a point in PostgreSQL simulation_metrics."""
        metrics = self.parse_locust_stats(artifacts_dir)
        now = datetime.now(timezone.utc)

        users = active_users_override if active_users_override is not None else metrics.active_users

        metric_entity = SimulationMetric(
            run_id=run_id,
            timestamp=now,
            active_users=users,
            requests_per_second=metrics.requests_per_second,
            successful_requests=metrics.successful_requests,
            failed_requests=metrics.failed_requests,
            average_latency=metrics.avg_latency_ms,
            p95_latency=metrics.p95_latency_ms,
            p99_latency=metrics.p99_latency_ms,
        )

        repo = SimulationRepository(db)
        return await repo.add_metric(metric_entity)


locust_metrics_collector = LocustMetricsCollector()
