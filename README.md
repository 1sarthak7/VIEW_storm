# ViewStorm — Distributed Synthetic Traffic & Virtual-Viewer Simulation Platform

ViewStorm is an enterprise-grade distributed virtual-viewer simulation and performance-engineering platform. It simulates high-throughput synthetic playback events against explicitly authorized test environments, measuring concurrent API capacity, latency distributions, worker cluster scaling, and database persistence.

---

## Architecture Overview

```
                                      ┌─────────────────────────────────────────────────────────┐
                                      │              ViewStorm React Dashboard                  │
                                      │   Overview | Simulations | Workers | Analytics | Reports │
                                      └──────────────────────────┬──────────────────────────────┘
                                                                 │ HTTP / JSON
                                                                 ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       FastAPI Ingestion & Control Plane                                 │
│                                                                                                        │
│   ┌────────────────────┐   ┌───────────────────────────┐   ┌─────────────────┐   ┌──────────────────┐  │
│   │   Auth & RBAC      │   │  Emergency Stop Subsystem │   │  Benchmarking   │   │ Prometheus Met.  │  │
│   │ (Admin/Op/Viewer)  │   │   (Global Kill-Switch)    │   │  (SLA Guard)    │   │   (/metrics)     │  │
│   └────────────────────┘   └───────────────────────────┘   └─────────────────┘   └──────────────────┘  │
│                                                                                                        │
│   ┌──────────────────────────────────────────────┐     ┌───────────────────────────────────────────┐   │
│   │   Local Locust Engine (Subprocess Manager)   │     │  Distributed Locust Master (ZeroMQ: 5557) │   │
│   └──────────────────────────────────────────────┘     └─────────────────────┬─────────────────────┘   │
└──────────────────────────┬───────────────────────────────────────────────────┼─────────────────────────┘
                           │ Redis Pipeline                                    │ ZeroMQ / HTTP Heartbeats
                           ▼                                                   ▼
┌─────────────────────────────────────────────────────────┐   ┌──────────────────────────────────────────┐
│                   Redis 7 Cluster                       │   │ Distributed Worker Nodes (worker-agent)  │
│  - Atomic Lua Event Deduplication (SHA256)             │   │  - Capacity-Aware Proportional Allocs    │
│  - High-Throughput HyperLogLog / Set Viewer Tracking   │   │  - Dynamic Subprocess Spawning           │
│  - Real-Time Sliding-Window RPS Counters                │   │  - Auto-Heartbeat & Failover Recovery    │
└──────────────────────────┬──────────────────────────────┘   └──────────────────────────────────────────┘
                           │ Background Flush (AggregationService)
                           ▼
┌─────────────────────────────────────────────────────────┐
│               PostgreSQL 16 Persistent Store            │
│  - Simulation Runs & Lifecycle State Records            │
│  - Historical Metrics Time-Series                       │
│  - Benchmark Results & SLA Evaluations                  │
│  - Users & Operator RBAC Credentials                    │
└─────────────────────────────────────────────────────────┘
```

---

## Core Capabilities

1. **Synthetic Playback Event Ingestion Engine**:
   - Atomic Lua ingestion with SHA-256 deduplication and idempotent replay protection.
   - Microsecond Redis counter aggregation and unique viewer tracking.

2. **Distributed Master-Worker Locust Architecture**:
   - ZeroMQ port 5557 cluster communication.
   - Dynamic worker node capacity registration and proportional user assignment.
   - Dynamic heartbeat monitoring and stale worker eviction.

3. **Production Hardening & Security (Milestone 6)**:
   - **Operator RBAC**: `admin`, `operator`, `viewer` roles.
   - **Argon2id Cryptography**: Secure memory-hard password hashing.
   - **JWT Bearer Authentication**: Signed token sessions with brute-force rate-limiting (5 failures / 5 minutes).
   - **Target Allowlisting**: Guardrails restricting load generation strictly to authorized local environments.

4. **Reliability & Crash Recovery**:
   - **Startup Lifecycle Reconciliation**: Automatically detects and transitions orphan/zombie runs to `INTERRUPTED`.
   - **Global Emergency Stop**: Instant distributed kill-switch terminating all local and remote generators in milliseconds.

