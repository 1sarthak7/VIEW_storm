# Standardized Benchmark Profiles and Execution Guardrails

## 1. The 9 Milestone 7 Benchmark Profiles

ViewStorm establishes 9 standardized benchmark profiles spanning from local sanity verification to massive distributed stress tests.

| Profile | Name | Users | Spawn Rate | Duration | Execution Mode | SLA Max Errors | SLA Max p95 | Explicit Approval | Min Workers |
|---|---|---|---|---|---|---|---|---|---|
| **1** | `smoke` | 10 | 2.0 /s | 30s | Local | 1.0% | 500 ms | No | 1 |
| **2** | `baseline` | 100 | 10.0 /s | 60s | Local | 2.0% | 1,000 ms | No | 1 |
| **3** | `small` | 1,000 | 50.0 /s | 120s | Local | 3.0% | 1,500 ms | No | 1 |
| **4** | `medium` | 5,000 | 100.0 /s | 180s | Distributed | 5.0% | 2,000 ms | No | 2 |
| **5** | `large` | 10,000 | 250.0 /s | 300s | Distributed | 5.0% | 2,500 ms | No | 4 |
| **6** | `extended` | 25,000 | 500.0 /s | 600s | Distributed | 5.0% | 3,000 ms | **Yes** | 8 |
| **7** | `high_capacity`| 50,000 | 1,000.0 /s | 900s | Distributed | 5.0% | 4,000 ms | **Yes** | 16 |
| **8** | `extreme` | 100,000 | 2,000.0 /s | 1,200s | Distributed | 5.0% | 5,000 ms | **Yes** | 32 |
| **9** | `target` | 200,000 | 2,500.0 /s | 1,800s | Distributed | 5.0% | 5,000 ms | **Yes** | 64 |

---

## 2. Multi-Stage Ramp Schedules

Rather than instantaneously applying full concurrency, larger profiles incorporate staged ramp schedules to detect tipping points before cascade failure:
- **Warmup Stage**: 10–25% of target users to establish TCP pools and JIT caches.
- **Ramp Stages**: Progressive increases in user count to observe queue depth.
- **Stabilization Stage**: Full load sustained for the duration of the measurement window.

---

## 3. Operator Authorization Protocol

Profiles generating $\ge 25,000$ virtual users (`extended`, `high_capacity`, `extreme`, `target`) impose severe stress on network and infrastructure. To prevent accidental triggering:
1. `BenchmarkRunRequest.approval_confirmed` must be explicitly set to `True`.
2. The user invoking the benchmark must possess the `admin` role.
3. The dashboard presents an explicit acknowledgment checkbox requiring the operator to confirm network and infrastructure authorization.
4. If approval is missing, the API rejects the request with HTTP 403 Forbidden.

---

## 4. Automated Safety Abort Guardrails

During execution, the background benchmark monitor queries live telemetry and immediately halts execution upon detecting any of the following conditions:

```
[Active Benchmark Execution]
              |
              +---> Error Rate > 2.5x Profile SLA (or >12.0%) ----> [AUTO-ABORT]
              |
              +---> Host Available RAM < 300 MB                ----> [AUTO-ABORT]
              |
              +---> Emergency Stop Kill Switch Fired           ----> [IMMEDIATE HALT]
              |
              +---> Normal Completion Window Reached           ----> [PERSIST & VERDICT]
```

When an abort occurs:
- `BenchmarkResult.abort_reason` is set (e.g., `ERROR_RATE_EXCEEDED`, `LOW_MEMORY_ABORT`).
- `BenchmarkResult.passed_thresholds` is set to `False`.
- Master and worker processes are safely shut down without hanging orphaned sockets.
