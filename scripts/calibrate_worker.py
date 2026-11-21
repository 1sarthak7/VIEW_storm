#!/usr/bin/env python3
"""Standalone CLI for Worker Load Generator Capacity Calibration."""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.database.session import AsyncSessionLocal
from app.schemas.worker_calibration import WorkerCalibrationRequest
from app.services.worker_calibration_service import worker_calibration_service


async def main():
    parser = argparse.ArgumentParser(description="Calibrate ViewStorm load generator worker capacity.")
    parser.add_argument("--worker-id", type=str, default=None, help="Worker node ID to calibrate (default: local host)")
    parser.add_argument("--steps", nargs="+", type=int, default=[10, 25, 50, 100, 250, 500], help="User counts to test")
    parser.add_argument("--duration", type=int, default=10, help="Duration in seconds per step")
    parser.add_argument("--max-cpu", type=float, default=85.0, help="CPU saturation limit (percent)")
    parser.add_argument("--output", type=str, default=None, help="Path to save JSON calibration results")
    args = parser.parse_args()

    print("=" * 70)
    print("VIEWSTORM WORKER CAPACITY CALIBRATION")
    print(f"Steps: {args.steps} users | Step duration: {args.duration}s | Saturation CPU: {args.max_cpu}%")
    print("=" * 70)

    req = WorkerCalibrationRequest(
        steps=args.steps,
        step_duration_seconds=args.duration,
        max_cpu_pct_threshold=args.max_cpu,
        notes="CLI stepped worker capacity calibration",
    )

    async with AsyncSessionLocal() as session:
        result = await worker_calibration_service.calibrate_worker(
            worker_node_id=args.worker_id,
            request=req,
            db=session,
        )

    print("\nCALIBRATION OUTCOME:")
    print(f"  Worker Identifier:        {result.worker_identifier}")
    print(f"  CPU Cores:                {result.cpu_cores}")
    print(f"  Total RAM:                {result.total_memory_mb:.1f} MB")
    print(f"  Max Stable Users:         {result.max_stable_users} users")
    print(f"  Max Stable RPS:           {result.max_stable_rps:.1f} RPS")
    print(f"  Recommended Capacity:     {result.recommended_capacity} users")
    print(f"  Saturation Bottleneck:    {result.saturation_bottleneck or 'None detected'}")
    print("=" * 70)

    if args.output:
        Path(args.output).write_text(json.dumps(result.model_dump(), indent=2, default=str))
        print(f"Results written to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
