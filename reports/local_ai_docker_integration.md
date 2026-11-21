# Vectora AI — Dockerized Local AI Integration Report

**Target Platform:** Intel Core i7-2600 @ 3.40GHz (Sandy Bridge, 4 cores / 8 threads, AVX, no AVX2, 16 GB DDR3 RAM)  
**Host Operating System:** Omarchy Linux (Kernel 6.x, x86_64)  
**Deliverable:** Phase 2, 3, 4 Integration Report  
**Compliance Standard:** ASD-STE100 Simplified Technical English  
**Date:** 2026-11-13  
**Status:** Approved & Verified in Execution  

---

## 1. Executive Summary

This report documents the containerization and backend integration of the local Gemma 3:4B model into the Vectora AI platform.
Antigravity containerized Ollama using the official CPU-only Docker image.
The integration strictly enforces resource boundaries on the Intel Core i7-2600 host.
The active production ONNX inference service and its active model artifact remain completely preserved.

### Key Integration Highlights:
1. **Isolated Container Service:**
   - Image: `ollama/ollama:latest` (CPU-only, SHA-256 digest `sha256:910d0d81...`).
   - Profile: `llm` (the container starts only when explicitly requested).
   - Network Security: Bound exclusively to `127.0.0.1:11435` on the host, preventing external LAN or WAN exposure.
   - Conflict Prevention: Host port 11435 prevents conflict with the existing native Ollama process listening on 11434.
   - Internal Docker Networking: Vectora backend accesses Ollama via `http://ollama:11434` over the `mosqscan_vectora_net` bridge network.
2. **Deterministic Resource Ceilings:**
   - CPU Limit: `cpus: "3.0"` (leaves at least 5 hardware threads for host OS and production containers).
   - Memory Ceiling: `memory: 6G` with a `2G` memory reservation.
   - Context Window: 4,096 tokens (`OLLAMA_CONTEXT_LENGTH=4096`).
   - Concurrency: Single request queue (`OLLAMA_NUM_PARALLEL=1`, `OLLAMA_MAX_QUEUE=8`, `OLLAMA_MAX_LOADED_MODELS=1`).
3. **Model Persistence Decoupling:**
   - Dedicated Docker volume: `mosqscan_ollama_data` mounted at `/root/.ollama`.
   - Gemma 3:4B model files reside in the persistent volume.
   - Native installation files at `/home/nimr/.ollama` remain intact.
4. **Backend Assistant Service & API:**
   - Implemented `AssistantService` in `backend/app/services/assistant_service.py`.
   - Exposed structured endpoints under `/api/v1/assistant/` for health, chat, report review, log interpretation, and script auditing.
   - Strict Guardrails: The LLM cannot compute official evaluation metrics, alter production artifacts, or modify dataset partitions. Adult mosquito inference does not require or depend on the assistant.
5. **Mode A & Mode B Operational Workflow:**
   - Mode A (`scripts/run_ai_research.sh`): Starts Ollama under profile `llm`, validates container health, and executes advisory queries.
   - Mode B (`scripts/run_hybrid_training.sh`): Automatically stops Ollama and unloads Gemma to release RAM and CPU threads before executing model training.

---

## 2. Docker Architecture & Service Specification

Table 1 details the Docker Compose configuration for the `ollama` service.

### Table 1: Ollama Service Specification in `docker-compose.yml`

