# ViewStorm Reliability, Lifecycle Reconciliation & Emergency Stop

This document specifies the fault tolerance, crash recovery, and emergency halt mechanisms implemented in ViewStorm.

---

## 1. Startup Lifecycle Reconciliation

When a backend process terminates abruptly (e.g. power failure, container restart, OOM event), simulation runs previously in `starting`, `running`, or `waiting_for_workers` states could be left stranded in PostgreSQL as "zombies".

### The Reconciliation Hook
On application boot (`lifespan` in `app/main.py`), the `LifecycleReconciliationService` scans the database for any active runs:

```python
async def reconcile_interrupted_runs(self, db: AsyncSession) -> int:
    zombie_statuses = ["running", "starting", "waiting_for_workers"]
    stmt = select(SimulationRun).where(SimulationRun.status.in_(zombie_statuses))
    ...
```

For every orphaned simulation run discovered:
1. Status is transitioned to `INTERRUPTED`.
2. `finished_at` timestamp is set to current UTC time.
3. `error_message` records: `"Simulation interrupted due to backend restart or ungraceful process termination."`
4. The event is logged at `WARNING` level with run ID and previous status.

---

## 2. Global Emergency Stop (Kill Switch)

The Emergency Stop subsystem provides an immediate halt across all running simulations, local Locust workers, and distributed master-worker clusters.

### Architecture

```
Operator Trigger (UI / API)
         │
         ▼
POST /api/v1/admin/emergency-stop
         │
         ├──► Redis Flag: viewstorm:emergency_stop:active = 1
         ├──► Prometheus Metric: viewstorm_emergency_stop_active = 1
         ├──► Terminate all local Locust runner subprocesses
         ├──► Terminate all distributed Locust master processes
         └──► PostgreSQL: Transition all RUNNING runs to INTERRUPTED
```

### Locking Behavior
While emergency stop is engaged:
- `POST /api/v1/runs` is rejected with `HTTP 423 Locked`.
- `POST /api/v1/runs/{id}/start` is rejected with `HTTP 423 Locked`.
- `POST /api/v1/benchmarks/run` is rejected with `HTTP 423 Locked`.
- The frontend analytics dashboard renders a prominent, persistent red emergency warning banner across all pages.

### Clearing Emergency Stop
Only operators with the `admin` role can clear an emergency stop:
- `POST /api/v1/admin/emergency-stop/clear`
- Clears Redis keys, sets Prometheus gauge back to 0, and restores simulation command capabilities.
