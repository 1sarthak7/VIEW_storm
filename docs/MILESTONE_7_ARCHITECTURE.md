# ViewStorm — Milestone 7: Large-Scale Distributed Capacity Validation Architecture

## 1. Executive Summary

Milestone 7 transitions ViewStorm from a functional distributed traffic simulation platform to an enterprise-grade, capacity-validated benchmarking suite capable of scaling synthetic workloads safely and reproducibly up to 200,000 concurrent virtual users across authorized infrastructure.

The core objectives of Milestone 7 are:
1. **Security Preconditions & Ephemeral Bootstrapping**: Zero hardcoded administrative credentials in source, environment, or UI; dynamic one-time cryptographic bootstrapping.
2. **Worker Capacity Calibration**: Autonomous multi-step saturation testing to determine maximum sustainable virtual users per physical/virtual worker node.
3. **Subsystem Capacity Profiling**: Empirical characterization of Locust Master, FastAPI backend ingestion, Redis atomic Lua pipeline, and PostgreSQL batch persistence.
4. **9 Standardized Benchmark Profiles**: Strict SLA guardrails (error rate, p95 latency) and automated safety abort triggers across Smoke (10 users) through Target (200,000 users).
5. **Operator Authorization Governance**: Cryptographically audited explicit operator approval required before executing high-scale benchmarks ($\ge 25,000$ users).
6. **Reproducibility & Comparative Benchmarking**: Full capture of software revisions, environment topography, resource saturation, and delta comparison verdicts (`IMPROVEMENT`, `REGRESSION`, `STABLE`, `INCOMPARABLE`).

---

## 2. High-Level System Architecture

```
                             +----------------------------------------+
                             |    ViewStorm React Dashboard (UI)      |
                             |  (Profile Selector, Preflight Checks) |
                             +--------------------+-------------------+
                                                  |
                                           HTTPS / REST
                                                  |
                                                  v
                             +----------------------------------------+
                             |       FastAPI Control Plane            |
                             |  - BenchmarkService (9 Profiles)       |
                             |  - Preflight Validation Engine         |
                             |  - Abort Monitoring (Error, RAM, SLA)  |
                             |  - WorkerCalibrationService            |
                             +--------+-------------------+-----------+
                                      |                   |
                        PostgreSQL AsyncPool         Redis 7/8 Sentinel
                                      |                   |
                                      v                   v
                        +-------------+----+      +-------+-------------+
                        | PostgreSQL 16    |      | Redis Cache & Lua   |
                        | - Benchmarks     |      | - Token Bucket      |
                        | - Calibrations   |      | - Idempotency Sets  |
                        | - Batch Metrics  |      | - Event Counters    |
                        +------------------+      +---------------------+
                                      ^
                                      |
                             Locust Master (ZeroMQ)
                         (Port 5557: REP / Port 5558: PUB)
                                      |
                     +----------------+----------------+
                     |                                 |
                     v                                 v
        +-------------------------+       +-------------------------+
        |  Worker Node 1          |  ...  |  Worker Node N          |
        |  - Calibrated Capacity  |       |  - Calibrated Capacity  |
        |  - Local Subprocesses   |       |  - Local Subprocesses   |
        +------------+------------+       +------------+------------+
                     |                                 |
                     +----------------+----------------+
                                      |
                       Synthetic Playback Event HTTP Ingestion
                                      v
                             +------------------+
                             | Target API Farm  |
                             | (Authorized Only)|
                             +------------------+
```

---

## 3. Core Architectural Components

### 3.1 One-Time Ephemeral Bootstrapping
- Traditional systems suffer from credential leakage through source repository history or static default variables.
- ViewStorm enforces dynamic initialization: if the administrative database is unseeded, an ephemeral cryptographic token is generated using Python's `secrets.token_urlsafe(32)`.
- The token is written to an atomic file permissions-restricted to the system operator (`chmod 0600`) and cached in Redis with a 15-minute TTL.
- Once the initial administrator executes `POST /api/v1/auth/bootstrap`, the token is immediately invalidated and destroyed. Subsequent attempts return HTTP 410 (Gone).

### 3.2 Automated Preflight Verification
Before any benchmark profile can be dispatched, `BenchmarkService.preflight_check()` executes a comprehensive readiness evaluation:
- **Emergency Stop Status**: Confirms no active global kill-switch is engaged.
- **Database & Cache Health**: Confirms Redis PING latency $\le 10\text{ms}$ and PostgreSQL connection pool readiness.
- **Host Available Memory**: Confirms host system has $\ge 500\text{ MB}$ unallocated physical memory headroom.
- **Worker Capacity Verification**: Queries active online worker nodes in `worker_registry_service`, sums calibrated sustainable capacity, and asserts that total cluster capacity meets or exceeds the profile's `virtual_users`.
- **Operator Authorization**: If `requires_explicit_approval` is `True` (Profiles 6-9), asserts `approval_confirmed == True`.

### 3.3 Active Safety Abort Loop
During execution, the background monitor continuously tracks:
1. **Error Rate Spike**: If real-time failure rate exceeds $2.5\times$ the profile SLA (or $>12\%$ absolute), the run is aborted immediately.
2. **Host Memory Exhaustion**: If available system memory drops below $300\text{ MB}$, the runner halts to prevent kernel OOM-killer deadlocks.
3. **Emergency Stop Interruption**: If an operator clicks Emergency Stop or calls `POST /api/v1/emergency/stop`, all master and worker processes are terminated via `SIGTERM` followed by `SIGKILL`.

---

## 4. Benchmark Reproducibility & Comparison Engine

Each benchmark run persists four immutable metadata payloads in PostgreSQL:
1. **Software Metadata**: Git commit SHA, branch name, Python runtime version, Locust version, OS kernel release.
2. **Infrastructure Metadata**: Host CPU count, total RAM, worker node topography, network interface MTU.
3. **Workload Metadata**: Configured profile name, virtual users, spawn rate, duration, test execution mode (`local` vs `distributed`).
4. **Resource Metrics**: Peak CPU utilization, average host memory usage, accepted HTTP events, network throughput.

### Delta Evaluation & Verdict Logic
When comparing candidate run $C$ against baseline run $B$:
- If $C.\text{virtual\_users} \ne B.\text{virtual\_users}$ or worker node count differs: **`INCOMPARABLE`**.
- If $C.\text{error\_rate} > B.\text{error\_rate} + 1.0\%$ or $C.\text{p95\_latency} > B.\text{p95\_latency} \times 1.10$: **`REGRESSION`**.
- If $C.\text{rps} \ge B.\text{rps} \times 1.05$ and latencies are non-degrading: **`IMPROVEMENT`**.
- Otherwise: **`STABLE`**.
