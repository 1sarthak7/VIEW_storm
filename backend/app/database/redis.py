"""Redis Asynchronous Connection and Atomic Operations Service."""

from typing import AsyncGenerator, Optional
import redis.asyncio as aioredis
from redis.asyncio import ConnectionPool, Redis
from app.core.config import settings
from app.core.logging import logger

# Redis Connection Pool
redis_pool = ConnectionPool.from_url(
    settings.redis_url,
    max_connections=settings.redis_pool_size,
    decode_responses=True,
)

redis_client = Redis(connection_pool=redis_pool)

# Key naming convention functions
def run_stats_key(run_id: str) -> str:
    return f"viewstorm:run:{run_id}:stats"

def run_events_key(run_id: str) -> str:
    return f"viewstorm:run:{run_id}:processed_events"

def run_viewers_key(run_id: str) -> str:
    return f"viewstorm:run:{run_id}:viewers"

def run_event_types_key(run_id: str) -> str:
    return f"viewstorm:run:{run_id}:event_types"

def run_timestamps_key(run_id: str) -> str:
    return f"viewstorm:run:{run_id}:recent_timestamps"


# Atomic Lua script for event deduplication and counter increments
INGEST_EVENT_LUA = """
-- KEYS[1] = processed_events (Set)
-- KEYS[2] = stats (Hash)
-- KEYS[3] = event_types (Hash)
-- KEYS[4] = viewers (Set)
-- KEYS[5] = recent_timestamps (List)
-- ARGV[1] = event_id
-- ARGV[2] = event_type
-- ARGV[3] = viewer_id
-- ARGV[4] = watch_duration_ms
-- ARGV[5] = timestamp_epoch
-- ARGV[6] = stats_ttl_seconds

local is_dup = redis.call('SISMEMBER', KEYS[1], ARGV[1])
if is_dup == 1 then
    redis.call('HINCRBY', KEYS[2], 'total_submissions', 1)
    redis.call('HINCRBY', KEYS[2], 'duplicate_events', 1)
    return 0
else
    redis.call('SADD', KEYS[1], ARGV[1])
    redis.call('HINCRBY', KEYS[2], 'total_submissions', 1)
    redis.call('HINCRBY', KEYS[2], 'accepted_events', 1)
    redis.call('HINCRBY', KEYS[2], 'total_watch_duration_ms', tonumber(ARGV[4]))
    redis.call('HINCRBY', KEYS[3], ARGV[2], 1)
    redis.call('SADD', KEYS[4], ARGV[3])
    redis.call('LPUSH', KEYS[5], ARGV[5])
    redis.call('LTRIM', KEYS[5], 0, 1999)
    local ttl = tonumber(ARGV[6])
    if ttl and ttl > 0 then
        redis.call('EXPIRE', KEYS[1], ttl)
        redis.call('EXPIRE', KEYS[2], ttl)
        redis.call('EXPIRE', KEYS[3], ttl)
        redis.call('EXPIRE', KEYS[4], ttl)
        redis.call('EXPIRE', KEYS[5], ttl)
    end
    return 1
end
"""


async def get_redis() -> AsyncGenerator[Redis, None]:
    """Dependency yielding Redis async client."""
    yield redis_client


async def check_redis_health() -> bool:
    """Perform real Redis ping probe."""
    try:
        return await redis_client.ping() is True
    except Exception as exc:
        logger.warning("Redis health check failed: %s", exc)
        return False
