# Vectora AI 3.0 — Server-Hosted Inference and Deployment Report

**Date:** 2026-11-12  
**Host Platform:** Intel Core i7-2600 Workstation (16 GB RAM, Omarchy Linux)  
**Standard:** ASD-STE100  
**Status:** Complete  

---

## 1. Executive Summary

This report documents the containerized deployment architecture, network security configuration, hardware optimization, and operational management scripts for the Vectora AI 3.0 server-hosted inference system.

All inference workloads are centralized on the developer's Intel Core i7-2600 workstation, serving predictions to both the native Android field client and the responsive Next.js web application.

---

## 2. Infrastructure Architecture

The server stack is deployed via Docker Compose with strict service isolation:

```
[Android Client / Web Browser]
       │
       │ HTTP / HTTPS (Port 8000 / 3001)
       ▼
┌────────────────────────────────────────────────────────┐
│  Host System (Intel Core i7-2600 / Omarchy Linux)     │
│                                                        │
│  ┌───────────────────────┐  ┌───────────────────────┐  │
│  │   vectora-backend     │  │     vectora-web       │  │
│  │   FastAPI + ONNX RT   │  │   Next.js 15 Platform │  │
│  │   Port: 0.0.0.0:8000  │  │   Port: 127.0.0.1:3001│  │
│  └───────────┬───────────┘  └───────────┬───────────┘  │
│              │                          │              │
│  ────────────┼──────────────────────────┼────────────  │
│              │ Internal Bridge Network  │              │
│              ▼                          ▼              │
│  ┌───────────────────────┐  ┌───────────────────────┐  │
│  │   vectora-postgres    │  │     vectora-redis     │  │
│  │   PostgreSQL 16 DB    │  │   Redis 7 Rate Limiter│  │
│  │   (NO HOST PORT)      │  │   (NO HOST PORT)      │  │
│  └───────────────────────┘  └───────────────────────┘  │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │   vectora-video-worker (Celery Video Pipeline)   │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

---

## 3. Host Hardware Optimization (i7-2600)

The host processor is an Intel Core i7-2600 (Sandy Bridge generation, 4 physical cores, 8 threads, AVX support, lacks AVX2).

To maximize throughput and prevent thread contention:
1. **Execution Provider:** ONNX Runtime `CPUExecutionProvider` is used. CUDA is explicitly disabled.
2. **Thread Allocation:**
   - `ONNX_INTRA_OP_THREADS=2` (limits intra-op parallel tasks to 2 cores).
   - `ONNX_INTER_OP_THREADS=1` (serial execution between independent nodes).
3. **Bounded Concurrency:** `CONCURRENT_INFERENCE_LIMIT=1` offloads inference to a dedicated single-threaded executor, preventing event loop blocking while serving async HTTP requests.
4. **Single Startup Loading:** The model artifact is verified via cryptographic SHA-256 and loaded once during FastAPI application lifespan. Subsequent inference requests reuse the warm in-memory session.

---

## 4. Operational Control Scripts

All server lifecycle operations are automated via ASD-STE100 shell scripts located in `scripts/`:

| Script Name | Purpose | Command |
| :--- | :--- | :--- |
| `server-start.sh` | Verifies model checksums, checks Docker daemon, and starts stack. | `./scripts/server-start.sh` |
| `server-health.sh` | Queries `/health` and `/api/v1/models/info` endpoints. | `./scripts/server-health.sh` |
| `server-status.sh` | Displays container state, memory, CPU load, and host resources. | `./scripts/server-status.sh` |
| `server-logs.sh` | Tails real-time logs for backend or workers. | `./scripts/server-logs.sh [service]` |
| `server-stop.sh` | Gracefully shuts down all containerized services. | `./scripts/server-stop.sh` |

---

## 5. Network Security and Remote Access Policy

### 5.1 Prohibition of Public Port Forwarding
Public NAT forwarding of port 8000, 5432, or 6379 is strictly prohibited. Unauthenticated exposure risks vulnerability scanning, denial-of-service, and credential attacks.

### 5.2 Local Area Network (LAN) Access
Within the local laboratory Wi-Fi network, field devices connect directly to the host's private IP (e.g. `http://192.168.1.120:8000/`).

### 5.3 Remote Field Access via WireGuard VPN
Remote mobile clients connect exclusively through an encrypted WireGuard VPN tunnel:
- Workstation acts as WireGuard peer (`10.8.0.1/24`).
- Android field device acts as VPN client (`10.8.0.2/24`).
- Base URL configured on Android: `http://10.8.0.1:8000/`.
- Full configuration details documented in `docs/remote-access.md`.
