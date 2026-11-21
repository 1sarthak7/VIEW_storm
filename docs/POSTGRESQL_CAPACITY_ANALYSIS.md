# PostgreSQL Database Capacity Analysis

## 1. Architectural Role of PostgreSQL

PostgreSQL 16 serves as ViewStorm's persistent system of record:
1. **Simulation Runs & Configuration**: Metadata, lifecycle state (`PENDING`, `RUNNING`, `COMPLETED`, `INTERRUPTED`), parameter schemas.
2. **Aggregated Summaries**: `event_summaries` records computed by `AggregationService` when simulations complete.
3. **Time-Series Metric Samples**: `simulation_metrics` records capturing 1-second snapshots of virtual users, RPS, latency, and error rates.
4. **Worker Node Calibrations**: Historical saturation benchmarks per worker host.
5. **Standardized Benchmark Results**: Software, infrastructure, and workload metadata alongside SLA pass/fail verdicts.

---

## 2. Empirical Batch Persistence Benchmarks

We measured batch insert throughput (`scripts/benchmark_postgres_capacity.py`) using SQLAlchemy asyncpg connection pools against PostgreSQL 16:

```
Batch Size:                 2,500 records
Elapsed Time:               0.0565 seconds
Batch Throughput:           44,271 records/second
Average Batch Latency:      22.58 microseconds / record
```

### Key Takeaway
Database writes will **not** bottleneck simulation execution when metric recording is decoupled from real-time request handling. By queuing time-series samples in-memory or Redis and flushing them to PostgreSQL in multi-record batches, the database easily sustains high volumes without locking.

---

## 3. Connection Pooling and Concurrency Management

ViewStorm utilizes `SQLAlchemy` asynchronous sessions backed by `asyncpg`.
- **Default Pool Size**: `pool_size=20`, `max_overflow=10`, `pool_timeout=30s`.
- **Session Lifecycle**: API endpoints acquire short-lived scoped sessions that are committed and returned to the pool immediately upon request completion.
- **Background Flusher**: Dedicated single async connection for periodic metric batch insertions.

### Index Optimization Strategy
To ensure fast reads in the analytics dashboard under heavy table growth:
- Composite index on `(simulation_id, timestamp)` on `simulation_metrics` enables rapid range scans for dashboard chart rendering.
- Unique index on `(worker_id)` and index on `tested_at` on `worker_calibrations`.
- Index on `(profile_name, created_at)` on `benchmark_results` powers real-time candidate vs baseline lookups.
