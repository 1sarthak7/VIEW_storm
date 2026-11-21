# Worker Fleet Operations and Capacity Management

## 1. Physical Node vs. Worker Process Accounting

A critical requirement of distributed load testing is distinguishing between:
1. **Physical / Virtual Worker Nodes ($N_{\text{nodes}}$)**: Independent compute instances (e.g. cloud VMs, bare-metal servers) with distinct IP addresses, network interfaces, and memory pools.
2. **Locust Worker Processes ($P_{\text{workers}}$)**: Individual Python/Gevent operating system processes spawned on a worker node to generate traffic.

Because Python's Global Interpreter Lock (GIL) limits a single Python process to 1 CPU core:
- A node with 8 CPU cores typically runs **8 worker processes**.
- For ViewStorm's 200,000 virtual-user profile:
  - Minimum Physical Nodes: **64 instances** (to avoid network interface saturation and OS socket file descriptor bottlenecks).
  - Minimum Worker Processes: **536 processes** ($\approx 8\text{ processes/node} \times 67\text{ nodes}$).

ViewStorm's models (`LoadGeneratorNode`, `BenchmarkProfile`) track both counts explicitly. Never treat node count and process count as interchangeable.

---

## 2. Capacity-Aware Proportional Allocation

Workload is distributed according to each node's certified capacity using the **75% Sustainable Capacity Rule**:

$$\text{Certified Capacity}_i = \lfloor 0.75 \times \text{Max Stable Virtual Users}_i \rfloor$$

When a simulation requests $U_{\text{total}}$ users across $K$ registered online workers:
$$\text{Assigned Users}_i = \left\lfloor U_{\text{total}} \times \frac{\text{Capacity}_i}{\sum_{j=1}^K \text{Capacity}_j} \right\rfloor$$
Any remainder from integer division is deterministically allocated to workers with the largest fractional remainder.

### Strict Invariant
$$\sum_{i=1}^K \text{Assigned Users}_i = U_{\text{total}}$$
No worker is ever assigned more users than its certified sustainable capacity.

---

## 3. Heartbeat Lifecycle and Automatic Eviction

Workers send heartbeats every $5\text{ seconds}$ to `POST /api/v1/worker-nodes/heartbeat`:
- Reports real-time CPU utilization, RAM utilization, and active process count.
- Sets a Redis lease with a $30\text{-second TTL}$ (`viewstorm:workers:{worker_id}:lease`).
- If a worker misses heartbeats for $>30\text{ seconds}$, `WorkerRegistryService` marks the node as `OFFLINE` and evicts it from future workload allocations.

---

## 4. Graceful Worker Draining and Rolling Upgrades

To upgrade worker nodes without aborting active runs or corrupting historical records:
1. **Drain Mode**: Mark the node status as `DRAINING` in the database. Active simulations continue running until completion, but the node will receive zero new simulation assignments.
2. **Process Teardown**: Issue `SIGTERM` to local worker subprocesses after simulation finalization.
3. **Software Update**: Pull updated git commits, update Python virtual environment, and restart `viewstorm-worker-agent`.
4. **Re-registration**: The worker agent registers with the Control Plane with updated version metadata (`software_version`, `locust_version`, `build_identifier`) and resumes `ONLINE` status.
