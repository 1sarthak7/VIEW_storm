# Control Plane and Data Plane Separation Architecture

## 1. Context and Problem Statement

In early milestones, a single monolithic FastAPI process served both control functions (dashboard API, worker registry, simulation runners, benchmarks, emergency stop) and data ingestion (`POST /api/v1/events/playback`).

Under high-concurrency synthetic testing (e.g., 5,000 to 200,000 virtual users emitting thousands of events per second):
1. The Python asynchronous event loop became congested processing JSON deserialization and Pydantic validation.
2. In-flight requests caused latency spikes on administrative endpoints.
3. Operator dashboard polling lagged or timed out.
4. Emergency-stop signals could be delayed by queue backup.

Milestone 8 completely resolves this by physically and logically decoupling the application into a **Control Plane** and a **Data Plane**.

---

## 2. Logical Separation Matrix

```
+-----------------------------------------------------------------------------------------+
|                                    VIEWSTORM SYSTEM                                     |
+--------------------------------------------+--------------------------------------------+
|            CONTROL PLANE                   |                DATA PLANE                  |
|       (Orchestration & Oversight)          |          (High-Throughput Ingestion)       |
+--------------------------------------------+--------------------------------------------+
| - React 19 Analytics Dashboard             | - Playback Event Endpoint (/events/playback|
| - Authentication & JWT RBAC (Admin/Op)     | - Batch Playback Endpoint (/events/batch)  |
| - Simulation Lifecycle Orchestrator        | - Real-time Ingestion Statistics (/stats)  |
| - Worker Node Registry & Assignments       | - Atomic Redis Lua Deduplication Pipeline  |
| - Standardized Benchmark Engine            | - Real-time Sliding-Window Throughput      |
| - Global Emergency Stop Kill Switch        | - Playback Event Metrics Exporter          |
| - SLA Guardrail Monitor & Abort Loops      | - Target-side DB Persistence (Batch Flush) |
| - PostgreSQL System of Record Operations   |                                            |
| - Locust Master Process (ZeroMQ 5557/5558) |                                            |
| - Prometheus Metric Scraper (/metrics)     |                                            |
+--------------------------------------------+--------------------------------------------+
| Entrypoint: app.controlplane_main:app      | Entrypoint: app.dataplane_main:app         |
| Default Port: 8000                         | Default Port: 8001                         |
| Network: control_plane_net                 | Network: data_plane_net                    |
+--------------------------------------------+--------------------------------------------+
```

---

## 3. Shared vs. Isolated Resources

### 3.1 Redis In-Memory Subsystems
- **Data Plane (Isolated Key Namespaces)**:
  - `viewstorm:events:{run_id}:seen` (Idempotency deduplication set)
  - `viewstorm:stats:{run_id}` (Atomic event counters & watch duration)
  - `viewstorm:viewers:{run_id}` (HyperLogLog unique synthetic viewer tracking)
  - `viewstorm:events:{run_id}:recent` (Circular ring-buffer of recent events)
- **Control Plane (Isolated Key Namespaces)**:
  - `viewstorm:workers:{worker_id}:lease` (Heartbeat liveness lease)
  - `viewstorm:workers:{worker_id}:assignment` (Workload distribution payload)
  - `viewstorm:emergency_stop:active` (Global kill-switch flag)
  - `viewstorm:auth:bootstrap_token` (One-time cryptographic initialization token)

### 3.2 PostgreSQL Database Persistence
- **Control Plane**: Owns write operations on `users`, `simulation_runs`, `load_generator_nodes`, `worker_calibrations`, and `benchmark_results`.
- **Data Plane / Aggregation**: Decoupled from synchronous request handling; writes time-series metrics (`simulation_metrics`) and final summaries (`event_summaries`) in batched background transactions.

---

## 4. Control Plane Survivability Proof

Because the Control Plane operates on an independent process, listening socket, and thread/event loop:
1. **Zero Event-Loop Contention**: 100% of the Control Plane event loop CPU cycles remain available for dashboard requests, status polling, and emergency-stop commands.
2. **Deterministic Kill-Switch Execution**: An operator clicking "Emergency Stop" immediately updates Redis and issues process termination signals without queuing behind in-flight playback events.
3. **Verified Benchmarking Accuracy**: The Control Plane can sample system metrics, poll worker statuses, and evaluate SLA guardrails without measuring client-side queue delays induced by its own servers.
