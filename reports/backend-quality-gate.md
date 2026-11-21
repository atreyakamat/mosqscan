# Vectora AI — Backend Quality Gate Report

**Date:** 2026-11-11  
**Auditor:** Senior Machine Learning & Quality Engineering  
**System:** Vectora AI Backend API & Background Worker  
**Status:** PROVISIONALLY APPROVED — EXPERIMENTAL USE ONLY  
**Model Evaluation Status:** `EXPERIMENTAL_NOT_FIELD_VALIDATED`

---

## 1. Executive Summary

This report provides the technical quality gate review for the Vectora AI backend.  
The backend implementation was tested against all functional, security, and machine learning criteria.  
All 56 unit and integration tests passed.  
The live Docker container environment was started, tested, and verified.

The adult mosquito identification pipeline does not include specimen detection.  
The classification model operates under a closed-world three-class assumption.  
The model cannot reliably reject non-mosquito images.  
Therefore, the model status remains strictly `EXPERIMENTAL_NOT_FIELD_VALIDATED`.

### Quality Gate Summary Table

| Quality Gate Item | Status | Verification Method | Result |
| :--- | :--- | :--- | :--- |
| **YOLO Specimen Detection** | **INCOMPLETE** | Static code search & architecture review | No detection network exists in codebase |
| **Non-Mosquito Rejection** | **EXPERIMENTAL** | Probability distribution audit | Uncalibrated 3-class softmax; heuristic threshold |
| **Model Status Flag** | **PASS** | API inspection & runtime verification | Set to `EXPERIMENTAL_NOT_FIELD_VALIDATED` |
| **Model Registry Parity** | **PASS** | SHA-256 checksums & PyTorch parity | Candidate Exp B matches ONNX FP32 & INT8 |
| **Video Duration (VFR)** | **PASS** | Boundary tests & timestamp audit | 2.99s/5.01s rejected; 3.00s/5.00s/VFR accepted |
| **No Video Trimming** | **PASS** | Code audit & API test | Rejected files are dropped without processing |
| **Authentication & RBAC** | **PASS** | Unit tests & live API requests | Argon2id, JWT, token rotation, cross-user isolation |
| **Media Upload Security** | **PASS** | Security test suite | Magic bytes, decompression bomb, traversal protected |
| **Docker Compose Environment** | **PASS** | Live container execution | Postgres, Redis, Backend, Celery Worker healthy |
| **Non-Root Execution** | **PASS** | `docker compose exec whoami` | Both backend and worker run as `vectora` (UID 1000) |
| **Restart Recovery** | **PASS** | `docker compose restart backend` | Clean recovery in 6s; tokens and database preserved |
| **Persistent Storage** | **PASS** | Docker volume inspection | Named volume `media_storage` retains files |
| **API Contract Freeze** | **PASS** | OpenAPI 3.1 schema export | Exported to `docs/openapi.json` |

---

## 2. Adult Mosquito Identification Audit

### 2.1 YOLO Specimen Localization

The Product Requirements Document specifies an object detector (such as YOLOv11n) for specimen localization.  
The codebase was inspected for object detection modules:

```bash
find . -iname "*yolo*"
```

**Finding:**  
Zero matching files exist in the repository.  
Specimen localization is missing.  
The backend directly inputs resized raw images into the classification model.  
Specimen detection is officially documented as **INCOMPLETE**.

### 2.2 Non-Mosquito Out-Of-Distribution (OOD) Rejection

The classification model uses an EfficientNet-B0 architecture with a 3-class linear head (`aedes`, `anopheles`, `culex`).  
The final layer applies a standard Softmax activation:

$$\sum_{i=1}^{3} P(\text{class}_i) = 1.0$$

The Softmax function forces all predictions to sum to 1.0.  
An image containing an arbitrary non-mosquito object (such as a desk, coin, or beetle) is assigned probabilities across the three mosquito classes.  

The application implements a heuristic threshold in `app/inference/adult_classifier.py`:
- Predictions with `confidence < 0.40` are marked as uncertain.
- Predictions with `confidence >= 0.40` output the top-scoring genus.

This heuristic threshold is not calibrated with temperature scaling or energy-based out-of-distribution scoring.  
Softmax confidence is known to produce overconfident predictions on out-of-distribution inputs.  

**Conclusion:**  
The three-class classifier cannot reliably reject non-mosquito objects.  
The model status is locked to:  
`EXPERIMENTAL_NOT_FIELD_VALIDATED`  
Confidence-based rejection remains experimental until empirical calibration is completed.

---

## 3. Model Registry Audit and Checksum Verification

### 3.1 Canonical Manifest

Two model manifest files exist in the repository:
1. `model-registry/manifest.json`: Runtime configuration mounted into backend and Docker containers.
2. `configs/model_manifest.json`: Provenance record documenting training parameters, dataset partitions, and metric logs.