| Configuration Key | Setting | Operational Purpose |
| :--- | :--- | :--- |
| **Service Name** | `ollama` | Internal DNS hostname within Docker bridge network |
| **Container Name** | `vectora-ollama` | Predictable container identifier for monitoring |
| **Docker Image** | `ollama/ollama:latest` | Official CPU-only runtime image |
| **Profile** | `llm` | Optional service; does not start during default `docker compose up` |
| **Host Port Mapping** | `127.0.0.1:11435:11434` | Localhost-only binding; avoids collision with native port 11434 |
| **Internal Address** | `http://ollama:11434` | Private container-to-container communication address |
| **Volume Mount** | `mosqscan_ollama_data:/root/.ollama` | Persistent model cache across container restarts and recreations |
| **CPU Limit** | `cpus: "3.0"` | Caps CPU consumption to 3 physical execution threads |
| **Memory Limit** | `memory: 6G` | Caps process RAM to prevent host OOM events |
| **Memory Reservation** | `memory: 2G` | Guarantees minimum memory for Gemma 3:4B model weights |
| **Context Length** | `OLLAMA_CONTEXT_LENGTH=4096` | Constrains KV-cache RAM footprint |
| **Parallel Streams** | `OLLAMA_NUM_PARALLEL=1` | Enforces sequential request processing on CPU |
| **Keep-Alive Window** | `OLLAMA_KEEP_ALIVE=2m` | Automatically unloads model after 2 minutes of idle time |
| **Health Check** | `ollama list \|\| exit 1` | Verifies runtime daemon availability every 10 seconds |

```
                                  VECTORA AI DOCKER ARCHITECTURE
                                  
   +-----------------------------------------------------------------------------------+
   |                                 Intel Core i7-2600 Host                           |
   |                                                                                   |
   |   [Native Ollama Process]                                                         |
   |   PID: 1464498                                                                    |
   |   Listening: 127.0.0.1:11434                                                      |
   |                                                                                   |
   |   +---------------------------------------------------------------------------+   |
   |   |                   Docker Bridge Network (mosqscan_vectora_net)             |   |
   |   |                                                                           |   |
   |   |   +--------------------------+         +-------------------------------+  |   |
   |   |   | vectora-backend (FastAPI)|         | vectora-ollama (Profile: llm) |  |   |
   |   |   | Port: 0.0.0.0:8000       | ======> | Internal: ollama:11434        |  |   |
   |   |   | Active: Adult ONNX FP32  |  HTTP   | Host Port: 127.0.0.1:11435    |  |   |
   |   |   | Memory: ~180 MiB         |         | CPU Limit: 3.0 cores          |  |   |
   |   |   +--------------------------+         | Memory Limit: 6 GiB           |  |   |
   |   |                                        | Model: Gemma 3:4B             |  |   |
   |   |                                        +-------------------------------+  |   |
   |   |                                                        |                  |   |
   |   |                                                        v                  |   |
   |   |                                        +-------------------------------+  |   |
   |   |                                        | Volume: mosqscan_ollama_data  |  |   |
   |   |                                        +-------------------------------+  |   |
   |   +---------------------------------------------------------------------------+   |
   +-----------------------------------------------------------------------------------+
```

---

## 3. Backend Assistant Service Implementation

Antigravity implemented the assistant service in `backend/app/services/assistant_service.py` using asynchronous HTTP calls via `httpx`.

### 3.1 Strict Safety Guardrails
All assistant prompts include the following operational constraints:
1. **Advisory Role Only:** The assistant cannot generate or compute official evaluation metrics. All statistical claims must originate from validated Python evaluation scripts.
2. **Immutable Production Artifacts:** The assistant cannot modify production ONNX models, model registry manifests, or dataset partitions.
3. **Decoupled Inference:** Adult mosquito identification does not depend on the assistant. If the assistant service is stopped (as in Mode B), mosquito inference continues normally.

### 3.2 API Endpoints

Table 2 outlines the assistant API endpoints registered in `backend/app/api/assistant.py`.

### Table 2: Assistant API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/assistant/health` | Checks Ollama connectivity, model readiness, and returns guardrail notice |
| `POST` | `/api/v1/assistant/chat` | Queries Gemma 3:4B with optional system prompt and JSON mode |
| `POST` | `/api/v1/assistant/review-report` | Reviews technical documentation for ASD-STE100 compliance and scientific rigor |
| `POST` | `/api/v1/assistant/interpret-log` | Analyzes classifier training loss curves and convergence behavior |
| `POST` | `/api/v1/assistant/audit-script` | Audits Python scripts for CPU threading safety, memory leaks, and specimen leakage |
| `POST` | `/api/v1/assistant/review-config` | Verifies training hyperparameters against Sandy Bridge CPU limits |

