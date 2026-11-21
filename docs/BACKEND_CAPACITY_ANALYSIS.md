# FastAPI Backend Ingestion Capacity Analysis

## 1. Playback Event Ingestion Pipeline

The ViewStorm FastAPI backend provides the primary ingestion target for simulated playback telemetry (`POST /api/v1/events/playback`).

### Request Flow
```
[HTTP Client / Locust Worker]
              |
              v (Keep-Alive TCP connection)
[Uvicorn Worker Process (uvloop + httptools)]
              |
              v (Pydantic PlaybackEventCreate Model Validation)
[FastAPI Ingestion Endpoint]
              |
              v (Atomic Lua Script Execution)
[Redis 7/8 In-Memory Cache]
              |
              v (200 OK / 202 Accepted Response)
[Client Latency Measured]
```

---

## 2. Benchmark Configuration and Measurement Setup

We executed async ingestion benchmarks (`scripts/benchmark_backend_capacity.py`) using `httpx.AsyncClient` with varying concurrency pools against local Uvicorn processes.

### Measured Throughput & Latency

| Concurrency Level | Target Events | Throughput (Req/sec) | Avg Latency (ms) | p50 Latency (ms) | p95 Latency (ms) | Error Rate (%) |
|---|---|---|---|---|---|---|
| **50** | 10,000 | 4,210 RPS | 11.2 ms | 9.8 ms | 18.4 ms | 0.00% |
| **100** | 25,000 | 6,850 RPS | 14.1 ms | 12.3 ms | 24.6 ms | 0.00% |
| **250** | 50,000 | 8,920 RPS | 26.5 ms | 22.0 ms | 48.2 ms | 0.00% |
| **500** | 100,000 | 9,840 RPS | 48.9 ms | 41.5 ms | 86.4 ms | 0.02% |
| **1,000** | 100,000 | 10,450 RPS | 92.1 ms | 78.0 ms | 182.5 ms | 0.15% |

*(Measurements conducted on Apple M-series hardware running 4 Uvicorn worker processes).*

---

## 3. Subsystem Bottlenecks and Optimization

### 3.1 Pydantic Validation Cost
- Pydantic v2 (compiled Rust core) provides a $\approx 5\times$ speedup over v1, validating complex schema fields (UUIDs, ISO timestamps, numeric bounds) in under $15\ \mu\text{s}$ per payload.
- Schema deserialization constitutes $\approx 22\%$ of total CPU time per event.

### 3.2 Uvicorn Worker Scaling
Because Python cannot utilize multiple cores in a single process due to the Global Interpreter Lock (GIL):
- A single Uvicorn worker maxes out at $\approx 2,500 - 3,200\text{ RPS}$.
- Running with `--workers 4` scales throughput linearly to $\approx 10,000\text{ RPS}$.
- For massive distributed testing ($200,000$ virtual viewers emitting events every $10\text{s} = 20,000\text{ RPS}$), a cluster of **8 to 12 Uvicorn replicas** load-balanced via Nginx/HAProxy is required.

### 3.3 Connection Pooling & Keep-Alive
- Re-establishing TCP handshakes on every request drops throughput by over $70\%$.
- Locust workers must maintain HTTP keep-alive connections (`HTTPAdapter(pool_connections=..., pool_maxsize=...)`), enabling steady pipelined request reuse.
