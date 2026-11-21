# ViewStorm — Milestone 8 Production Deployment Architecture

## 1. Executive Summary

Milestone 8 provides a production-grade, multi-machine deployment architecture for ViewStorm. It decouples the application into two logically independent operational planes:
1. **The Control Plane**: Hosts the React dashboard, authentication & RBAC, simulation orchestration, worker registry, standardized benchmarking engine, Prometheus scraping, and system of record.
2. **The Data Plane**: Hosts dedicated, horizontally scaled FastAPI playback event ingestion endpoints, high-throughput Redis Lua atomic pipelines, and target-side metric persistence.

This architecture ensures that even when the data plane is undergoing extreme traffic stress (up to 20,000+ requests/second across thousands of concurrent synthetic virtual viewers), the control plane remains 100% responsive for live observation, cluster management, and emergency-stop execution.

---

## 2. Architectural Topography

```
+----------------------------------------------------------------------------------------------------+
|                                    OPERATOR / PUBLIC NETWORK                                       |
|                                                                                                    |
|    Browser Clients / Operators                   Monitoring Dashboards (Prometheus/Grafana)         |
|              |                                                     |                               |
+--------------|-----------------------------------------------------|-------------------------------+
               | HTTPS (Port 443 / TLS)                              | Port 9090 (Restricted)
               v                                                     v
+----------------------------------------------------------------------------------------------------+
|                                  CONTROL PLANE HOST (10.10.1.0/24)                                 |
|                                                                                                    |
|   +--------------------------+       +-------------------------+       +-----------------------+   |
|   |   Nginx Reverse Proxy    | ----> |   ViewStorm Dashboard   |       |  Prometheus Metrics   |   |
|   |     (TLS Termination)    |       |     (React 19 / Vite)   |       |    (/metrics scraper) |   |
|   +-------------+------------+       +-------------------------+       +-----------+-----------+   |
|                 |                                                                  |               |
|                 v                                                                  |               |
|   +--------------------------------------------------------------------------------+-----------+   |
|   |                          FastAPI Control Plane (Port 8000)                                 |   |
|   |  - Simulation Lifecycle Orchestrator     - Standardized Benchmark Engine (9 Profiles)      |   |
|   |  - Ephemeral Admin Bootstrapper          - Worker Fleet Registry & Capacity Allocator      |   |
|   |  - Global Emergency Stop Controller      - SLA Guardrail & Safety Abort Loop               |   |
|   +---------------------+--------------------------------------------------+-------------------+   |
|                         |                                                  |                       |
|                         v                                                  v                       |
|   +-------------------------------------+                +-------------------------------------+   |
|   |      PostgreSQL 16 Database         |                |       Redis Coordination Cache      |   |
|   |   (Runs, Users, Calibrations,       |                |   (Worker Heartbeats, Leases,       |   |
|   |    Benchmarks, Metric Records)      |                |    Emergency Kill-Switch Active)    |   |
|   +-------------------------------------+                +-------------------------------------+   |
|                         ^                                                  ^                       |
+-------------------------|--------------------------------------------------|-----------------------+
                          |                                                  |
                          | (Internal Private Subnet)                        | (Internal Private Subnet)
                          |                                                  |
+-------------------------|--------------------------------------------------|-----------------------+
|                         |         DATA PLANE INGESTION FARM (10.10.2.0/24) |                       |
|                         |                                                  |                       |
|                         |         +-----------------------------+          |                       |
|                         |         |   Data Plane Load Balancer  | <---+    |                       |
|                         |         |      (Nginx / Port 8001)    |     |    |                       |
|                         |         +--------------+--------------+     |    |                       |
|                         |                        |                    |    |                       |
|                         |         +--------------+--------------+     |    |                       |
|                         |         |                             |     |    |                       |
|                         |         v                             v     |    |                       |
|                         |  +--------------+              +---------+--+--+ |                       |
|                         |  | Dataplane 1  |              | Dataplane 2   | |                       |
|                         |  | (4 Workers)  |              | (4 Workers)   | |                       |
|                         |  +-------+------+              +-------+-------+ |                       |
|                         |          |                             |         |                       |
|                         +----------+-----------------------------+         |                       |
|                                    | (High-Throughput Lua Atomic Pipeline) |                       |
|                                    +---------------------------------------+                       |
+----------------------------------------------------------------------------------------------------+
                                             ^
                                             | HTTP/1.1 Keep-Alive (Synthetic Playback Events)
                                             | Target Port 8001
                                             |
+--------------------------------------------|-------------------------------------------------------+
|                                    WORKER FLEET NETWORK (10.10.3.0/24)                             |
|                                                                                                    |
|    ZeroMQ Master Coordination (Ports 5557/5558) bound strictly to Private Network                  |
|                                                                                                    |
|   +---------------------------+       +---------------------------+       +--------------------+   |
|   |   Worker Machine 01       |       |   Worker Machine 02       |  ...  |  Worker Machine N  |   |
|   |   - WorkerAgent Daemon    |       |   - WorkerAgent Daemon    |       |  - WorkerAgent     |   |
|   |   - Calibrated 187 users  |       |   - Calibrated 187 users  |       |  - Calibrated      |   |
|   |   - Locust Worker Procs   |       |   - Locust Worker Procs   |       |  - Locust Worker   |   |
|   +---------------------------+       +---------------------------+       +--------------------+   |
+----------------------------------------------------------------------------------------------------+
```

---

## 3. Host and Subsystem Decoupling

| Plane / Subsystem | Primary Responsibilities | Network Scope | Compute Requirements |
|---|---|---|---|
| **Control Plane** | Dashboard, User RBAC, Run lifecycle, Worker registry, Benchmarks, Emergency Stop | Public HTTPS (443), Private Master (5557/5558) | 4–16 vCPU, 16–32 GB RAM |
| **Data Plane** | Playback event ingestion (`/api/v1/events/playback`), Pydantic validation, Redis Lua execution | Private Worker Net (8001) | Horizontally scaled (8–12 Uvicorn workers) |
| **Redis Cache** | Idempotency sets, atomic event counters, active viewer hyperloglogs | Private Data & Control Subnets | 8–16 GB RAM with `volatile-lru` |
| **PostgreSQL** | Persistent state of record, benchmark metadata, historical summaries | Private Control & Data Subnets | 4–16 vCPU, 16–64 GB RAM, SSD IOPS |
| **Worker Fleet** | Outbound synthetic load generation, hardware telemetry, Gevent event loops | Private Worker Subnet (VPN) | 68 physical instances / 536 worker processes (for 200k target) |

---

## 4. Operational Survivability Invariant

Under this architecture:
1. **Worker Network Isolation**: Synthetic traffic generated by workers never hits the Control Plane port 8000; all traffic is strictly directed to the Data Plane load balancer at port 8001.
2. **Control Loop Integrity**: Even if Data Plane ingestion instances reach 100% CPU saturation or queue events, the Control Plane processes remain idle and responsive (<25ms API response latency).
3. **Emergency Stop Guarantee**: Emergency stop triggers (`POST /api/v1/emergency/stop`) propagate via Redis keys and SIGTERM signals within milliseconds, immediately terminating load generation regardless of Data Plane queuing.
