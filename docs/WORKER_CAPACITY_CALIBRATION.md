# Worker Node Capacity Calibration Methodology

## 1. Overview and Problem Statement

Distributed load generation requires understanding the physical operating limits of each worker node. Running excessive virtual users on a worker causes:
- Gevent event loop starvation, leading to artificial client-side latency inflation.
- Socket file descriptor exhaustion (`EMFILE`).
- High CPU context-switching overhead rather than actual request generation.
- Client CPU saturation skewing server-side response measurements.

To ensure benchmark integrity, ViewStorm introduces the **Worker Capacity Calibration Framework** (`WorkerCalibrationService` and `scripts/calibrate_worker.py`).

---

## 2. Stepped Ramp-Up Methodology

The calibration service executes a progressive stepped workload against the local or cluster loopback target, stepping through distinct user tiers:

$$\text{Steps} = [10, 25, 50, 100, 250, 500, \dots]$$

Each step runs for a controlled test window ($15\text{s}$ warmup, $30\text{s}$ measurement). During each step, system performance counters are sampled at $1\text{s}$ intervals:
- Host CPU utilization (`psutil.cpu_percent()`)
- Process CPU utilization
- Available host memory percentage (`psutil.virtual_memory().available / total`)
- Client-measured HTTP error rate
- Request latency percentiles (p50, p95, p99)
- Achieved requests per second (RPS)

---

## 3. Saturation and Failure Criteria

A worker node is classified as **saturated** at a given tier if *any* of the following invariant thresholds are breached:

| Metric | Saturation Threshold | Rationale |
|---|---|---|
| **Host CPU Utilization** | $> 85.0\%$ | Prevents thread scheduling starvation in Python/Gevent |
| **Available RAM** | $< 15.0\%$ | Prevents OS paging and memory thrashing |
| **HTTP Error Rate** | $> 2.0\%$ | Client-side socket errors, drops, or HTTP timeouts |
| **Latency p95 Degradation** | $> 1,500\text{ ms}$ | Indicates event queue backup or TCP backlog saturation |

If saturation occurs at step $k$, the calibration engine halts the stepped ramp immediately and records the saturation reason (e.g., `CPU_SATURATION`, `MEMORY_SATURATION`, `ERROR_SPIKE`, `LATENCY_DEGRADATION`).

---

## 4. The 75% Sustainable Capacity Rule

To provide high-reliability headroom and prevent cascading worker dropouts during extended distributed simulations, the worker node's certified maximum capacity is calculated as:

$$\text{Recommended Capacity} = \lfloor 0.75 \times \text{Max Stable Virtual Users} \rfloor$$

### Example Calibration Matrix
On an Apple M-series / 10-core 16GB RAM node:
- 10 users: CPU 4.2%, RAM 48% free, p95 8ms, error 0% $\rightarrow$ **PASS**
- 50 users: CPU 12.8%, RAM 47% free, p95 14ms, error 0% $\rightarrow$ **PASS**
- 100 users: CPU 24.1%, RAM 47% free, p95 22ms, error 0% $\rightarrow$ **PASS**
- 250 users: CPU 56.4%, RAM 46% free, p95 48ms, error 0% $\rightarrow$ **PASS**
- 500 users: CPU 88.2%, RAM 45% free, p95 380ms, error 0.4% $\rightarrow$ **SATURATED (CPU > 85%)**

Max Stable Users: **250**.  
Certified Recommended Capacity: $\lfloor 250 \times 0.75 \rfloor = \mathbf{187\text{ users/process}}$.

---

## 5. Storage and Preflight Enforcement

Calibration outcomes are persisted in PostgreSQL (`worker_calibrations` table):
- `worker_id` / `hostname`
- `max_stable_users`
- `recommended_capacity`
- `cpu_saturation_pct`
- `memory_saturation_pct`
- `saturation_reason`
- `tested_at`

During benchmark preflight checks, ViewStorm computes:
$$\text{Total Cluster Capacity} = \sum_{w \in \text{Online Workers}} w.\text{recommended\_capacity}$$
If $\text{Total Cluster Capacity} < \text{Profile Required Users}$, preflight verification fails and execution is blocked.
