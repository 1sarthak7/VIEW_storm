#!/usr/bin/env python3
"""ViewStorm Staged End-to-End Progressive Benchmark Runner.

Executes progressive capacity validation stages with automated preflight checks,
SLA guardrail monitoring, duration semantics recording, and artifact verification.
"""

import argparse
import asyncio
import sys
import time
from typing import List, Optional
import httpx


async def run_single_stage(
    client: httpx.AsyncClient,
    base_url: str,
    profile_name: str,
    approval_confirmed: bool = False,
    auth_token: Optional[str] = None,
) -> bool:
    print(f"\n{'='*70}")
    print(f"STAGE EXECUTION: Profile '{profile_name}'")
    print(f"{'='*70}")

    headers = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    # 1. Preflight Readiness
    print("  [1/4] Running Preflight Readiness Check...")
    preflight_resp = await client.post(
        f"{base_url.rstrip('/')}/api/v1/benchmarks/preflight",
        json={"profile_name": profile_name},
        headers=headers,
    )
    if preflight_resp.status_code != 200:
        print(f"  ✗ Preflight check call failed: HTTP {preflight_resp.status_code}")
        return False

    pf = preflight_resp.json()
    if not pf.get("ready"):
        print(f"  ✗ Preflight check BLOCKED for '{profile_name}':")
        for msg in pf.get("messages", []):
            print(f"    • {msg}")
        return False
    print("  ✓ Preflight passed.")

    # 2. Check Authorization
    if pf.get("requires_explicit_approval") and not approval_confirmed:
        print("  ✗ Explicit operator approval is REQUIRED for this stage. Set --approve flag.")
        return False

    # 3. Trigger Benchmark Run
    print(f"  [2/4] Triggering Benchmark Run for '{profile_name}'...")
    run_resp = await client.post(
        f"{base_url.rstrip('/')}/api/v1/benchmarks/run",
        json={
            "profile_name": profile_name,
            "approval_confirmed": approval_confirmed,
            "target_environment": "local",
        },
        headers=headers,
    )
    if run_resp.status_code != 201:
        print(f"  ✗ Benchmark run creation failed: HTTP {run_resp.status_code} - {run_resp.text}")
        return False

    bmk = run_resp.json()
    benchmark_id = bmk.get("id")
    duration = bmk.get("duration_seconds", 30)
    print(f"  ✓ Benchmark launched: ID={benchmark_id}, Users={bmk.get('virtual_users')}, Configured Duration={duration}s")

    # 4. Wait for Completion
    print(f"  [3/4] Running experiment window ({duration}s)...")
    await asyncio.sleep(duration + 2)

    # 5. Fetch Final Report and Artifacts (poll until finalization commits)
    print("  [4/4] Verifying Final SLA Results & Artifacts...")
    final_data = {}
    for _ in range(15):
        await asyncio.sleep(1.5)
        res_resp = await client.get(
            f"{base_url.rstrip('/')}/api/v1/benchmarks/results/{benchmark_id}",
            headers=headers,
        )
        if res_resp.status_code == 200:
            final_data = res_resp.json()
            if (final_data.get("requests_per_second", 0.0) > 0.0) or final_data.get("abort_reason"):
                break

    if not final_data:
        print(f"  ✗ Failed to fetch final results: HTTP {res_resp.status_code}")
        return False
    passed = final_data.get("passed_thresholds")
    status_str = "SLA PASSED" if passed else "SLA BREACHED / ABORTED"
    print(f"\n  Final Result: {status_str}")
    print(f"  - RPS Achieved:      {final_data.get('requests_per_second', 0.0):.1f} req/s")
    print(f"  - p95 Latency:       {final_data.get('p95_latency_ms', 0.0):.1f} ms")
    print(f"  - Error Rate:        {final_data.get('error_rate_pct', 0.0):.2f}%")
    if final_data.get("abort_reason"):
        print(f"  - Abort Reason:      {final_data.get('abort_reason')}")

    # Check generated artifacts
    art_resp = await client.get(
        f"{base_url.rstrip('/')}/api/v1/benchmarks/results/{benchmark_id}/artifacts",
        headers=headers,
    )
    if art_resp.status_code == 200:
        art_data = art_resp.json()
        print(f"  - Artifacts Generated: {len(art_data.get('files', []))} files in {art_data.get('artifact_directory')}")
        for f in art_data.get("files", [])[:6]:
            print(f"    • {f}")

    return passed


async def main_async():
    parser = argparse.ArgumentParser(description="ViewStorm Progressive Benchmark Runner")
    parser.add_argument("--control-plane-url", default="http://127.0.0.1:8000", help="Control Plane URL")
    parser.add_argument("--stages", nargs="+", default=["smoke", "baseline"], help="Ordered list of profiles to execute")
    parser.add_argument("--approve", action="store_true", help="Confirm explicit authorization for high-tier profiles")
    parser.add_argument("--token", default=None, help="Operator Bearer JWT token if auth enabled")
    args = parser.parse_args()

    async with httpx.AsyncClient(timeout=30.0) as client:
        for stage in args.stages:
            success = await run_single_stage(
                client=client,
                base_url=args.control_plane_url,
                profile_name=stage,
                approval_confirmed=args.approve,
                auth_token=args.token,
            )
            if not success:
                print(f"\nStage '{stage}' failed or was blocked. Halting staged progression.")
                sys.exit(1)

    print("\n✓ All requested benchmark stages completed successfully!")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
