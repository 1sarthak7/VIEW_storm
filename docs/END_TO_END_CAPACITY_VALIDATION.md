# End-to-End Staged Capacity Validation Methodology

## 1. Staged Progression Framework

Capacity validation is conducted through a progressive, 10-stage execution ladder. Each stage tests a distinct scaling boundary and requires an independent preflight check:

```
[Smoke (10)] ----> [Baseline (100)] ----> [Small (1,000)] ----> [Medium (5,000)]
                                                                        |
                                                                        v
[High Capacity (50,000)] <---- [Extended (25,000)*] <---- [Large (10,000)]
         |
         v
[Extreme (100,000)*] ----> [Massive (150,000)*] ----> [Target (200,000)*]

(* Requires explicit operator cryptographic approval)
```

Advancement to higher stages is strictly forbidden if the previous stage breaches SLA thresholds or triggers an automated abort.

---

## 2. Precise Duration Semantics

To ensure rigorous benchmarking integrity, ViewStorm measures duration in explicit segments:

```
Concurrency
    ^
    |                       +---------------------------------------+ (Target: 200,000 Users)
    |                      /|                                       |\
    |                     / |                                       | \
    |                    /  |                                       |  \
    |                   /   |                                       |   \
    |                  /    |                                       |    \
    |                 /     |                                       |     \
  0 +----------------+------+---------------------------------------+------+----> Time
     <-- Ramp-Up ---><Stab-><------- Steady-State (1,800s) --------><Ramp->
     (Spawn: 2500/s) (10-30s)                                        Down
```

### Measured Intervals
1. **Ramp-Up Duration ($T_{\text{ramp}}$)**: Time spent spawning virtual users:
   $$T_{\text{ramp}} = \frac{U_{\text{target}}}{\text{Spawn Rate}}$$
   *(For Target 200,000 users at 2,500/s: $T_{\text{ramp}} = 80\text{ seconds}$).*
2. **Stabilization Duration ($T_{\text{stab}}$)**: Buffer window (10–30s) allowing worker TCP connection pools and Redis caches to settle.
3. **Steady-State Measurement Duration ($T_{\text{steady}}$)**: The official SLA measurement interval. **Ramp-up time is NEVER counted as steady-state time.** For the Target 200K profile, steady-state duration is certified at **1,800 seconds (30 minutes)**.
4. **Ramp-Down Duration ($T_{\text{down}}$)**: Graceful disconnect window allowing pending playback events to flush.

---

## 3. Workload Shaping: Concurrency vs. Request Throughput

Concurrent virtual users ($U$) and HTTP requests per second ($\text{RPS}$) are fundamentally separate workload dimensions:

$$\text{RPS} = \frac{U}{\text{Viewer Event Interval}}$$

### ViewStorm Viewer Behavior Model
- Each virtual viewer represents an active video playback session.
- Synthetic viewers emit heartbeat playback progress events every $10\text{ seconds}$ on average (configured between $8.0\text{s}$ and $12.0\text{s}$ with Gaussian jitter).
- At **200,000 concurrent virtual users**, the expected steady-state ingestion rate is:
  $$\text{Target RPS} = \frac{200,000}{10\text{s}} = \mathbf{20,000\text{ HTTP Req/s}}$$
  $$\text{Requests per Viewer per Second} = \mathbf{0.10\text{ req/viewer/s}}$$

ViewStorm explicitly tracks and persists both metrics to prevent turning a concurrency test into an uncalibrated packet flood.

---

## 4. Automated Safety Abort Guardrails

During every benchmark run, the background monitor evaluates telemetry every $2\text{ seconds}$:
1. **Error Rate Spike**: If real-time failure rate exceeds $2.5\times$ SLA threshold (or $>12.0\%$ absolute), execution is halted immediately.
2. **Memory Exhaustion**: If available system memory drops below $300\text{ MB}$, the runner halts to prevent kernel OOM-killer deadlocks.
3. **Emergency Stop**: If an operator activates the global kill-switch, SIGTERM is dispatched immediately to all runner processes.
