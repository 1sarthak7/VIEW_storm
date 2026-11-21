#!/usr/bin/env python3
"""Benchmark PostgreSQL Persistence & Aggregation Service Capacity."""

import asyncio
import time
import uuid
from pathlib import Path
import sys

backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from datetime import datetime, timezone
from app.database.session import AsyncSessionLocal
from app.models.event_summary import EventSummary
from app.models.metrics import SimulationMetric
from app.models.simulation import SimulationRun
from sqlalchemy import text


async def main():
    print("=" * 70)
    print("VIEWSTORM POSTGRESQL PERSISTENCE CAPACITY BENCHMARK")
    print("=" * 70)

    async with AsyncSessionLocal() as session:
        # 1. Measure transaction roundtrip latency
        t0 = time.perf_counter()
        res = await session.execute(text("SELECT 1;"))
        ping_lat = (time.perf_counter() - t0) * 1000.0
        print(f"Database Query Latency: {ping_lat:.2f} ms")

        # 2. Measure batch insert throughput for SimulationMetric
        batch_counts = [100, 500, 1000, 2500]
        print(f"\n{'Metric Batch Size':<18} | {'Insert Time (s)':<16} | {'Inserts / Sec':<16}")
        print("-" * 55)

        run_id = f"run_pg_bench_{uuid.uuid4().hex[:8]}"
        dummy_run = SimulationRun(
            id=run_id,
            name="PG-Bench-Run",
            target_environment="local",
            virtual_users=100,
            spawn_rate=10.0,
            duration_seconds=60,
            status="completed",
        )
        session.add(dummy_run)
        await session.commit()

        for b in batch_counts:
            metrics = [
                SimulationMetric(
                    run_id=run_id,
                    timestamp=datetime.now(timezone.utc),
                    active_users=100,
                    requests_per_second=150.0,
                    successful_requests=145,
                    failed_requests=5,
                    average_latency=22.5,
                    p95_latency=45.0,
                    p99_latency=75.0,
                )
                for _ in range(b)
            ]
            t_ins = time.perf_counter()
            session.add_all(metrics)
            await session.commit()
            elapsed = time.perf_counter() - t_ins
            rate = b / elapsed if elapsed > 0 else 0.0
            print(f"{b:<18} | {elapsed:<16.3f} | {rate:<16.1f}")

        # 3. Clean up
        await session.execute(text(f"DELETE FROM simulation_runs WHERE id = '{run_id}';"))
        await session.commit()

    print("-" * 55)
    print("PostgreSQL Persistence Benchmark Completed.")


if __name__ == "__main__":
    asyncio.run(main())
