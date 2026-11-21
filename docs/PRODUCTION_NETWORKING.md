# Production Networking and Security Architecture

## 1. Subnet Topology and Segmentation

ViewStorm implements strict network segmentation across three private subnets:

```
[Internet / Operator] 
         | (Port 443 HTTPS only)
         v
+--------------------------------------------------------------+
| control_plane_net (10.10.1.0/24)                             |
| - Nginx Reverse Proxy (10.10.1.5)                            |
| - Control Plane Orchestrator (10.10.1.20:8000)               |
| - PostgreSQL Database (10.10.1.10:5432)                      |
| - Redis Cache (10.10.1.11:6379)                              |
+------------------------------+-------------------------------+
                               |
                               | (Internal Bridge)
                               v
+--------------------------------------------------------------+
| data_plane_net (10.10.2.0/24)                                |
| - Data Plane Load Balancer (10.10.2.20:8001)                 |
| - Dataplane Instance 1 (10.10.2.21:8001)                     |
| - Dataplane Instance 2 (10.10.2.22:8001)                     |
+------------------------------+-------------------------------+
                               |
                               | (Restricted Routing)
                               v
+--------------------------------------------------------------+
| worker_net (10.10.3.0/24 / WireGuard 10.10.100.0/24)         |
| - Outbound-only Worker Agents                                |
| - ZeroMQ Communication to Master (Ports 5557/5558)           |
| - Synthetic Traffic Generation targeting Data Plane          |
+--------------------------------------------------------------+
```

---

## 2. ZeroMQ Master-Worker Security

Locust distributed execution uses ZeroMQ sockets:
- **Port 5557 (REP/REQ)**: Worker registration and heartbeat signals.
- **Port 5558 (PUB/SUB)**: Master instruction broadcasting (spawn, halt).

### Critical Security Constraints
1. **Never Expose Ports 5557/5558 Publicly**: ZeroMQ does not provide transport-layer authentication or TLS encryption by default. Exposing ports 5557/5558 to the public internet allows unauthorized actors to inject malicious jobs or trigger remote code execution.
2. **Private Network Binding**: ViewStorm binds the Locust master sockets strictly to the internal private IP address (`10.10.1.20` or WireGuard interface `10.10.100.1`).
3. **Outbound-Only Worker Model**: Workers initiate all connections outward to the master and control plane; the master never opens inbound listening sockets toward workers.

---

## 3. WireGuard VPN for Multi-Machine Distributed Clusters

For clusters distributed across cloud VPCs, physical bare-metal servers, or remote development labs, ViewStorm provides a WireGuard VPN mesh:

### Master Node (`/etc/wireguard/wg0.conf`)
```ini
[Interface]
Address = 10.10.100.1/24
ListenPort = 51820
PrivateKey = MASTER_PRIVATE_KEY

PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

[Peer]
PublicKey = WORKER1_PUBLIC_KEY
AllowedIPs = 10.10.100.11/32
```

### Worker Node (`/etc/wireguard/wg0.conf`)
```ini
[Interface]
Address = 10.10.100.11/24
PrivateKey = WORKER1_PRIVATE_KEY

[Peer]
PublicKey = MASTER_PUBLIC_KEY
Endpoint = master.viewstorm.internal:51820
AllowedIPs = 10.10.100.0/24, 10.10.1.0/24, 10.10.2.0/24
PersistentKeepalive = 25
```

---

## 4. Firewall and Security Group Invariants

| Port | Protocol | Source | Destination | Purpose |
|---|---|---|---|---|
| **443** | TCP | Public Internet / VPN | Nginx Reverse Proxy | Secure Operator Dashboard |
| **8000** | TCP | `control_plane_net`, `worker_net` | Control Plane | REST APIs & Worker Registration |
| **8001** | TCP | `worker_net` | Data Plane LB | Synthetic Playback Event Ingestion |
| **5557** | TCP | `worker_net` (VPN only) | Control Plane (Master) | ZeroMQ Worker Handshake |
| **5558** | TCP | `worker_net` (VPN only) | Control Plane (Master) | ZeroMQ Broadcast Dispatch |
| **5432** | TCP | `control_plane_net`, `data_plane_net` | PostgreSQL | Database Queries & Batch Metrics |
| **6379** | TCP | `control_plane_net`, `data_plane_net` | Redis | Atomic Lua Ingestion & Leases |
| **9090** | TCP | Management CIDR | Prometheus | Monitoring Telemetry |
