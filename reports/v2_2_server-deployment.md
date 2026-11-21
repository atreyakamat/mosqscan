# Vectora AI 2.2 — Server Deployment and Inference Benchmark Report

## 1. Executive Summary

This report documents the server-hosted adult mosquito classifier deployment on the developer workstation for Vectora AI 2.2.
The candidate model **Exp B** (`vectora_candidate_exp_b.onnx`) was loaded, cryptographically validated, and hosted using ONNX Runtime CPU.
Docker container services were hardened to ensure LAN security.
Empirical benchmarking demonstrates server inference latency of ~62 ms and resilient concurrency bounding.

---

## 2. Server Environment and Hardware Profile

- **Processor**: Intel Core i7-2600 CPU @ 3.40 GHz
  - Physical Cores: 4
  - Logical Threads: 8
  - Supported Instruction Sets: MMX, SSE, SSE2, SSE3, SSSE3, SSE4.1, SSE4.2, AVX
  - Missing Instruction Sets: AVX2, FMA (Sandy Bridge architecture constraint)
- **Memory**: 16 GB DDR3 RAM (15.49 GiB addressable)
- **Host OS**: Linux (Omarchy Linux / Arch-based, Kernel 6.17.7)
- **Python Runtime**: Python 3.12.15
- **ONNX Runtime**: `onnxruntime` v1.31.1 (CPU Execution Provider)
- **Network Interface**: Ethernet IP `192.168.1.120`

---

## 3. Containerized Architecture and Network Hardening

The deployment runs via Docker Compose with 4 coordinated services:

| Container Name | Service | Image | Published Ports | Health Check Status |
| :--- | :--- | :--- | :--- | :--- |
| `vectora-backend` | FastAPI REST API | `mosqscan-backend` | `0.0.0.0:8000->8000` | Healthy (HTTP 200 on `/health`) |
| `vectora-postgres` | PostgreSQL 16 DB | `postgres:16-alpine` | *Internal Only* | Healthy (`pg_isready`) |
| `vectora-redis` | Redis 7 Broker | `redis:7-alpine` | *Internal Only* | Healthy (`redis-cli ping`) |
| `vectora-video-worker` | Celery Async Worker | `mosqscan-video_worker` | *Internal Only* | Running |

### Security Isolation
- PostgreSQL and Redis port bindings (`5432:5432` and `6379:6379`) were removed from host exposure.
- Backend API binds to `0.0.0.0:8000`, allowing field devices on the local subnet `192.168.1.0/24` to access the API while shielding the database.

---

## 4. Startup Verification and Lifespan Integrity

During FastAPI application startup (`lifespan` in `backend/app/main.py`), the following sequence executes:

1. **Path Verification**: Resolves `/app/models/vectora_candidate_exp_b.onnx`.
2. **SHA-256 Checksum Calculation**:
   - Actual: `d644b9cd9c952d461bbfbb44e8b1926cdcf9bbbfb9cd43f85065cbed0d7b1499`
   - Expected: `d644b9cd9c952d461bbfbb44e8b1926cdcf9bbbfb9cd43f85065cbed0d7b1499`
   - Integrity result: **MATCH (VERIFIED)**.
3. **Session Graph Verification**:
   - Input Tensor: `(1, 3, 224, 224)` float32.
   - Output Tensor: `(1, 3)` float32.
4. **Smoke Test Execution**:
   - Synthetic tensor evaluated in 12.4 ms.
   - Initialized `AdultClassifier` singleton with `is_ready = True`.

---

## 5. CPU Resource Concurrency Tuning

To optimize latency and avoid resource contention on the 4-core i7-2600 host:
- `intra_op_num_threads = 2`: Limits ONNX thread allocation per operation.
- `inter_op_num_threads = 1`: Sequential operator execution.
- `CONCURRENT_INFERENCE_LIMIT = 1`: `asyncio.Semaphore(1)` ensures only one inference runs at a time.
- `ThreadPoolExecutor(max_workers=1)`: Executes model evaluation off the main async event loop.

---

## 6. Empirical Benchmark Results

Benchmark script `scripts/benchmark_inference.py` executed against the live Docker backend on the host machine.
Results were saved to `reports/v2_2_benchmark_results.json`:

### 6.1 Warm-up Phase (5 requests)
- Warm-up 1: 1184.9 ms (server inference: 293 ms)
- Warm-up 2: 531.9 ms (server inference: 57 ms)
- Warm-up 3: 646.9 ms (server inference: 163 ms)
- Warm-up 4: 503.0 ms (server inference: 61 ms)
- Warm-up 5: 444.3 ms (server inference: 61 ms)

### 6.2 Sequential Benchmark (25 requests)
- **End-to-End Client Roundtrip**:
  - Median Latency: **407.55 ms**
  - p95 Latency: **499.86 ms**
  - Minimum Latency: **383.94 ms**
  - Maximum Latency: **541.51 ms**
- **Server Inference Processing (Pure Model Time)**:
  - Median Inference Time: **62.0 ms**
  - p95 Inference Time: **85.0 ms**

### 6.3 Concurrency Test (5 Simultaneous Parallel Requests)
Five concurrent HTTP requests submitted simultaneously from distinct worker threads:
- Request 1: Status 201, Roundtrip: 2457.7 ms, Server inference: 66 ms
- Request 2: Status 201, Roundtrip: 2524.4 ms, Server inference: 62 ms
- Request 3: Status 201, Roundtrip: 2599.5 ms, Server inference: 64 ms
- Request 4: Status 201, Roundtrip: 2666.0 ms, Server inference: 68 ms
- Request 5: Status 201, Roundtrip: 2724.4 ms, Server inference: 64 ms
- Result: **100% success rate (5/5 HTTP 201)**.
  The semaphore queued requests cleanly without server crashes, race conditions, or CPU saturation.

### 6.4 Resource Utilization During Benchmark
- **Backend Container Memory**: 8.29 MiB (0.05% of available RAM).
- **Host Total RAM**: 15.49 GiB (Used: 12.74 GiB, Available: 2.75 GiB, 82.2%).
- **Host CPU Load**: 2.64, 4.79, 4.89 (stable across test cycle).
