# Vectora AI 2.1 — Full System Regression Report

## 1. Executive Summary

This report documents the results of the complete regression test cycle executed for Vectora AI 2.1.
All automated test suites across Backend, Web Frontend, Android Mobile, Docker Compose integration, and Model Registry were executed.

**Summary of Results**:
- **Backend Tests (pytest)**: 71 passed, 0 failed (100% pass rate).
- **Web Tests (node:test)**: 10 passed, 0 failed (100% pass rate).
- **Android Tests (Gradle JUnit)**: 18 passed, 0 failed (100% pass rate).
- **Docker Compose Live Integration**: 8 test suites passed, 0 failed (100% pass rate).
- **Model Registry Checksums**: 2 passed, 0 failed (100% pass rate).
- **Android Signed Release Build**: Successful, v2 signature verified across all 5 ABI splits.

---

## 2. Backend Regression Suite (Pytest)

### 2.1 Execution Details
- Environment: Python 3.12.15, PyTorch 2.6.0+cpu, ONNX Runtime 1.20.1, Redis 8.1.0, Pytest 9.2.0.
- Command: `PYTHONPATH=backend vectora-ai-starter/.venv/bin/python -m pytest backend/tests -v`
- Execution Time: 16.52 seconds.

### 2.2 Test Results by Module

| Test Module | Tests | Passed | Failed | Key Areas Verified |
| :--- | :---: | :---: | :---: | :--- |
| `backend/tests/test_adult.py` | 11 | 11 | 0 | JPEG/PNG signatures, corrupt image rejection, min dimensions (224x224), max dimension limits, decompression bomb guard, Candidate Exp B ONNX inference |
| `backend/tests/test_auth.py` | 10 | 10 | 0 | Registration, unique constraints, Argon2id login, JWT expiration, refresh token rotation, logout cookie clearing |
| `backend/tests/test_dashboard_history.py` | 3 | 3 | 0 | Stats user isolation, submission history pagination and deletion, genus/date search filters |
| `backend/tests/test_database_migrations.py` | 1 | 1 | 0 | Alembic migration execution from base to head on fresh SQLite instance |
| `backend/tests/test_model_parity.py` | 3 | 3 | 0 | Manifest SHA-256 matching, Android bundled model parity, FP32 vs INT8 prediction agreement |
| `backend/tests/test_model_registry.py` | 3 | 3 | 0 | Metadata schema retrieval, version tags, model file checksum health checks |
| `backend/tests/test_password_reset.py` | 9 | 9 | 0 | Token generation, SHA-256 hashing, 15m expiration, single-use enforcement, session revocation, enumeration defense, token log masking |
| `backend/tests/test_rate_limit.py` | 6 | 6 | 0 | Under-limit allowance, over-limit blocking, multithreaded concurrency, window expiry, Redis failure fallback, API login rate limits |
| `backend/tests/test_security.py` | 9 | 9 | 0 | Path traversal blocking, cross-user isolation, invalid/expired JWT, RBAC admin enforcement, SQL injection payloads, XSS filename escaping, CSRF Bearer validation |
| `backend/tests/test_video_validation.py` | 16 | 16 | 0 | Video duration limits (2.99s, 3.00s, 4.00s, 5.00s, 5.01s), corrupted containers, truncated streams, variable frame rate, Celery async background dispatch |
| **Total** | **71** | **71** | **0** | **Overall Pass Rate: 100%** |

---

## 3. Web Frontend Regression Suite

### 3.1 Execution Details
- Framework: Node.js test runner (`node --experimental-strip-types --test src/__tests__/*.test.ts`).
- Directory: `web/`
- Execution Time: 414 ms.

### 3.2 Test Results Breakdown

| Test Suite | Tests | Passed | Failed | Verification Description |
| :--- | :---: | :---: | :---: | :--- |
| `auth-and-history.test.ts` | 4 | 4 | 0 | Token store lifecycle (login sets token, logout clears), history filtering by type, search filtering by genus or ID, larvae model contract enforcement (`model_not_validated`) |
| `video-validation.test.ts` | 6 | 6 | 0 | Client video duration boundary checks (2.99s rejected, 3.00s accepted, 4.00s accepted, 5.00s accepted, 5.01s rejected, zero/NaN duration rejected) |
| **Total** | **10** | **10** | **0** | **Overall Pass Rate: 100%** |

---

## 4. Android Mobile Regression Suite

