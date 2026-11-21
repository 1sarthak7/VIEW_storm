#!/usr/bin/env python3
"""Benchmark ViewStorm Playback Event Ingestion API Capacity."""

import asyncio
import time
import uuid
from typing import List
import httpx


async def run_worker(client: httpx.AsyncClient, run_id: str, count: int) -> List[float]:
    latencies = []
    url = f"http://localhost:8000/api/v1/events"
    for i in range(count):
        payload = {
            "run_id": run_id,
            "session_id": f"sess_{uuid.uuid4().hex[:12]}",
            "synthetic_viewer_id": f"viewer_{i % 500:04d}",
            "event_type": "playback_heartbeat",
            "playback_time_ms": (i + 1) * 5000,
            "total_watch_duration_ms": (i + 1) * 5000,
            "timestamp": time.time(),
        }
        t0 = time.perf_counter()
        try:
            res = await client.post(url, json=payload, timeout=5.0)
            if res.status_code == 202:
                latencies.append((time.perf_counter() - t0) * 1000.0)
        except Exception:
            pass
    return latencies


async def main():
    print("=" * 70)
    print("VIEWSTORM BACKEND INGESTION CAPACITY BENCHMARK")
    print("=" * 70)

    # First create an active run
    async with httpx.AsyncClient() as client:
        # Check health
        health = await client.get("http://localhost:8000/health")
        if health.status_code != 200:
            print("Backend not healthy or offline. Start with 'uvicorn app.main:app'.")
            return

        run_res = await client.post(
            "http://localhost:8000/api/v1/runs",
            json={
                "name": "Backend-Capacity-Benchmark-Run",
                "target_environment": "local",
                "virtual_users": 100,
                "spawn_rate": 10.0,
                "duration_seconds": 120,
            },
        )
        if run_res.status_code != 201:
            print(f"Failed to create test run: {run_res.text}")
            return
        run_data = run_res.json()
        run_id = run_data["id"]

        # Transition run to running
        start_res = await client.post(f"http://localhost:8000/api/v1/runs/{run_id}/start")
        print(f"Active run initialized: {run_id}")

        concurrencies = [10, 25, 50, 100]
        requests_per_conn = 100

        print(f"\n{'Concurrency':<14} | {'Total Reqs':<12} | {'Throughput (RPS)':<18} | {'p50 (ms)':<10} | {'p95 (ms)':<10} | {'p99 (ms)':<10}")
        print("-" * 80)

        for c in concurrencies:
            t_start = time.perf_counter()
            tasks = [run_worker(client, run_id, requests_per_conn) for _ in range(c)]
            results = await asyncio.gather(*tasks)
            elapsed = time.perf_counter() - t_start

            all_lat = [lat for worker_lats in results for lat in worker_lats]
            all_lat.sort()

            total = len(all_lat)
            rps = total / elapsed if elapsed > 0 else 0.0
            p50 = all_lat[int(len(all_lat) * 0.50)] if all_lat else 0.0
            p95 = all_lat[int(len(all_lat) * 0.95)] if all_lat else 0.0
            p99 = all_lat[int(len(all_lat) * 0.99)] if all_lat else 0.0

            print(f"{c:<14} | {total:<12} | {rps:<18.1f} | {p50:<10.1f} | {p95:<10.1f} | {p99:<10.1f}")

        # Stop run
        await client.post(f"http://localhost:8000/api/v1/runs/{run_id}/stop")
        print("-" * 80)
        print("Backend Ingestion Benchmark Completed.")


if __name__ == "__main__":
    asyncio.run(main())