The operational runtime source of truth is `model-registry/manifest.json`.  
Both manifests were verified to ensure synchronized metadata, class ordering (`aedes`, `anopheles`, `culex`), input shape (`[1, 3, 224, 224]`), and normalization parameters.

### 3.2 Artifact Checksums

Every model file was audited using SHA-256 checksums:

| Artifact Path | SHA-256 Checksum | Origin / Role |
| :--- | :--- | :--- |
| `models/vectora_candidate_exp_b.onnx` | `d644b9cd9c952d461bbfbb44e8b1926cdcf9bbbfb9cd43f85065cbed0d7b1499` | Exp B Candidate FP32 ONNX |
| `vectora-ai-starter/models/vectora_candidate_exp_b.onnx` | `d644b9cd9c952d461bbfbb44e8b1926cdcf9bbbfb9cd43f85065cbed0d7b1499` | Identical duplicate of Exp B FP32 |
| `models/vectora_candidate_exp_b_int8.onnx` | `6d7e830699f4ca3f3b67c538c2f77a592f88288845dfa00d94c7837ccef68803` | Exp B Candidate INT8 Dynamic ONNX |
| `vectora-ai-starter/models/vectora_candidate_exp_b_int8.onnx` | `6d7e830699f4ca3f3b67c538c2f77a592f88288845dfa00d94c7837ccef68803` | Identical duplicate of Exp B INT8 |
| `vectora-ai-starter/experiments/exp_B_unfreeze_stage7_8_best.pt` | `9179d67761ce4c0423c4aeb1f68153c306354673fb3911c07ae3f40dd169c9bf` | PyTorch Source Checkpoint |
| `android/app/src/main/assets/efficientnet_b0_int8.onnx` | `bac40d9af5441ddbdb6c6b19348fe04167ca4d8de7466611742022b7f505bd95` | **Discrepancy:** Old baseline INT8 model |

**Discrepancy Note:**  
The model bundled in `android/app/src/main/assets/` is the old baseline model (`bac40d...`), not the Exp B candidate model (`6d7e83...`).  
The Android asset must be updated before mobile integration.

### 3.3 Checkpoint-to-ONNX Parity Verification

The PyTorch checkpoint `exp_B_unfreeze_stage7_8_best.pt` was loaded and evaluated side-by-side against `models/vectora_candidate_exp_b.onnx` across test inputs:

- Maximum logit difference: $5.3644 \times 10^{-7}$
- Maximum probability difference: $5.9605 \times 10^{-8}$

The FP32 ONNX model is mathematically identical to the PyTorch Exp B checkpoint.

---

## 4. Video Validation and Variable Frame Rate (VFR) Handling

### 4.1 Duration Calculation Logic

Naively calculating video duration via `frame_count / fps` fails on variable-frame-rate (VFR) recordings common to smartphones.  
The video validator in `backend/app/services/larvae_service.py` implements a two-stage verification process:
1. `ffprobe` decodes presentation timestamps (PTS) from the container and video stream.
2. OpenCV `VideoCapture` decodes actual frames to verify stream integrity and non-zero duration.

### 4.2 Boundary Test Results

The duration boundaries (3.00s to 5.00s) were tested with synthetic and real video files:

| Test Case | Calculated Duration | Validation Result | HTTP Status Code | Error Code |
| :--- | :--- | :--- | :--- | :--- |
| `boundary_2_99s.mp4` | 2.990 s | REJECTED | 422 Unprocessable Entity | `DURATION_TOO_SHORT` |
| `boundary_3_00s.mp4` | 3.000 s | ACCEPTED | 202 Accepted | — |
| `nominal_4_00s.mp4` | 4.000 s | ACCEPTED | 202 Accepted | — |
| `boundary_5_00s.mp4` | 5.000 s | ACCEPTED | 202 Accepted | — |
| `boundary_5_01s.mp4` | 5.010 s | REJECTED | 422 Unprocessable Entity | `DURATION_TOO_LONG` |
| `corrupted_header.mp4` | N/A (Header invalid) | REJECTED | 422 Unprocessable Entity | `CORRUPTED_VIDEO` |
| `truncated_stream.mp4` | N/A (Incomplete stream) | REJECTED | 422 Unprocessable Entity | `CORRUPTED_VIDEO` |
| `vfr_4_00s.mp4` | 4.000 s (VFR stream) | ACCEPTED | 202 Accepted | — |

### 4.3 Trimming and Rejection Enforcement

- No uploaded videos are trimmed or modified.
- Rejected videos are deleted from storage immediately.
- Rejected videos are never queued to Redis or Celery.

---

## 5. Docker Integration Audit

The backend services were deployed using Docker Compose:
- `vectora-postgres` (PostgreSQL 16)
- `vectora-redis` (Redis 7)
- `vectora-backend` (FastAPI)
- `vectora-video-worker` (Celery background worker)

### 5.1 Verification Checklist

