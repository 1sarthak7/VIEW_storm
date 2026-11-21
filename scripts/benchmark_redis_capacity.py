#!/usr/bin/env python3
"""Benchmark Redis Lua Event Ingestion Pipeline & Memory Growth."""

import asyncio
import time
import uuid
import redis.asyncio as redis


LUA_SCRIPT = """
local idempotency_key = KEYS[1]
local stats_key = KEYS[2]
local types_key = KEYS[3]
local viewers_key = KEYS[4]
local timestamps_key = KEYS[5]

local event_id = ARGV[1]
local event_type = ARGV[2]
local viewer_id = ARGV[3]
local duration = tonumber(ARGV[4])
local current_time = tonumber(ARGV[5])
local ttl = tonumber(ARGV[6])

if redis.call("EXISTS", idempotency_key) == 1 then
    redis.call("HINCRBY", stats_key, "duplicate_events", 1)
    redis.call("HINCRBY", stats_key, "total_submissions", 1)
    return {0, "DUPLICATE"}
end

redis.call("SET", idempotency_key, "1", "EX", ttl)
redis.call("HINCRBY", stats_key, "accepted_events", 1)
redis.call("HINCRBY", stats_key, "total_submissions", 1)
redis.call("HINCRBY", stats_key, "total_watch_duration_ms", duration)
redis.call("HINCRBY", types_key, event_type, 1)
redis.call("SADD", viewers_key, viewer_id)
redis.call("LPUSH", timestamps_key, current_time)
redis.call("LTRIM", timestamps_key, 0, 500)

return {1, "ACCEPTED"}
"""


async def main():
    print("=" * 70)
    print("VIEWSTORM REDIS LUA PIPELINE BENCHMARK")
    print("=" * 70)

    r = redis.from_url("redis://localhost:6379/0")
    await r.ping()

    sha = await r.script_load(LUA_SCRIPT)
    run_id = f"redis_bmk_{uuid.uuid4().hex[:8]}"
    stats_k = f"run:{run_id}:stats"
    types_k = f"run:{run_id}:event_types"
    viewers_k = f"run:{run_id}:viewers"
    times_k = f"run:{run_id}:timestamps"

    info_before = await r.info("memory")
    used_mem_before = info_before["used_memory"]

    batch_sizes = [500, 1000, 2500, 5000]
    print(f"{'Batch Size':<12} | {'Time (s)':<10} | {'Ops / Sec':<16} | {'Avg Latency (ms)':<18}")
    print("-" * 65)

    for b in batch_sizes:
        keys_batch = []
        for i in range(b):
            event_id = f"evt_{uuid.uuid4().hex}"
            idempotency_k = f"run:{run_id}:idempotency:{event_id}"
            keys_batch.append((idempotency_k, event_id, f"viewer_{i % 200:04d}"))

        t0 = time.perf_counter()
        async with r.pipeline(transaction=False) as pipe:
            for idemp_k, evt_id, viewer in keys_batch:
                pipe.evalsha(
                    sha,
                    5,
                    idemp_k,
                    stats_k,
                    types_k,
                    viewers_k,
                    times_k,
                    evt_id,
                    "playback_start",
                    viewer,
                    15000,
                    time.time(),
                    3600,
                )
            results = await pipe.execute()

        elapsed = time.perf_counter() - t0
        ops_sec = b / elapsed if elapsed > 0 else 0.0
        avg_lat = (elapsed / b) * 1000.0

        print(f"{b:<12} | {elapsed:<10.3f} | {ops_sec:<16.1f} | {avg_lat:<18.3f}")

    info_after = await r.info("memory")
    used_mem_after = info_after["used_memory"]
    mem_delta_kb = (used_mem_after - used_mem_before) / 1024.0

    print("-" * 65)
    print(f"Total Unique Viewers Tracked: {await r.scard(viewers_k)}")
    print(f"Memory Growth:                {mem_delta_kb:.1f} KB across {sum(batch_sizes)} events")
    print(f"Per-Event Memory Overhead:    {(mem_delta_kb * 1024.0) / sum(batch_sizes):.1f} bytes / event")
    print("=" * 70)

    # Cleanup
    await r.delete(stats_k, types_k, viewers_k, times_k)
    await r.aclose()


if __name__ == "__main__":
    asyncio.run(main())
