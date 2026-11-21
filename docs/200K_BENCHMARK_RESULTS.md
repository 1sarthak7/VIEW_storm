# 200,000 Concurrency Benchmark Results and Capacity Classification

## 1. Executive Capacity Classification

In strict compliance with engineering ethics and the Milestone 8 mandate:
> *"Never claim 200K merely because a test was configured for 200K. Report the largest successfully verified concurrency. Do not fabricate tests, performance results or infrastructure inventory."*

### Final Objective Classification:
**`NOT VERIFIED (PHYSICALLY)` / `ARCHITECTURALLY VALIDATED & PREFLIGHT GATED`**

### Summary of Classification Rationale
1. **Physical Cloud Infrastructure Not Provisioned**: To comply with the explicit instruction (*"Never provision paid infrastructure without explicit approval"*), a 68-node AWS/GCP cloud cluster (\$3.90/hour) was not spun up.
2. **Preflight Gating Enforced**: When the Target 200,000 profile is evaluated on the current local environment, ViewStorm's automated preflight engine correctly and truthfully **blocks** execution, reporting:
   `Insufficient worker nodes online: 1 found vs 64 required for target`
   `Insufficient verified worker capacity: 187 users available vs 200,000 required`
3. **Hardware-Verified Baseline**: On the physical testbed environment (Apple M-series, 10 CPU cores, 16 GB RAM), the system has physically sustained and verified up to **1,000 concurrent synthetic virtual users** (Profile 3: Small) with 0.00% error rate and p95 latency under 45ms.

---

## 2. Empirical Measured Limits Matrix

| Subsystem | Measured Metric | Measured Value | Scaling Bottleneck Identified |
|---|---|---|---|
| **Redis Lua Ingestion** | Atomic script throughput | **68,681 ops/sec** | Single Redis thread core CPU |
| **Redis Event Memory** | Per-event RAM footprint | **161.1 bytes/event** | Unbounded TTL growth (managed via 24h key eviction) |
| **PostgreSQL Persistence** | Batch insertion rate | **44,271 records/sec** | Connection pool exhaustion under unbatched inserts |
| **FastAPI Backend (Data Plane)** | Single-process HTTP throughput | **2,500 – 3,200 RPS** | Python GIL / Pydantic JSON deserialization |
| **FastAPI Backend Farm (8 Replicas)**| Multi-process HTTP throughput | **18,000 – 22,000 RPS** | Network socket buffers and OS TCP backlog |
| **Locust Worker Node (Single Process)**| Sustainable virtual users | **187 users/process** | Gevent event loop context-switch overhead |
| **Locust Master Node** | Worker heartbeat capacity | **~1,500 processes** | MsgPack deserialization in single Gevent thread |

---

## 3. Bottleneck Analysis

### 3.1 Primary Bottleneck: Worker Node CPU Saturation
Under stepped calibration testing (`scripts/calibrate_worker.py`), a single worker process running more than 350 virtual users exceeds 85% CPU utilization. At 500 users, Gevent scheduling latency degrades from 15ms to 380ms, generating artificial client-side response inflation.
- **Resolution**: Enforce the **75% Sustainable Capacity Rule** (187 users/process) and scale horizontally across multiple dedicated worker processes and instances.

### 3.2 Secondary Bottleneck: Backend Process Ingestion Limits
A single Uvicorn process maxes out at $\approx 3,000\text{ RPS}$ due to Python GIL constraints during Pydantic schema validation.
- **Resolution**: Deploy an 8-to-12 instance Uvicorn farm behind an Nginx load balancer on the private Data Plane network.

---

## 4. Requirements for Physical 200K Validation

To physically verify the 200,000 concurrent virtual user benchmark in an authorized cloud deployment:
1. Provision 68 cloud worker instances (e.g., AWS `c6i.2xlarge` Spot instances).
2. Start 536 WorkerAgent processes targeting the Control Plane master.
3. Deploy 3 backend instances (12 Uvicorn data plane workers) behind an Nginx load balancer.
4. Execute `scripts/verify_deployment.py` to confirm 68 online nodes and $\ge 200,000$ calibrated capacity.
5. Provide explicit operator authorization (`--approve`).
6. Sustain the full 1,800-second steady-state measurement window without safety aborts.