5. **Large-Scale Distributed Capacity Validation (Milestone 7)**:
   - **Worker Capacity Calibration**: Stepped ramp calibration testing (10 to 500+ users), saturation detection (CPU >85%, RAM <15%, error >2%, p95 >1500ms), and 75% sustainable capacity enforcement.
   - **9 Standardized Profiles**: Smoke (10), Baseline (100), Small (1,000), Medium (5,000), Large (10,000), Extended (25,000), High Capacity (50,000), Extreme (100,000), and Target (200,000).
   - **Cluster Preflight Verification**: Multi-factor validation checking Emergency Stop, Redis latency, PostgreSQL health, host RAM (>500MB), and online worker fleet capacity.
   - **Operator Authorization**: Explicit cryptographic approval protocol for high-tier profiles (>=25k virtual users).
   - **Automated Safety Aborts**: Instant termination on error rate spikes (>2.5x SLA or >12%) or low system memory (<300MB).
   - **Reproducibility & Comparison**: Full software, infrastructure, and workload metadata capture with `IMPROVEMENT`, `REGRESSION`, `STABLE`, or `INCOMPARABLE` delta verdicts.

6. **React 19 Analytics & Benchmarking Dashboard**:
   - Route-based code splitting with `React.lazy` and manual vendor chunking, achieving a **75% reduction** in initial bundle size.
   - Interactive Benchmarks dashboard (`/benchmarks`) with profile selection, real-time preflight checklist, authorization acknowledgment, live telemetry, and regression comparison modal.
   - Interactive charts for Throughput, Latency Distributions (p50/p95/p99), Virtual User Ramps, and Event Breakdowns.
   - Prominent Emergency Halt banner with administrative clear actions.

---

## Quick Start

### 1. Start Infrastructure
```bash
docker compose -f infrastructure/docker-compose.yml up -d
```

### 2. Backend Setup
```bash
cd backend
python -m venv ../.venv
source ../.venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Frontend Dashboard
```bash
cd frontend
npm install
npm run dev
```

Visit the dashboard at `http://localhost:5173`.
On first launch, initialize the root administrator via one-time bootstrap token (displayed in the backend startup log or stored in `.viewstorm_bootstrap.token`).

### 4. Running Distributed Workers
```bash
cd worker-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m worker_agent.main --coordinator-url http://localhost:8000 --capacity 500
```

---

## Automated Verification

### Backend Test Suite (71 Tests)
```bash
cd backend
pytest tests -v
```

### Frontend Test Suite (15 Tests) & Bundle Verification
```bash
cd frontend
npm test
npm run typecheck
npm run build
```

---

## Documentation Index
- [Milestone 7 Architecture](docs/MILESTONE_7_ARCHITECTURE.md)
- [Worker Capacity Calibration](docs/WORKER_CAPACITY_CALIBRATION.md)
- [Master Capacity Analysis](docs/MASTER_CAPACITY_ANALYSIS.md)
- [Backend Capacity Analysis](docs/BACKEND_CAPACITY_ANALYSIS.md)
- [Redis Capacity Analysis](docs/REDIS_CAPACITY_ANALYSIS.md)
- [PostgreSQL Capacity Analysis](docs/POSTGRESQL_CAPACITY_ANALYSIS.md)
- [Large-Scale Benchmarking](docs/LARGE_SCALE_BENCHMARKING.md)
- [Capacity Planning (200k Users)](docs/CAPACITY_PLANNING.md)
- [Benchmark Results](docs/BENCHMARK_RESULTS.md)
- [Security & RBAC](docs/SECURITY.md)
- [Reliability & Emergency Stop](docs/RELIABILITY_AND_RECOVERY.md)
- [Benchmarking Guide](docs/BENCHMARKING_GUIDE.md)
- [Frontend Optimization](docs/FRONTEND_OPTIMIZATION.md)
- [Distributed Architecture](docs/DISTRIBUTED_ARCHITECTURE.md)
- [Database Architecture](docs/DATABASE_ARCHITECTURE.md)
- [Redis Architecture](docs/REDIS_ARCHITECTURE.md)
