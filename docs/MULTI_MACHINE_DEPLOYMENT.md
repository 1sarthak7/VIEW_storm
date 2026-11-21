# Multi-Machine Production Deployment Guide

## 1. Overview

This guide details how to deploy ViewStorm across multiple physical servers, cloud virtual machines, or isolated Docker containers in a production-like environment.

ViewStorm supports two primary multi-machine deployment topologies:
1. **Containerized Multi-Host Deployment**: Utilizing Docker Compose with separated host groups.
2. **Bare-Metal / Virtual Machine Deployment**: Utilizing Linux systemd service units and automated Ansible playbooks.

---

## 2. Docker Compose Multi-Host Deployment

### Host Group 1: Control Plane Host (e.g. `10.10.1.20`)
Hosts PostgreSQL, Redis, Control Plane FastAPI, React Frontend, and Locust Master:
```bash
git clone https://github.com/1sarthak7/VIEW_storm.git /opt/viewstorm
cd /opt/viewstorm/infrastructure
docker compose -f docker-compose.control-plane.yml up -d
```

### Host Group 2: Data Plane Ingestion Hosts (e.g. `10.10.2.21`, `10.10.2.22`)
Hosts high-throughput Uvicorn workers and Nginx load balancer:
```bash
git clone https://github.com/1sarthak7/VIEW_storm.git /opt/viewstorm
cd /opt/viewstorm/infrastructure
docker compose -f docker-compose.data-plane.yml up -d
```

### Host Group 3: Load Generator Worker Fleet (e.g. `10.10.3.31`–`10.10.3.99`)
Hosts distributed WorkerAgent containers:
```bash
git clone https://github.com/1sarthak7/VIEW_storm.git /opt/viewstorm
cd /opt/viewstorm/infrastructure
docker compose -f docker-compose.workers.yml up -d
```

---

## 3. Bare-Metal / Linux VM Deployment via systemd

For maximum performance (avoiding container bridge network NAT overhead), run directly under Linux systemd:

### Step 1: Install System Dependencies
```bash
sudo apt update && sudo apt install -y python3.11 python3.11-venv python3-pip git wireguard
```

### Step 2: Provision ViewStorm Daemon User
```bash
sudo useradd -m -s /bin/bash viewstorm
sudo mkdir -p /opt/viewstorm && sudo chown -R viewstorm:viewstorm /opt/viewstorm
```

### Step 3: Deploy Application Code and Virtual Environment
```bash
su - viewstorm
git clone https://github.com/1sarthak7/VIEW_storm.git /opt/viewstorm
python3.11 -m venv /opt/viewstorm/.venv
/opt/viewstorm/.venv/bin/pip install --upgrade pip
/opt/viewstorm/.venv/bin/pip install -r /opt/viewstorm/backend/requirements.txt
/opt/viewstorm/.venv/bin/pip install -r /opt/viewstorm/worker-agent/requirements.txt
exit
```

### Step 4: Install and Enable Services
- **Control Plane**:
  ```bash
  sudo cp /opt/viewstorm/infrastructure/systemd/viewstorm-controlplane.service /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl enable --now viewstorm-controlplane
  ```
- **Data Plane**:
  ```bash
  sudo cp /opt/viewstorm/infrastructure/systemd/viewstorm-dataplane.service /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl enable --now viewstorm-dataplane
  ```
- **Worker Node**:
  ```bash
  sudo cp /opt/viewstorm/infrastructure/systemd/viewstorm-worker-agent.service /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl enable --now viewstorm-worker-agent
  ```

---

## 4. Automated Multi-Machine Provisioning via Ansible

ViewStorm provides automated playbooks in `infrastructure/ansible/`:

```bash
cd infrastructure/ansible

# 1. Copy and configure inventory
cp inventory.ini.example inventory.ini
nano inventory.ini

# 2. Deploy Control Plane
ansible-playbook -i inventory.ini deploy-control-plane.yml

# 3. Deploy Data Plane Ingestion Farm
ansible-playbook -i inventory.ini deploy-data-plane.yml

# 4. Deploy Distributed Worker Fleet
ansible-playbook -i inventory.ini deploy-worker-fleet.yml
```

---

## 5. Deployment Verification

Run the automated verification script to validate all nodes across the network:
```bash
python scripts/verify_deployment.py \
  --control-plane-url http://10.10.1.20:8000 \
  --data-plane-url http://10.10.2.20:8001 \
  --redis-url redis://10.10.1.11:6379/0
```
