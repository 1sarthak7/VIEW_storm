# ViewStorm Distributed Networking & Security Guide

## 1. Network Topology & Ports

ViewStorm separates control plane operations, load generation telemetry, and distributed coordination across distinct network paths:

| Port | Protocol | Source | Destination | Purpose | Security Requirement |
|---|---|---|---|---|---|
| `8000` | HTTP / TCP | Workers / Users | FastAPI Backend | API Control Plane & Event Ingestion | TLS recommended; auth token on worker endpoints |
| `5557` | ZeroMQ / TCP | Locust Workers | Locust Master | Master-Worker RPC Coordination | **PRIVATE ONLY**; do not expose to public internet |
| `5558` | ZeroMQ / TCP | Locust Workers | Locust Master | Master-Worker Heartbeat & Sync | **PRIVATE ONLY**; do not expose to public internet |
| `6379` | RESP / TCP | FastAPI Backend | Redis Server | High-Speed Counters & Heartbeat Leases | Isolated internal network / localhost |
| `5432` | Postgres / TCP | FastAPI Backend | PostgreSQL | Durable Metadata & Historical Stats | Isolated internal network / localhost |

---

## 2. ZeroMQ Unencrypted Wire Warning

> [!WARNING]
> Locust's ZeroMQ transport on ports `5557` and `5558` is completely **unencrypted** and does not provide native cryptographic authentication.
> **NEVER expose port 5557 or 5558 directly to the public internet.**
> In distributed cross-machine or cross-cloud deployments, all ZeroMQ traffic between workers and the master must traverse a secure overlay network, such as a private VPC subnet or an encrypted WireGuard VPN.

---

## 3. Secure Multi-Host Setup with WireGuard

For remote load-generation machines located across different cloud regions or on-premise hardware:

```
[ Worker Machine 1 ] (10.0.0.2) ---WireGuard VPN Tunnel---\
                                                           +---> [ Master / Backend ] (10.0.0.1)
[ Worker Machine 2 ] (10.0.0.3) ---WireGuard VPN Tunnel---/
```

### Master Node Firewall Rules (`ufw` on Linux)
```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow WireGuard VPN
sudo ufw allow 51820/udp

# Allow control plane and ZeroMQ only from WireGuard interface (wg0)
sudo ufw allow in on wg0 to any port 8000 proto tcp
sudo ufw allow in on wg0 to any port 5557 proto tcp
sudo ufw allow in on wg0 to any port 5558 proto tcp

# Enable firewall
sudo ufw enable
```

### Worker Outbound-Only Model
Because `WorkerAgent` connects out to the control plane via HTTP and connects out to the master via ZeroMQ, the worker machines require **zero inbound listening firewall ports**. They can sit behind NAT gateways or standard corporate firewalls without port forwarding.
