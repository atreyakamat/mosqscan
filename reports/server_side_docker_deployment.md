# Vectora AI — Server-Side Docker Deployment Report

**Document Status:** Accepted Production Deployment Baseline  
**Date:** 2026-11-13  
**Target Host:** Intel Core i7-2600 (Sandy Bridge, 4 cores / 8 threads, AVX, no AVX2, 16 GB DDR3 RAM, Omarchy Linux)  
**Standard Compliance:** ASD-STE100 Technical English  

---

## 1. Executive Summary

This report documents the server-side Docker deployment for Vectora AI. The deployment enables authenticated Android and Web clients to upload mosquito photographs and receive real-time ONNX Runtime inference results.

The deployment satisfies three operational rules:
1. The deployment preserves the active production model `models/vectora_v3_fp32.onnx` (SHA-256: `c3a3656f746a1bb2e7ac428e44670d89cf51f0d0f923ad3aa15420e8a4592cfa`).
2. The deployment runs on an Intel Core i7-2600 CPU host without GPU acceleration.
3. The deployment isolates optional Large Language Model services from the primary inference path.

---

## 2. Hardware Baseline and CPU Resource Allocations

The host system operates with the following physical constraints:

| Specification | Host Parameter |
| :--- | :--- |
| **CPU Architecture** | Intel Core i7-2600 (Sandy Bridge, 3.40 GHz base, 3.80 GHz turbo) |
| **Physical Cores / Threads** | 4 physical cores / 8 execution threads |
| **Vector Instruction Support** | AVX (256-bit floating point). **No AVX2, No FMA3** |
| **System Memory** | 16 GB DDR3-1333 RAM |
| **Graphics Processing Unit** | None (Integrated Intel HD Graphics 2000 only; no CUDA or ROCm) |
| **Operating System** | Omarchy Linux (Kernel 6.6+ LTS) |

### CPU Threading Policy
To prevent CPU contention during ONNX inference and API request processing, the deployment enforces explicit thread allocations:
- **ONNX Intra-Op Threads:** `2` (handles vector parallelization for single tensor operations).
- **ONNX Inter-Op Threads:** `1` (executes sequential operator graphs).
- **Concurrent Inference Semaphore:** `1` (FastAPI restricts simultaneous ONNX model calls to one execution thread).
- **Celery Video Worker Concurrency:** `2` (background video frame extraction).
- **Gemma 3:4B CPU Threads (when invoked):** `4` (allocated via Ollama CPU thread pool).

---

## 3. Container Topology and Network Architecture

The deployment uses Docker Compose to orchestrate six isolated services. All inter-service traffic routes through an internal bridge network named `mosqscan_vectora_net`.

```
                         [ Android Client / Web Browser ]
                                        |
               +------------------------+------------------------+
               | (Port 8000: LAN/Host)                           | (Port 3001: Localhost only)
               v                                                 v
      +-----------------+                              +-------------------+
      | vectora-backend |                              |    vectora-web    |
      | (FastAPI + ONNX)|                              |     (Next.js)     |
      +--------+--------+                              +-------------------+
               |
               | (mosqscan_vectora_net: Private Docker Bridge)
               +--------------------+---------------------+
               |                    |                     |
               v                    v                     v
      +-----------------+  +-----------------+  +-------------------+
      |vectora-postgres |  |  vectora-redis  |  |vectora-video-worker|
      | (PostgreSQL 16) |  |   (Redis 7.0)   |  |   (Celery App)    |
      +-----------------+  +-----------------+  +-------------------+
               .
               . (Optional Research Profile: `docker compose --profile llm up -d ollama`)
               v
      +-----------------+
      | vectora-ollama  | (Bound to 127.0.0.1:11435 on host; http://ollama:11434 on bridge)
      | (Gemma 3:4B CPU)|
      +-----------------+
```

### Network Exposure Matrix

