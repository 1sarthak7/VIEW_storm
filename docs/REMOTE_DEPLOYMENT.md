# ViewStorm Remote Deployment & Systemd Guide

## 1. Remote Worker Node Provisioning (Ubuntu / Debian)

Follow these steps to deploy a distributed load generator node on an independent Linux server:

### Step 1: Install Dependencies
```bash
sudo apt-get update && sudo apt-get install -y python3-venv python3-pip git build-essential
```

### Step 2: Clone Repository or Copy Worker Package
```bash
git clone https://github.com/1sarthak7/VIEW_storm.git /opt/viewstorm
cd /opt/viewstorm
```

### Step 3: Setup Python Virtual Environment
```bash
python3 -m venv /opt/viewstorm/.venv
/opt/viewstorm/.venv/bin/pip install --upgrade pip
/opt/viewstorm/.venv/bin/pip install -r worker-agent/requirements.txt
```

---

## 2. Systemd Service Unit File

Create a persistent service unit at `/etc/systemd/system/viewstorm-worker.service`:

```ini
[Unit]
Description=ViewStorm Distributed Load Generator Agent
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/viewstorm
Environment="PYTHONPATH=/opt/viewstorm/worker-agent:/opt/viewstorm"
Environment="VIEWSTORM_SERVER_URL=http://controlplane.internal:8000"
Environment="VIEWSTORM_WORKER_AUTH_TOKEN=viewstorm-secret-token"
Environment="VIEWSTORM_WORKER_NAME=loadgen-node-01"
Environment="VIEWSTORM_WORKER_CAPACITY=5000"
Environment="VIEWSTORM_PINNED_LOCUST_VERSION=2.47.0"

ExecStart=/opt/viewstorm/.venv/bin/python -m viewstorm_agent.main \
    --server-url http://controlplane.internal:8000 \
    --token viewstorm-secret-token \
    --capacity 5000 \
    --locustfile /opt/viewstorm/simulator/locustfile.py

Restart=always
RestartSec=5s
KillMode=mixed
TimeoutStopSec=15s

# Security sandboxing
NoNewPrivileges=true
ProtectSystem=full
ProtectHome=read-only

[Install]
WantedBy=multi-user.target
```

### Step 4: Enable and Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable viewstorm-worker
sudo systemctl start viewstorm-worker
sudo systemctl status viewstorm-worker
```

### Step 5: Check Logs
```bash
journalctl -u viewstorm-worker -f
```

---

## 3. Capacity Sizing Recommendations

| Target Virtual Users | Worker Count | Cores per Worker | RAM per Worker | Network Bandwidth |
|---|---|---|---|---|
| **1,000** | 1 Node | 2 vCPU | 2 GB | 100 Mbps |
| **10,000** | 2 Nodes | 4 vCPU | 4 GB | 1 Gbps |
| **50,000** | 5 Nodes | 8 vCPU | 8 GB | 2.5 Gbps |
| **200,000** | 10–15 Nodes | 16 vCPU | 16 GB | 10 Gbps |

Each Locust greenlet consumes negligible memory, but kernel socket limits (`nofile` ulimit) must be adjusted for high concurrency:

```bash
# Add to /etc/security/limits.conf
* soft nofile 65536
* hard nofile 65536
```
