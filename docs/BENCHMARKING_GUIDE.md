# ViewStorm Standardized Benchmarking Framework

The ViewStorm Benchmarking Framework provides automated, reproducible performance experiments with defined SLA thresholds and automated safety abort guardrails.

---

## 1. Predefined Benchmark Profiles

| Profile Name | Virtual Users | Spawn Rate | Duration | Target Mode | Max Error Rate | Max p95 Latency | Description |
|---|---|---|---|---|---|---|---|
| **`smoke`** | 10 | 2.0/s | 30s | Local | 1.0% | 500ms | Sanity check verifying API ingestion and pipeline connectivity |
| **`baseline`** | 50 | 5.0/s | 60s | Local | 2.0% | 1,000ms | Single-node baseline under typical operational load |
| **`medium`** | 200 | 20.0/s | 120s | Local | 5.0% | 2,000ms | Stress simulation assessing local concurrency limits |
| **`high`** | 500 | 50.0/s | 180s | Local | 5.0% | 3,000ms | High-concurrency stress test testing saturation boundaries |
| **`distributed`** | 1,000 | 100.0/s | 300s | Distributed | 5.0% | 5,000ms | Multi-node cluster benchmark orchestrating workers over ZeroMQ |

---

## 2. Automated SLA Guardrails & Safety Aborts

During a benchmark execution, the `BenchmarkService` background monitor inspects live throughput, error rate, and response latencies:
- **Runaway Error Detection**: If the measured error rate exceeds `max_error_rate_pct * 3.0` (or >15%), the benchmark runner is automatically aborted immediately.
- **Safety Abort**: The simulation subprocess is gracefully terminated, the run is marked aborted, and the SLA evaluation flags `passed_thresholds = False` with the exact breach reason.

---

## 3. Comparative Regression Analysis

Benchmark results are persistently stored in the `benchmark_results` PostgreSQL table. The comparison engine analyzes performance deltas between any baseline run and candidate run:

$$\Delta RPS\% = \frac{RPS_{candidate} - RPS_{baseline}}{RPS_{baseline}} \times 100$$

$$\Delta p95\% = \frac{p95_{candidate} - p95_{baseline}}{p95_{baseline}} \times 100$$

### Performance Verdicts
- **`IMPROVEMENT`**: RPS improved by >10% with p95 latency delta $\le 5\%$ and error rate delta $\le 0.5\%$.
- **`REGRESSION`**: p95 latency degraded by >15% or error rate increased by >2% or throughput collapsed by >15%.
- **`STABLE`**: Performance metrics remain within acceptable operational variance.
