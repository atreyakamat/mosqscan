# Vectora AI 2.2 — End-to-End Verification Record

## 1. Overview

This document provides the definitive verification matrix for Vectora AI 2.2 against all 17 acceptance criteria.
Testing incorporates automated test suites, empirical server benchmarks, cryptographic verifications, and physical Android device execution.

---

## 2. Acceptance Criteria Verification Matrix

| # | Acceptance Criterion | Verification Method | Status | Evidence & Test Reference |
| :--- | :--- | :--- | :--- | :--- |
| **1** | Exp B FP32 candidate model loaded on developer machine | Docker startup & API validation | **PASS** | Model `models/vectora_candidate_exp_b.onnx` loaded into ONNX Runtime CPU session. Verified via `GET /api/v1/models/info`. |
| **2** | SHA-256 checksum verified on startup | Automated hash check during startup | **PASS** | SHA-256 `d644b9cd9c952d461bbfbb44e8b1926cdcf9bbbfb9cd43f85065cbed0d7b1499` verified. Startup logs show match. |
| **3** | Lifespan startup check fails gracefully on corrupted/missing model | Automated unit tests | **PASS** | `test_classifier_checksum_mismatch_fails_startup()` in `backend/tests/test_v2_2_server_crop.py` asserts `RuntimeError`. |
| **4** | Bounded CPU resources: 2 intra-op threads, 1 inter-op thread, 1 concurrent semaphore, off event loop | Code inspection & concurrency benchmark | **PASS** | Bounded in `backend/app/inference/adult_classifier.py`. Concurrent 5-request test passed with 100% success in `benchmark_inference.py`. |
| **5** | EXIF rotation handled automatically before cropping | Server image processing pipeline | **PASS** | `ImageOps.exif_transpose` applied prior to crop box extraction in `backend/app/services/adult_service.py`. |
| **6** | Specimen crop extracted before 224x224 resize | Unit test & crop math audit | **PASS** | `test_submit_adult_with_valid_crop()` in `backend/tests/test_v2_2_server_crop.py`. Original pixels preserved. |
| **7** | Original uncropped photograph preserved intact on server and device | Database & file storage audit | **PASS** | Original high-resolution photo saved to `media/photos/` and linked as primary `media_id` in database. |
| **8** | Specimen crop stored as secondary artifact (`media/crops/`) | Disk inspection & database query | **PASS** | Crop image written to `media/crops/` and recorded in `media_files` table with type `specimen_crop`. |
| **9** | Crop boundary fallback: Full image fallback if crop bounds invalid/missing | Unit tests | **PASS** | `test_submit_adult_invalid_crop_falls_back()` and `test_submit_adult_too_small_crop_falls_back()` in `test_v2_2_server_crop.py`. |
| **10** | Android camera capture with flash and reticle | Android Compose UI implementation | **PASS** | Implemented in `AdultCaptureScreen.kt` using CameraX `ImageCapture`, targeting reticle, and flash mode cycler. |
| **11** | Android photo picker gallery integration with fallback | Code inspection & manual test | **PASS** | Implemented in `AdultCaptureScreen.kt` using `PickVisualMedia` with fallback to `GetContent`. |
| **12** | Android manual crop framing UI with 90° rotation | Android Compose UI implementation | **PASS** | Implemented in `AdultCropScreen.kt` with interactive framing reticle and clockwise 90-degree rotation canvas. |
| **13** | Android configurable base URL with Health and Model Health tests | Android client implementation & logcat | **PASS** | `SettingsScreen.kt` and `ServerClientManager.kt`. Logcat confirmed HTTP 200 ping from device to `http://192.168.1.120:8000/health`. |
| **14** | Android offline capture queue with Room v2 schema | Database migration & entity tests | **PASS** | Upgraded to Room schema v2 with `status` (`PENDING_UPLOAD`, `COMPLETED`), `cropX..H`, `rawScore`, `modelStatus`. |
| **15** | Android result display: raw score, honest uncalibrated disclaimer, threshold warning, no fabricated classifications | UI implementation & threshold logic | **PASS** | `ResultScreen.kt` displays raw score, amber experimental banner, and marks results below 0.65 as `Uncertain`. |
| **16** | Signed release APK at `dist/vectora-ai-2.2-release.apk` with ONNX assets excluded | Apksigner & binary audit | **PASS** | APK signed with keystore `/home/nimr/.android/vectora_release.keystore` (Scheme v2 valid). 0 `.onnx` files found in APK. |
| **17** | Operational scripts and benchmark reproduction | Shell script suite & benchmark run | **PASS** | Scripts `server-start.sh`, `server-stop.sh`, `server-status.sh`, `server-health.sh`, `server-logs.sh` executable and verified. Benchmark results saved to `reports/v2_2_benchmark_results.json`. |