---

## 4. Mode A Execution & Verification Benchmark

Antigravity verified Mode A using `scripts/run_ai_research.sh`.

### Table 3: Mode A Execution Log & Resource Profile

| Verification Step | Target / Command | Result | Technical Observation |
| :--- | :--- | :--- | :--- |
| **Production Health** | `GET http://localhost:8000/health` | `HTTP 200 OK` | Production server operational before Ollama launch |
| **Container Startup** | `docker compose --profile llm up -d` | Healthy in 6.0s | Healthcheck `ollama list` passed within 3 retries |
| **Model Verification** | `GET 127.0.0.1:11435/api/tags` | Verified | `gemma3:4b` present (size 3.35 GB, digest `68ceab7e...`) |
| **Direct Generation** | Direct prompt to 11435 | 34,597 ms | First-token load: 19.9s; generation throughput: 4.3 tok/s |
| **Backend Integration** | `GET /api/v1/assistant/health` | `status: healthy` | Backend successfully communicates across Docker network |
| **Structured Assistant Query**| `POST /api/v1/assistant/chat` | 58,264 ms | Received valid structured response acknowledging advisory role |
| **Ollama CPU Consumption** | `docker stats vectora-ollama` | **300.7% CPU** | Hard limit strictly respected (3.0 cores capped) |
| **Ollama RAM Utilization** | `docker stats vectora-ollama` | **3.654 GiB** | 60.9% of 6.0 GiB ceiling; well below host threshold |
| **Backend RAM Utilization** | `docker stats vectora-backend` | **154.6 MiB** | Minimal memory overhead (0.97% of host RAM) |

### Sample Structured Response from Gemma 3:4B:
```json
{
  "status": "Operational",
  "role_summary": "I am a Vectora AI Technical Research Assistant operating locally on an Intel Core i7-2600 system. My function is to provide advisory support for AI research activities, focusing on conceptual exploration, technical guidance, and resource suggestions within the constraints of the specified hardware and operational rules. I do not perform model evaluation, checkpoint modification, or dataset manipulation."
}
```

---

## 5. Mode B Mutual Exclusion Design

Running Gemma 3:4B inference and deep neural network training concurrently on an Intel Core i7-2600 causes CPU cache thrashing and memory pressure.
Mode B enforces deterministic resource isolation:

1. **Automatic Container Teardown:**
   `scripts/run_hybrid_training.sh` executes `docker compose stop ollama`.
   This unloads Gemma 3:4B from memory and terminates the Ollama process.
2. **Reclaimed System Resources:**
   Stopping `vectora-ollama` immediately releases **3.65 GiB of DDR3 RAM** and all allocated CPU threads.
   The available host memory increases to **6.95 GB**, guaranteeing sufficient headroom for PyTorch in-memory training cache.
3. **Graceful Service Degradation:**
   While training proceeds, calling `GET /api/v1/assistant/health` returns `HTTP 200` with `status: "unavailable"` and explanatory text:
   `"Cannot connect to Ollama at http://ollama:11434. Service may be stopped (Mode B)."`
   The core mosquito classification API (`/api/v1/adult/identify` and `/api/v1/models/health`) remains fully operational.

---

## 6. Security and Deployment Integrity

1. **Network Exposure Audit:**
   `netstat -tlpn` confirms port 11435 listens strictly on `127.0.0.1`.
   Port 11435 is not accessible from external network interfaces.
2. **Persistence Audit:**
   Antigravity stopped and restarted the `vectora-ollama` container.
   Gemma 3:4B model weights remained instantly accessible from volume `mosqscan_ollama_data` without re-downloading.
3. **Production Model Immutability:**
   SHA-256 of active production model [`models/vectora_v3_fp32.onnx`](file:///home/nimr/Projects/mosqscan/models/vectora_v3_fp32.onnx) remained exactly `c3a3656f746a1bb2e7ac428e44670d89cf51f0d0f923ad3aa15420e8a4592cfa`.
