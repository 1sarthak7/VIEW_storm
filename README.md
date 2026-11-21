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

5. **Standardized Benchmarking Framework**:
   - Predefined profiles: `smoke`, `baseline`, `medium`, `high`, `distributed`.
   - Continuous SLA threshold monitoring with automated safety aborts for runaway error rates or latency degradation.
   - Automated regression analysis computing $\Delta RPS\%$, $\Delta p95\%$, and performance verdicts (`IMPROVEMENT`, `REGRESSION`, `STABLE`).

6. **React 19 Analytics Dashboard**:
   - Route-based code splitting with `React.lazy` and manual vendor chunking, achieving a **75% reduction** in initial bundle size.
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
Default administrator account: `admin` / `ViewStormAdmin2026!`.

### 4. Running Distributed Workers
```bash
cd worker-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m worker_agent.main --coordinator-url http://localhost:8000 --capacity 500
```

---

## Automated Verification

### Backend Test Suite (64 Tests)
```bash
cd backend
pytest tests -v
```

### Frontend Test Suite & Bundle Verification
```bash
cd frontend
npm test
npm run typecheck
npm run build
```

---

## Documentation Index
- [Security & RBAC](docs/SECURITY.md)
- [Reliability & Emergency Stop](docs/RELIABILITY_AND_RECOVERY.md)
- [Benchmarking Guide](docs/BENCHMARKING_GUIDE.md)
- [Frontend Optimization](docs/FRONTEND_OPTIMIZATION.md)
- [Distributed Architecture](docs/DISTRIBUTED_ARCHITECTURE.md)
- [Database Architecture](docs/DATABASE_ARCHITECTURE.md)
- [Redis Architecture](docs/REDIS_ARCHITECTURE.md)
