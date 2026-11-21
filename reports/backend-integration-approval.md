# Vectora AI — Backend Integration Approval

**Date:** 2026-11-11  
**Auditor:** Senior Machine Learning & Quality Engineering  
**System:** Vectora AI Backend Platform  
**Integration Status:** **PROVISIONALLY APPROVED — EXPERIMENTAL USE ONLY**  
**Production Readiness:** **BLOCKED PENDING FIELD VALIDATION AND SECURITY HARDENING**

---

## 1. Approval Decision

The Vectora AI backend platform is **PROVISIONALLY APPROVED** for software integration and end-to-end testing with client applications.  

This approval confirms that the backend architecture, database schemas, asynchronous processing pipelines, authentication systems, model serving engines, and Docker container environments function correctly and adhere to defined engineering contracts.

**PRODUCTION RELEASE IS BLOCKED.**  
The machine learning models have not achieved the PRD acceptance target (92% macro-F1).  
Specimen detection (YOLO) is missing.  
Out-of-distribution rejection is uncalibrated.  
The backend must remain configured with model status:  
`EXPERIMENTAL_NOT_FIELD_VALIDATED`

---

## 2. Verified Capabilities and Passing Gates

The backend implementation successfully passed all technical verification criteria:

### 2.1 Machine Learning and Inference Parity
- **Model Candidate Exp B Verified:** Both FP32 (`d644b9...`) and INT8 (`6d7e83...`) ONNX artifacts match the trained PyTorch checkpoint `exp_B_unfreeze_stage7_8_best.pt` within numerical tolerance ($< 6 \times 10^{-7}$ max logit difference).
- **Runtime Model Registry:** `model-registry/manifest.json` serves as the runtime operational source of truth.
- **Inference Latency:** FP32 ONNX inference executes in 14.58 ms (median) on 4 CPU threads on the host Intel i7-2600.
- **Model Parity Tests:** Automated tests verify class ordering (`aedes`, `anopheles`, `culex`) and probability alignment across precision levels.

### 2.2 Asynchronous Video Processing Pipeline
- **Decoupled Architecture:** FastAPI dispatches video processing tasks to Celery via Redis.
- **VFR Duration Validation:** `ffprobe` PTS stream inspection prevents false rejections on variable-frame-rate videos while enforcing strict 3.00s to 5.00s boundaries.
- **Zero Trimming:** Invalid or out-of-boundary videos are rejected immediately with HTTP 422 and are never processed.
- **Worker Execution:** Celery workers process videos, decode frames, and record execution metrics (`frame_count`, `valid_frames`) in PostgreSQL.

### 2.3 Authentication and Data Isolation
- **Argon2id Hashing:** Password security satisfies modern cryptographic guidelines.
- **Session Security:** 15-minute JWT access tokens and rotating SHA-256 hashed refresh tokens prevent persistent token theft.
- **Multi-Tenant Isolation:** Automated test suite and live Docker tests confirmed that cross-user access to submissions or jobs is strictly blocked with HTTP 403 Forbidden.

### 2.4 Containerized Infrastructure
- **Docker Compose:** All four core services (`postgres`, `redis`, `backend`, `video_worker`) start reliably and pass automated health checks.
- **Database Migrations:** Alembic runs migrations automatically on container startup.
- **Non-Root Execution:** Both application containers execute as non-root user `vectora` (UID 1000).
- **Restart Recovery:** Tested clean restart recovery; service health is restored within 6 seconds without data loss.
- **Persistent Media:** Media storage is mounted to a persistent Docker named volume.

### 2.5 Test Suite and API Contract Freeze
- **Test Suite Results:** 56 unit and integration tests executed with 100% pass rate (`56 passed, 0 failed`).
- **Live Integration Tests:** Live Docker API requests (`backend/tests/test_live_docker.py`) confirmed end-to-end operation across authentication, adult inference, video processing, and isolation.
- **OpenAPI Specification:** Complete OpenAPI 3.1.0 contract exported and frozen at `docs/openapi.json`.

---

## 3. Production Deployment Blockers

The following items are unresolved blockers for production deployment:

| Blocker ID | Category | Description | Status | Resolution Requirement |
| :--- | :--- | :--- | :--- | :--- |
| **BLK-01** | Machine Learning | YOLO specimen detection is absent from codebase | Open | Train and integrate specimen detection module |
| **BLK-02** | Machine Learning | 3-class Softmax classifier cannot reject non-mosquitoes | Open | Implement calibrated OOD rejection (temperature/energy) |
| **BLK-03** | Machine Learning | Model Exp B test macro-F1 is 0.707 (PRD target: 0.920) | Open | Acquire larger field dataset and retrain model |
| **BLK-04** | Security | In-memory rate limiting does not scale across workers | Open | Migrate rate limiter store to Redis |
| **BLK-05** | Security | Cookie refresh lacks explicit CSRF token header | Open | Implement `X-CSRF-Token` header verification |
| **BLK-06** | Android Sync | Android asset contains old baseline model | Open | Copy `vectora_candidate_exp_b_int8.onnx` to Android assets |

---

## 4. Operational Guardrails

During this integration phase, the following guardrails must remain active:

1. **Model Status Header & Response:**  
   Every adult and larvae identification response must include:  
   `"model_status": "EXPERIMENTAL_NOT_FIELD_VALIDATED"`  
   Clients must display appropriate warnings to users indicating that results are experimental.
2. **Confidence Threshold:**  
   Predictions with confidence $< 0.40$ must continue to report `predicted_genus = null` with `is_uncertain = true`.
3. **No Unapproved Production Claims:**  
   Documentation, marketing, and user interfaces must not claim production-grade mosquito identification until field validation targets are met.

---

## 5. Integration Approval Sign-Off

- **Technical Lead:** Senior Quality & Machine Learning Engineer
- **Approval Date:** 2026-11-11
- **Recommendation:** Proceed with frontend and Android client integration testing against the backend Docker containers using the frozen API specification (`docs/openapi.json`). Keep production deployment gated behind Blockers BLK-01 through BLK-06.
