# ViewStorm Worker Agent Specification

## 1. Overview

`viewstorm-agent` is an autonomous background daemon engineered to run on distributed load generator instances. It bridges the central FastAPI control plane and local Locust worker subprocesses without exposing any open listening ports on the host.

---

## 2. Agent Execution Flow

```mermaid
sequenceDiagram
    participant Agent as WorkerAgent
    participant API as FastAPI Control Plane
    participant Redis as Redis Leases
    participant Worker as Locust Worker Subprocess
    participant Master as Locust Master (:5557)

    Agent->>API: POST /api/v1/worker-nodes/register
    API->>Redis: SET viewstorm:workers:{id}:heartbeat (TTL 30s)
    API-->>Agent: 201 Created (worker_id)

    loop Heartbeat (every 5s)
        Agent->>API: POST /api/v1/worker-nodes/heartbeat (CPU, RAM, active workers)
        API->>Redis: EXPIRE viewstorm:workers:{id}:heartbeat 30s
        API-->>Agent: 200 OK (should_stop_run: bool)
    end

    loop Poll Assignment (every 2s)
        Agent->>API: GET /api/v1/worker-nodes/{id}/assignments
        API-->>Agent: 200 OK (has_assignment: bool)
    end

    Note over Agent: Assignment received
    Agent->>Worker: fork locust --worker --master-host ...
    Agent->>API: POST /api/v1/worker-nodes/{id}/assignments/{run_id}/acknowledge
    Worker->>Master: ZeroMQ Connection (:5557)
    Master->>Worker: Command spawn users
    Worker->>API: Ingest synthetic playback events
```

---

## 3. CLI Options & Configuration

The agent can be started using the CLI entrypoint:

```bash
python -m viewstorm_agent.main \
  --server-url "http://controlplane.internal:8000" \
  --token "viewstorm-secret-token" \
  --name "loadgen-us-east-01" \
  --capacity 500 \
  --locustfile "simulator/locustfile.py" \
  --log-level "INFO"
```

### Environment Variables
All options can also be provided through environment variables:
- `VIEWSTORM_SERVER_URL`: Base URL of the FastAPI backend.
- `VIEWSTORM_WORKER_AUTH_TOKEN`: Shared secret or per-node token.
- `VIEWSTORM_WORKER_NAME`: Node label.
- `VIEWSTORM_WORKER_CAPACITY`: Maximum users this instance can support.
- `VIEWSTORM_HEARTBEAT_INTERVAL`: Heartbeat interval (default: `5.0` seconds).
- `VIEWSTORM_POLL_INTERVAL`: Workload polling frequency (default: `2.0` seconds).

---

## 4. Failure Recovery & Orphaned Process Handling

- **Control Plane Disconnect**: If the backend is unreachable during registration or heartbeat, the agent exponentially backs off and retries while keeping existing workers alive until the run's duration completes.
- **Run Abortion**: If a user cancels a simulation via the UI or API (`/api/v1/runs/{id}/stop`), the subsequent heartbeat response returns `should_stop_run=True`. The agent immediately sends `SIGTERM` to the local worker process and cleans up.
- **Crash Recovery**: If the agent process crashes, the Redis lease expires within 30 seconds. The backend marks the node as `stale` and reallocates pending assignments if necessary.
