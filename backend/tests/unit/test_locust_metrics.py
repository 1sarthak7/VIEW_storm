"""Unit Tests for Locust CSV Statistics Parsing and Metrics Collection."""

from pathlib import Path
import pytest
from app.database.session import AsyncSessionLocal
from app.repositories.simulation_repository import SimulationRepository
from app.schemas.run import SimulationRunCreate
from app.schemas.runner import LocustPerformanceMetrics
from app.services.locust_metrics_collector import LocustMetricsCollector

pytestmark = pytest.mark.asyncio


async def test_parse_missing_csv(tmp_path: Path):
    """Verify graceful handling when CSV stats files do not exist."""
    collector = LocustMetricsCollector()
    metrics = collector.parse_locust_stats(tmp_path)
    assert isinstance(metrics, LocustPerformanceMetrics)
    assert metrics.total_requests == 0
    assert metrics.requests_per_second == 0.0


async def test_parse_valid_locust_stats_csv(tmp_path: Path):
    """Verify correct extraction of latency percentiles, throughput, and error counts."""
    stats_file = tmp_path / "stats_stats.csv"
    history_file = tmp_path / "stats_stats_history.csv"

    stats_content = (
        '"Type","Name","Request Count","Failure Count","Median Response Time","Average Response Time","Min Response Time","Max Response Time","Average Content Size","Requests/s","Failures/s","50%","66%","75%","80%","90%","95%","98%","99%","99.9%","99.99%","100%"\n'
        '"POST","/api/v1/events/playback",100,5,15.0,18.5,8.0,120.0,250,20.0,1.0,15.0,16.0,18.0,20.0,25.0,35.0,45.0,60.0,90.0,110.0,120.0\n'
        '"","Aggregated",100,5,15.0,18.5,8.0,120.0,250,20.0,1.0,15.0,16.0,18.0,20.0,25.0,35.0,45.0,60.0,90.0,110.0,120.0\n'
    )
    stats_file.write_text(stats_content, encoding="utf-8")

    history_content = (
        '"Timestamp","User Count","Type","Name","Requests/s","Failures/s","50%","66%","75%","80%","90%","95%","98%","99%","99.9%","99.99%","100%","Total Request Count","Total Failure Count","Total Median Response Time","Total Average Response Time","Total Min Response Time","Total Max Response Time","Total Average Content Size"\n'
        '"1710000000",25,"POST","/api/v1/events/playback",20.0,1.0,15.0,16.0,18.0,20.0,25.0,35.0,45.0,60.0,90.0,110.0,120.0,100,5,15.0,18.5,8.0,120.0,250\n'
    )
    history_file.write_text(history_content, encoding="utf-8")

    collector = LocustMetricsCollector()
    metrics = collector.parse_locust_stats(tmp_path)

    assert metrics.total_requests == 100
    assert metrics.failed_requests == 5
    assert metrics.successful_requests == 95
    assert metrics.requests_per_second == 20.0
    assert metrics.failures_per_second == 1.0
    assert metrics.min_latency_ms == 8.0
    assert metrics.avg_latency_ms == 18.5
    assert metrics.p50_latency_ms == 15.0
    assert metrics.p95_latency_ms == 35.0
    assert metrics.p99_latency_ms == 60.0
    assert metrics.max_latency_ms == 120.0
    assert metrics.active_users == 25


async def test_record_metrics_snapshot_persistence(tmp_path: Path):
    """Verify snapshot metrics are stored in PostgreSQL simulation_metrics table."""
    stats_file = tmp_path / "stats_stats.csv"
    stats_content = (
        '"Type","Name","Request Count","Failure Count","Median Response Time","Average Response Time","Min Response Time","Max Response Time","Average Content Size","Requests/s","Failures/s","50%","66%","75%","80%","90%","95%","98%","99%","99.9%","99.99%","100%"\n'
        '"","Aggregated",50,0,10.0,12.0,5.0,35.0,200,10.0,0.0,10.0,11.0,12.0,13.0,15.0,20.0,25.0,30.0,35.0,35.0,35.0\n'
    )
    stats_file.write_text(stats_content, encoding="utf-8")

    run_id = "run-metrics-db-test"
    async with AsyncSessionLocal() as session:
        repo = SimulationRepository(session)
        payload = SimulationRunCreate(name="Metrics Collector Run", target_environment="local")
        await repo.create(run_id, payload)

        collector = LocustMetricsCollector()
        metric_entity = await collector.record_metrics_snapshot(
            run_id=run_id,
            artifacts_dir=tmp_path,
            db=session,
            active_users_override=10,
        )

        assert metric_entity is not None
        assert metric_entity.successful_requests == 50
        assert metric_entity.requests_per_second == 10.0
        assert metric_entity.average_latency == 12.0

        persisted = await repo.list_metrics(run_id)
        assert len(persisted) == 1
        assert persisted[0].requests_per_second == 10.0
