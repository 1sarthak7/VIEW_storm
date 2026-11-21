# PostgreSQL Database Architecture & Schema Specification

## 1. Role in ViewStorm
PostgreSQL serves as the system of record for ViewStorm. It durably stores simulation run configurations, lifecycle history, historical time-series performance metrics, worker health registrations, and aggregated event summaries.

Individual synthetic events are **never** written synchronously to PostgreSQL under high load. Instead, Redis handles per-event atomic counting, and PostgreSQL stores periodically batched and finalized aggregates.

## 2. Relational Schema & Entities

```
+--------------------+            +------------------------+
|  simulation_runs   | 1 <---- *  |   simulation_metrics   |
|--------------------|            |------------------------|
| id (PK)            |            | id (PK)                |
| name               |            | run_id (FK -> runs.id) |
| target_environment |            | timestamp (indexed)    |
| virtual_users      |            | active_users           |
| spawn_rate         |            | requests_per_second    |
| duration_seconds   |            | successful_requests    |
| event_type         |            | failed_requests        |
| watch_duration_min |            | average_latency        |
| watch_duration_max |            | p95_latency            |
| status (indexed)   |            | p99_latency            |
| created_at         |            +------------------------+
| started_at         |
| finished_at        |            +------------------------+
| error_message      | 1 <---- *  |    event_summaries     |
+--------------------+            |------------------------|
          |                       | id (PK)                |
          | 1                     | run_id (FK -> runs.id) |
          v *                     | event_type             |
+------------------------+        | accepted_count         |
|   simulation_workers   |        | rejected_count         |
|------------------------|        | duplicate_count        |
| id (PK)                |        | total_watch_duration   |
| run_id (FK -> runs.id) |        | recorded_at            |
| worker_identifier (idx)|        +------------------------+
| status                 |
| last_heartbeat         |
| resource_information   |
+------------------------+
```

## 3. Foreign Key Cascades & Indexes
- All child tables reference `simulation_runs.id` with `ON DELETE CASCADE`.
- B-Tree indexes are defined on `status`, `run_id`, `worker_identifier`, and `timestamp`.

## 4. Alembic Migrations
Migrations are managed in `backend/alembic/versions/` with support for asyncpg:
- Upgrade: `alembic upgrade head`
- Downgrade: `alembic downgrade -1`