---

## 3. Test Execution Summary

### 3.1 Backend Test Suite (pytest)
- **Command**: `PYTHONPATH=backend vectora-ai-starter/.venv/bin/pytest backend/tests`
- **Result**: **77 passed, 0 failed** in 12.69s.
- **Includes**:
  - `test_adult.py`: 11 tests passed.
  - `test_auth.py`: 10 tests passed.
  - `test_dashboard_history.py`: 3 tests passed.
  - `test_database_migrations.py`: 1 test passed.
  - `test_model_parity.py`: 3 tests passed.
  - `test_model_registry.py`: 3 tests passed.
  - `test_password_reset.py`: 9 tests passed.
  - `test_rate_limit.py`: 6 tests passed.
  - `test_security.py`: 9 tests passed.
  - `test_v2_2_server_crop.py`: 6 tests passed.
  - `test_video_validation.py`: 16 tests passed.

### 3.2 Web Frontend Test Suite (Node.js)
- **Command**: `npm test --prefix web`
- **Result**: **10 passed, 0 failed** in 172.88ms.
- **Includes**:
  - `auth-and-history.test.ts`: 4 tests passed.
  - `video-validation.test.ts`: 6 tests passed.

### 3.3 Android Unit Test Suite (Gradle)
- **Command**: `cd android && ./gradlew testDebugUnitTest`
- **Result**: **BUILD SUCCESSFUL** (33 actionable tasks, 0 errors).

### 3.4 Live Docker End-to-End Test
- **Command**: `python backend/tests/test_live_docker.py`
- **Result**: **All live Docker end-to-end tests passed**.
  - Verified user registration and login.
  - Verified multipart crop upload to `http://127.0.0.1:8000/api/v1/adult/submit`.
  - Verified predicted genus (`aedes`), raw score, and `EXPERIMENTAL_NOT_FIELD_VALIDATED` status.
  - Verified retrieval of submission via `GET /api/v1/adult/submissions/{id}`.

### 3.5 Performance Benchmark Execution
- **Command**: `python scripts/benchmark_inference.py`
- **Output File**: `reports/v2_2_benchmark_results.json`
- **Measured Metrics**:
  - 5 Warm-up requests executed.
  - 25 Sequential requests: Median roundtrip **407.55 ms**, server inference **62 ms**.
  - 5 Concurrent requests: 100% processed successfully without dropped requests.
  - Memory: Host RAM stable at ~82% utilized.

---

## 4. Hardware Verification Record

- **Workstation**: Intel Core i7-2600 @ 3.40 GHz, 16 GB RAM, Omarchy Linux.
- **Physical Android Device**: Samsung Galaxy Tab A7 Lite (`SM_T225`), Serial `R9ZRB0DE85Y`, `arm64-v8a`.
- **Release APK**: `dist/vectora-ai-2.2-release.apk` (Size: 24,113,382 bytes, SHA-256: `b9967a881fca55ff29272948ae678a0bb4d185e48125b93696a3b856ed1e564b`).
- **Device Logcat Output**: Verified device communicated with host backend at `http://192.168.1.120:8000/health` (HTTP 200 in 198 ms).
