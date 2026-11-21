# ViewStorm Frontend Architecture & Developer Guide

## 1. Overview & Stack

The ViewStorm Frontend is a dark-first developer dashboard for distributed traffic simulation, real-time telemetry observation, cluster health diagnostics, and load-generator swarm management.

### Technology Stack
- **Framework**: React 19 + TypeScript (Strict Mode)
- **Bundler & Tooling**: Vite 6
- **Styling**: Tailwind CSS 3.4 (Dark-first palette, Plus Jakarta Sans & JetBrains Mono typography)
- **Routing**: React Router 7 (`react-router-dom`)
- **State & Server Cache**: TanStack Query 5 (`@tanstack/react-query`) with adaptive polling
- **Forms & Validation**: React Hook Form 7 + Zod 3.24
- **Charts & Data Visualization**: Recharts 2.15
- **Icons**: Lucide React
- **Testing**: Vitest + React Testing Library + JSDOM

---

## 2. Application Layout & Navigation

```
+--------------------------------------------------------------------------------------------------+
|                                    Top Navigation Bar                                            |
| [Page Title & Breadcrumb]                 [Cluster Health: API ● | Redis ☵ | PostgreSQL 🗄] [v1.0] |
+---------------+----------------------------------------------------------------------------------+
|               |                                                                                  |
|   Sidebar     |   Main Dashboard View Outlet                                                     |
|               |                                                                                  |
| ⚡ ViewStorm   |   • Overview Dashboard (Cluster KPIs, health probes, recent runs)                |
|               |   • Simulations (List, filter, create wizard, start/stop actions)                |
| 📈 Overview   |   • Simulation Details (Real-time charts, KPIs, worker allocations)               |
| 📑 Simulations |   • Worker Nodes (Swarm grid, hardware specs, capacity, detail drawer)           |
| 🖥 Worker Nodes|   • Performance Analytics (Multi-run side-by-side comparison & charts)           |
| 📊 Analytics   |   • Simulation Reports (Historical table, metrics breakdown, JSON/CSV exports)   |
| 📋 Reports     |   • Settings & Diagnostics (Infrastructure probe, version audit, polling rates) |
| ⚙ Settings    |                                                                                  |
|               |                                                                                  |
| [⇦ Collapse]  |                                                                                  |
+---------------+----------------------------------------------------------------------------------+
```

---

## 3. Real-Time Telemetry & Adaptive Polling

The dashboard connects to live FastAPI backend endpoints without fabricating mock counters:

| Entity | Endpoint | Polling Interval | Behavior |
|---|---|---|---|
| **Cluster Health** | `GET /api/v1/health` | 5,000 ms | Probes live Redis & PostgreSQL connectivity |
| **Simulations List** | `GET /api/v1/runs` | 4,000 ms | Refetches active status transitions |
| **Active Run Details** | `GET /api/v1/runs/:id` | 2,000 ms | Polls while `running`, pauses when `completed` / `stopped` |
| **Live Statistics** | `GET /api/v1/runs/:id/stats` | 2,000 ms | Real-time Redis event counters & calculated RPS |
| **Time-Series Metrics** | `GET /api/v1/runs/:id/metrics` | 2,000 ms | Periodic snapshots of RPS, latencies (P50/P95/P99), active viewers |
| **Worker Allocations** | `GET /api/v1/runs/:id/workers` | 2,500 ms | Displays assigned users and active status per distributed node |
| **Worker Swarm** | `GET /api/v1/worker-nodes` | 5,000 ms | Reflects active Redis leases and hardware health |

---

## 4. Frontend Security & Credential Isolation

- **Zero Secret Exposure**: Neither worker authentication tokens nor database passwords are included or exposed in browser bundles.
- **Explicit CORS**: The FastAPI backend restricts Cross-Origin Resource Sharing strictly to explicit authorized dashboard origins (`http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:3000`).
- **Input Sanitization & Boundary Validation**: Zod schemas validate user limits client-side (local runs capped at 1,000 virtual users; distributed runs verified against active worker capacity) before dispatching API mutations.

---

## 5. Development & Production Commands

### Installation
```bash
cd frontend
npm install
```

### Local Development Server
```bash
npm run dev
# Starts Vite dev server at http://localhost:5173
```

### Run Frontend Automated Tests
```bash
npm test
# Executes Vitest test suite with JSDOM
```

### Production Build
```bash
npm run build
# Compiles TypeScript and packages production assets into dist/
```

### Docker Deployment
```bash
docker compose up -d frontend
# Serves optimized production build via Nginx on port 3000
```