### 4.1 Execution Details
- Framework: Gradle 8.9, Kotlin 2.0.21, JUnit 4, Robolectric.
- Directory: `android/`
- Command: `./gradlew test`

### 4.2 Test Results Breakdown

| Test Class | Variant | Tests | Passed | Failed | Description |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `ModelContractTest` | Debug | 4 | 4 | 0 | Model classes, 3 output probabilities, score summation to 1.0, float confidence |
| `ModelContractTest` | Release | 4 | 4 | 0 | Release bytecode contract verification with R8 optimization |
| `VideoRecordingRulesTest` | Debug | 4 | 4 | 0 | 3.0s minimum boundary, 5.0s maximum auto-stop, frame rate constraints |
| `VideoRecordingRulesTest` | Release | 4 | 4 | 0 | Release bytecode verification for recording limits |
| `ImageQualityValidatorTest` | Debug | 1 | 1 | 0 | Aspect ratio and image resolution rules |
| `ImageQualityValidatorTest` | Release | 1 | 1 | 0 | Release bytecode verification for image quality |
| **Total** | | **18** | **18** | **0** | **Overall Pass Rate: 100%** |

---

## 5. Docker Compose Live Integration Testing

### 5.1 Service Environment
The production Docker Compose topology was running:
- `vectora-postgres`: PostgreSQL 16 Alpine (healthy).
- `vectora-redis`: Redis 7 Alpine (healthy, port 6379 mapped).
- `vectora-backend`: Mosqscan FastAPI Backend (healthy, port 8000 mapped).
- `vectora-video-worker`: Celery 5.4 / FFmpeg 6.1 (healthy).

### 5.2 Test Scenarios (`test_live_docker.py`)
1. **Unauthorized Access**: Confirmed unauthenticated requests to `/api/v1/auth/me` return HTTP 401.
2. **User Registration**: Created new field researcher account via `/api/v1/auth/register` (HTTP 201).
3. **User Authentication**: Obtained JWT access token via `/api/v1/auth/login` (HTTP 200).
4. **Profile Access**: Retrieved authenticated user profile matching registration email (HTTP 200).
5. **Adult Mosquito Identification**:
   - Submitted test image `model-registry/golden-tests/images/aedes_01.jpg`.
   - Backend processed image with `vectora_candidate_exp_b.onnx`.
   - Correctly identified top genus `aedes` (HTTP 201).
6. **Larvae Video Job Processing**:
   - Generated synthetic 3.5-second test video via FFmpeg.
   - Submitted to `/api/v1/larvae/submit` (HTTP 202).
   - Celery video worker processed 105 frames.
   - Status polled: `queued` -> `processing` -> `completed` within 3 seconds.
   - Model status correctly enforced contract: `model_not_validated` with `result: null`.
7. **Cross-User Tenant Isolation**:
   - Created second independent user.
   - Attempted access to User 1's larvae job: HTTP 403 Forbidden.
   - Attempted access to User 1's adult submission: HTTP 403 Forbidden.
8. **Live Rate Limiting & Password Reset**:
   - Password reset request returned HTTP 200 generic message.
   - Sixth failed login attempt returned HTTP 429 Too Many Requests.

---

## 6. Model Registry Integrity

Execution of `bash model-registry/verify_checksums.sh`:
- FP32 Model (`vectora-ai-starter/models/efficientnet_b0.onnx`):
  `03fc58fd99578b756415ca50a8cc8b702e7e98ad248cfe0215f836e1652b0d19` — OK.
- INT8 Model (`vectora-ai-starter/models/efficientnet_b0_int8.onnx`):
  `bac40d9af5441ddbdb6c6b19348fe04167ca4d8de7466611742022b7f505bd95` — OK.
- Overall: 2 passed, 0 failed.

---

## 7. Known Environment Warnings

The following non-blocking deprecation warnings were observed during testing:
1. `pytest_asyncio`: Missing `asyncio_default_fixture_loop_scope` setting defaults to fixture scope.
2. `starlette.testclient`: Deprecation warning for passing `cookies` per request.
3. `StarletteDeprecationWarning`: `HTTP_422_UNPROCESSABLE_ENTITY` recommended replacement is `HTTP_422_UNPROCESSABLE_CONTENT`.
4. `OpenJDK 21`: Native library access warnings during Gradle build.
5. `Physical Device Status`: Device `R9ZRB0DE85Y` (Samsung Galaxy Tab A7 Lite SM-T225) is authorized. The release APK was installed (`Success`), launched, camera preview verified, and offline inference executed without native crashes following ProGuard rule remediation.
