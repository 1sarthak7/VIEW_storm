# Redis Architecture & Key Scoping Specification

## 1. Role in ViewStorm
Redis serves as the high-throughput, low-latency transient data layer. It handles real-time counter mutations, event deduplication, unique synthetic viewer sets, and worker synchronization.

## 2. Key Naming Convention
All Redis keys are explicitly scoped by the simulation `run_id`:

| Key Format | Redis Type | Purpose | TTL |
|---|---|---|---|
| `viewstorm:run:{run_id}:stats` | Hash | Aggregate counters (`total_submissions`, `accepted_events`, `rejected_events`, `duplicate_events`, `total_watch_duration_ms`) | 7 days |
| `viewstorm:run:{run_id}:processed_events` | Set | Set of ingested `event_id` strings for atomic deduplication | 7 days |
| `viewstorm:run:{run_id}:viewers` | Set | Set of distinct synthetic `viewer_id` strings for viewer cardinality | 7 days |
| `viewstorm:run:{run_id}:event_types` | Hash | Counter map breakdown by event type (e.g. `playback_start`: count) | 7 days |
| `viewstorm:run:{run_id}:recent_timestamps` | List | Rolling queue of recent submission epochs (max 2,000 entries) for RPS calculation | 7 days |

## 3. Atomic Deduplication via Lua Script
To prevent race conditions across multiple concurrent load generator processes or distributed FastAPI backend instances, event ingestion executes an atomic Lua script (`INGEST_EVENT_LUA`):

```lua
-- KEYS[1] = processed_events (Set)
-- KEYS[2] = stats (Hash)
-- KEYS[3] = event_types (Hash)
-- KEYS[4] = viewers (Set)
-- KEYS[5] = recent_timestamps (List)
-- ARGV[1] = event_id, ARGV[2] = event_type, ARGV[3] = viewer_id, ARGV[4] = watch_duration_ms, ARGV[5] = timestamp, ARGV[6] = ttl

local is_dup = redis.call('SISMEMBER', KEYS[1], ARGV[1])
if is_dup == 1 then
    redis.call('HINCRBY', KEYS[2], 'total_submissions', 1)
    redis.call('HINCRBY', KEYS[2], 'duplicate_events', 1)
    return 0 -- Duplicate
else
    redis.call('SADD', KEYS[1], ARGV[1])
    redis.call('HINCRBY', KEYS[2], 'total_submissions', 1)
    redis.call('HINCRBY', KEYS[2], 'accepted_events', 1)
    redis.call('HINCRBY', KEYS[2], 'total_watch_duration_ms', tonumber(ARGV[4]))
    redis.call('HINCRBY', KEYS[3], ARGV[2], 1)
    redis.call('SADD', KEYS[4], ARGV[3])
    redis.call('LPUSH', KEYS[5], ARGV[5])
    redis.call('LTRIM', KEYS[5], 0, 1999)
    -- Extend TTL on active mutation
    return 1 -- Accepted
end
```

## 4. Eviction and Retention Policies
- **Key Expiry**: Keys are assigned a configurable TTL (`stats_retention_ttl_seconds`, default 7 days) upon run initialization and renewed on event ingestion.
- **Durable Sync**: When a simulation is stopped, `AggregationService` synchronizes Redis data into PostgreSQL `EventSummary` and `SimulationMetric` tables.