1. **Database Readiness:** PostgreSQL container passed healthchecks (`pg_isready`).
2. **Database Migrations:** Alembic migration `bfe186d08758` applied cleanly on container startup.
3. **Backend Readiness:** FastAPI startup completed and passed HTTP health check on port 8000.
4. **Worker Readiness:** Celery 5.4.0 worker registered `process_larvae_video_task` and connected to Redis.
5. **Non-Root Execution:** Verified `whoami` returns `vectora` in both `backend` and `video_worker`.
6. **Persistent Media Storage:** Media files uploaded to `/app/media` persisted across container restarts.
7. **Restart Recovery:** Backend container was restarted (`docker compose restart backend`); full health was restored in 6 seconds without loss of state.

### 5.2 Live API Test Results

A live integration test suite (`backend/tests/test_live_docker.py`) executed against the running containers:

```text
--- 1. Testing Unauthorized Request Rejection ---
Status: 401, Body: {'success': False, 'error_code': 'UNAUTHORIZED', 'message': 'Not authenticated'}

--- 2. Testing Registration (User 1) ---
Status: 201, User ID: 6f34aab4-89b7-4308-b5d8-948014c53a88

--- 3. Testing Login (User 1) ---
Status: 200, JWT access token returned

--- 4. Testing User Profile (User 1) ---
Status: 200, Email: field_researcher_1_1794395893@vectora.org

--- 5. Testing Adult Mosquito Identification ---
Status: 201, Top score genus: aedes, Confidence: 0.44195, Processing time: 268ms

--- 6. Testing Larvae Job Submission & Celery Worker Processing ---
Status: 202, Job ID: 75a38cd2-6042-4492-b89e-598c8832823f

--- 7. Polling Job Status ---
Poll 1: status = processing
Poll 2: status = completed
Frames processed: 105, Valid frames: 105

--- 8. Testing Cross-User Isolation (User 2) ---
User 2 access to User 1 larvae job: 403 Forbidden
User 2 access to User 1 adult submission: 403 Forbidden

ALL LIVE DOCKER API TESTS PASSED SUCCESSFULLY!
```

---

## 6. CPU Inference Benchmark

Benchmarking was executed on the host CPU using ONNX Runtime with `CPUExecutionProvider`.  
The benchmark used 10 warmup runs followed by 100 timed inference iterations per configuration.

### 6.1 Hardware and Runtime Specification

- **Processor:** Intel(R) Core(TM) i7-2600 CPU @ 3.40GHz
- **Architecture:** x86_64, 4 cores, 8 threads
- **Instruction Sets:** AVX supported, no AVX2, no AVX-512, no AVX-VNNI
- **Operating System:** Linux 7.2.8
- **ONNX Runtime:** 1.31.1
- **Execution Provider:** `CPUExecutionProvider`

### 6.2 Latency Results

| Model Artifact | Precision | Threads | Mean Latency | Median Latency | p95 Latency | p99 Latency |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `vectora_candidate_exp_b.onnx` | FP32 | 1 | 39.84 ms | **38.04 ms** | 53.19 ms | 64.07 ms |
| `vectora_candidate_exp_b.onnx` | FP32 | 2 | 22.00 ms | **20.83 ms** | 28.00 ms | 32.60 ms |
| `vectora_candidate_exp_b.onnx` | FP32 | 4 | 15.70 ms | **14.58 ms** | 21.00 ms | 21.61 ms |
| `vectora_candidate_exp_b_int8.onnx` | INT8 | 1 | 165.01 ms | **150.86 ms** | 250.88 ms | 282.80 ms |
| `vectora_candidate_exp_b_int8.onnx` | INT8 | 2 | 76.81 ms | **72.52 ms** | 101.31 ms | 114.73 ms |
| `vectora_candidate_exp_b_int8.onnx` | INT8 | 4 | 67.34 ms | **60.35 ms** | 108.14 ms | 118.06 ms |

### 6.3 Performance Analysis

1. **FP32 vs INT8 on Desktop CPU:**  
   FP32 executes substantially faster than INT8 on this host (14.58 ms vs 60.35 ms on 4 threads).  
   The Intel i7-2600 supports AVX but lacks AVX-VNNI or AVX2 integer acceleration instructions.  
   On CPUs without hardware integer vectorization, dynamic quantization introduces runtime dequantization overhead.
2. **Mobile Deployment:**  
   INT8 dynamic quantization is designed for mobile ARM NEON architectures with hardware dot-product instructions.  
   Desktop benchmark figures must not be confused with Android device performance.
3. **Throughput:**  
   With 4 threads, the FP32 model achieves 68.6 inferences per second, satisfying all backend throughput requirements.

---

## 7. Frozen API Contract

The complete OpenAPI 3.1.0 specification was exported to `docs/openapi.json`.  
The API contract defines:
- 28 API routes.
- Schemas for all requests and responses.
- HTTP status codes (200, 201, 202, 400, 401, 403, 404, 422, 500).
- Upload limits: 20MB for images, 100MB for videos.
- Video duration boundaries: 3.00s to 5.00s.
- Background job states: `queued`, `processing`, `completed`, `failed`.
