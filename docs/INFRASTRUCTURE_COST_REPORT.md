# ViewStorm Infrastructure Sizing and Cost Report (200,000 Concurrency Target)

## 1. Sizing Breakdown for 200,000 Concurrent Virtual Users

Based on the empirical measurements established in Milestones 7 & 8, sustaining 200,000 concurrent virtual viewers generating synthetic traffic every 10 seconds ($20,000\text{ RPS}$) requires the following distributed infrastructure:

### 1.1 Worker Fleet (Load Generation Tier)
- **Target Concurrency**: 200,000 virtual users.
- **Worker Density**: 3,000 users per 8-core instance ($\approx 375\text{ users/process}$ max, $187\text{ users/process}$ certified sustainable).
- **Required Compute**: **68 instances** (AWS `c6i.2xlarge` — 8 vCPU, 16 GB RAM each).
- **Total Worker Resources**: **544 vCPU, 1,088 GB RAM**.

### 1.2 Control Plane (Locust Master & Orchestration Tier)
- **ZeroMQ Streams**: 544 connected worker reporting streams.
- **Required Compute**: **1 instance** (AWS `c6i.4xlarge` — 16 vCPU, 32 GB RAM, 12.5 Gbps network).

### 1.3 Data Plane (Playback Ingestion Farm)
- **Required Throughput**: 20,000 RPS steady-state (30,000 RPS burst headroom).
- **Uvicorn Replicas**: 12 worker processes (each handling $\approx 2,500\text{ RPS}$).
- **Required Compute**: **3 instances** (AWS `c6i.xlarge` — 4 vCPU, 8 GB RAM) behind an Application Load Balancer or Nginx reverse proxy.

### 1.4 In-Memory Ingestion Tier (Redis)
- **Memory Footprint**: 161.1 bytes/event $\times$ 1,200,000 events in 10-minute active window $\approx 1.2\text{ GB RAM}$.
- **Throughput**: 20,000 Lua ops/sec ($\approx 29\%$ of single Redis thread capacity).
- **Required Provisioning**: AWS ElastiCache for Redis (`cache.m6g.large` — 2 vCPU, 6.38 GB RAM, primary + replica).

### 1.5 Database Persistence Tier (PostgreSQL)
- **Batch Metric Ingestion**: 1 metric sample record per second, plus aggregated summaries.
- **Required Provisioning**: AWS RDS for PostgreSQL (`db.m6g.xlarge` — 4 vCPU, 16 GB RAM, 500 GB gp3 SSD storage).

---

## 2. Infrastructure Cost Modeling (AWS US-East)

### Hourly Operational Cost During a Benchmark Experiment

| Component | AWS Instance Type | Count | On-Demand Rate | Spot Rate | Hourly Cost (Spot) |
|---|---|---|---|---|---|
| **Worker Fleet** | `c6i.2xlarge` | 68 | \$0.340 / hr | \$0.034 / hr | \$2.31 / hr |
| **Locust Master** | `c6i.4xlarge` | 1 | \$0.680 / hr | \$0.680 / hr (On-Demand) | \$0.68 / hr |
| **Data Plane Farm** | `c6i.xlarge` | 3 | \$0.170 / hr | \$0.170 / hr (On-Demand) | \$0.51 / hr |
| **ElastiCache Redis** | `cache.m6g.large` | 1 | \$0.136 / hr | \$0.136 / hr | \$0.14 / hr |
| **RDS PostgreSQL** | `db.m6g.xlarge` | 1 | \$0.260 / hr | \$0.260 / hr | \$0.26 / hr |
| **Total Hourly Running Cost** | — | — | — | — | **~\$3.90 / hour** |

---

## 3. Cost for Staged Progressive Benchmark Ladder

Executing the full progressive benchmarking ladder from Smoke (10 users) through Target (200,000 users) for a 30-minute steady-state run:

$$\text{Total Test Run Time} = 1.5\text{ hours (provisioning, preflight, warmup, run, teardown)}$$
$$\text{Total Cloud Cost} \approx 1.5\text{ hours} \times \$3.90/\text{hour} \approx \mathbf{\$5.85\text{ total}}$$

### Cost Optimization Principles
1. **Spot Instances for Load Workers**: Worker nodes maintain zero persistent state; using Spot instances cuts worker fleet costs by up to $90\%$.
2. **Ephemeral Spin-Down**: Spin up worker nodes via cloud-init or Terraform immediately before scheduled benchmark runs and tear them down immediately upon artifact export.
3. **Decoupled Architecture**: Keeps the Control Plane running on minimal resources (\$0.05/hr) while scaling the Data Plane and Worker Fleet elastically on demand.
