# Runner Process Lifecycle & State Machine

## 1. Lifecycle State Machine
```
[PENDING]
    |
    | POST /api/v1/runs/{id}/start
    v
[RUNNING] (Locust subprocess PID spawned, CSV outputs created)
    |
    +----------------------------------+----------------------------------+
    |                                  |                                  |
    | POST /runs/{id}/stop             | Duration Expired                 | Non-zero Exit / Crash
    v                                  v                                  v
[STOPPED] (SIGTERM -> SIGKILL)   [COMPLETED] (code 0)               [FAILED] (code != 0)
    |                                  |                                  |
    +----------------------------------+----------------------------------+
                                       |
                                       v
                     Final Locust Metrics Parsed & Stored
                     Redis Aggregates Flushed to PostgreSQL
                     Runner Subprocess Resources Cleaned Up
```

## 2. Termination & Graceful Shutdown
1. When stopped manually or on server shutdown, `SIGTERM` is delivered to the runner process group.
2. The runner is granted a 5.0-second grace period (`stop_grace_period_seconds`) to finish ongoing HTTP calls and flush CSV buffers.
3. If the process does not terminate within the grace window, escalation to `SIGKILL` ensures no orphaned load generators persist.
4. On backend startup, `cleanup_orphaned_runners()` detects and terminates any lingering Locust processes from prior aborted sessions.