| Container Name | Service | Internal Port | Host Port Binding | Exposure Scope |
| :--- | :--- | :--- | :--- | :--- |
| `vectora-backend` | FastAPI App + ONNX Runtime | `8000/tcp` | `0.0.0.0:8000` | Local Network (LAN) & Host |
| `vectora-web` | Next.js Frontend | `3000/tcp` | `127.0.0.1:3001` | Localhost only |
| `vectora-postgres` | PostgreSQL 16 Alpine | `5432/tcp` | None (internal only) | Container network only |
| `vectora-redis` | Redis 7 Alpine | `6379/tcp` | None (internal only) | Container network only |
| `vectora-video-worker` | Celery Worker | N/A | None | Container network only |
| `vectora-ollama` (Profile: `llm`) | Ollama LLM Service | `11434/tcp` | `127.0.0.1:11435` | Localhost only (isolated) |

---

## 4. Volume Persistence and Data Storage

The deployment persists application data across container recreation cycles using Docker named volumes and host bind mounts.

| Storage Volume | Target Path Inside Container | Purpose |
| :--- | :--- | :--- |
| `media_storage` | `/tmp/vectora_media` | User upload images, extracted specimen crops, and video frames |
| `postgres_data` | `/var/lib/postgresql/data` | PostgreSQL relational tables, scan records, user credentials |
| `redis_data` | `/data` | Redis job states and task broker message queues |
| `mosqscan_ollama_data` | `/root/.ollama` | Gemma 3:4B model weights and Ollama configuration |
| Host Bind Mount (`./models`) | `/app/models` (read-only) | Production ONNX model artifact (`vectora_v3_fp32.onnx`) |
| Host Bind Mount (`./model-registry`) | `/app/model-registry` (read-only) | Production model manifest (`manifest.json`) |

---

## 5. Healthchecks and Monitoring Configuration

Every production container includes an automated healthcheck. Docker Compose evaluates container health before marking dependencies ready.

1. **`vectora-postgres`:**
   - Command: `pg_isready -U postgres -d vectora`
   - Interval: 10s, Timeout: 5s, Retries: 5.
2. **`vectora-redis`:**
   - Command: `redis-cli ping`
   - Interval: 10s, Timeout: 5s, Retries: 5.
3. **`vectora-backend`:**
   - Command: `curl -f http://localhost:8000/api/v1/models/health`
   - Interval: 10s, Timeout: 5s, Retries: 5.
   - Validation criteria: HTTP 200, `"status": "healthy"`, `"checksum_verified": true`.
4. **`vectora-web`:**
   - Command: `wget --no-verbose --tries=1 --spider http://127.0.0.1:3000/api/health`
   - Interval: 15s, Timeout: 5s, Retries: 3.
5. **`vectora-ollama`:**
   - Command: `ollama list`
   - Interval: 15s, Timeout: 10s, Retries: 3.

---

## 6. Restart Persistence and Resilience Verification

Verification testing confirmed that all system states survive service restarts:
- **Database Persistence Test:** Verified database submissions, prediction results, and media records survived a complete restart of `vectora-backend`.
- **Media File Integrity Test:** Verified that stored image bytes retrieved after container restart matched the original upload bytes.
- **Model Checksum Check:** Verified that `vectora-backend` recalibrated the SHA-256 hash upon container boot and confirmed exact equality with `c3a3656f746a1bb2e7ac428e44670d89cf51f0d0f923ad3aa15420e8a4592cfa`.
- **Ollama Independence:** Verified that stopping `vectora-ollama` causes zero degradation to adult inference throughput, latency, or result schemas.

---

## 7. Deployment Status Summary

| Service Component | Operational Status | Verification Method |
| :--- | :--- | :--- |
| Production ONNX Inference | Operational | 20/20 test scans executed |
| PostgreSQL Storage | Operational | Relational foreign keys and persistence verified |
| Redis Task Broker | Operational | Task dispatch verified |
| Celery Video Worker | Operational | Worker daemon registered and listening |
| Next.js Web Interface | Operational | HTTP 200 health check verified |
| Ollama Gemma 3:4B Profile | Operational (On-Demand) | Mode A explanation generated successfully |
