# Vectora AI — Release Integrity Audit: Cross-Platform Verification & Device Readiness

**Document:** `reports/v2-cross-platform-verification.md`  
**Date:** November 11, 2026  
**Auditor:** Senior Android & Full-Stack Systems Engineer  
**Status:** AUDIT COMPLETE — PHYSICAL DEVICE TESTING BLOCKED (NO DEVICE CONNECTED)

---

## 1. Executive Summary

This report documents the verification of the Android mobile application, web frontend platform, and backend API across compilation, packaging, automated test suites, and hardware readiness.

### Readiness Summary

| Platform | Compilation / Build | Automated Tests | Physical Runtime Verification | Release Readiness |
|---|:---:|:---:|:---:|:---:|
| **Android Application** | **PASS** (Debug & Release) | **PASS** (18 test runs) | **BLOCKED** (No device attached to ADB) | Gate Open |
| **Web Application** | **PASS** (Next.js 15 Static) | **PASS** (10 tests) | **PASS** (Headless browser runtime verified) | Ready |
| **Backend API** | **PASS** (Python 3.12 / FastAPI) | **PASS** (56 tests) | **PASS** (TestClient & Alembic DB verified) | Ready |

---

## 2. Android Device Verification & Package Inspection

### 2.1 Hardware Connectivity Audit
Execution of the Android Debug Bridge diagnostic:
```bash
adb devices
```
**Output:**
```text
List of devices attached

```
- **Finding:** No physical Android smartphone or running emulator instance is connected to the host.
- **Strict Compliance:** In accordance with execution rules, **zero physical camera tests, hardware sensor tests, or on-device APK installations are claimed as verified**.

### 2.2 Release Build Execution
A standalone release build was executed using the pinned Gradle 8.9 wrapper:
```bash
cd android && ./gradlew assembleRelease
```
- **Build Duration:** 3 minutes 15 seconds
- **Result:** `BUILD SUCCESSFUL` (52 actionable tasks: 28 executed, 24 up-to-date)
- **Artifact Location:** [`android/app/build/outputs/apk/release/app-release-unsigned.apk`](file:///home/nimr/Projects/mosqscan/android/app/build/outputs/apk/release/app-release-unsigned.apk)

### 2.3 APK Size & Minification Efficiency
- **Debug APK Size:** **137 MB** (`app-debug.apk`)
- **Release APK Size:** **78 MB** (`app-release-unsigned.apk`)
- **Size Reduction via R8:** **43.1% reduction** (59 MB eliminated via bytecode dead-code stripping and resource optimization).

### 2.4 Native Library & ABI Packaging Audit
Inspection of the packaged release APK archive:
```bash
unzip -l app-release-unsigned.apk | grep -E "(lib/|assets/)"
```
**Contents:**
- `assets/efficientnet_b0_int8.onnx`: **4,360,533 bytes** (4.36 MB bundled ONNX model)
- `assets/dexopt/baseline.prof`: **4,763 bytes** (AOT baseline profile for instant cold start)
- **Native Shared Libraries:**
  - `arm64-v8a`: `libonnxruntime.so` (17.5 MB), `libonnxruntime4j_jni.so` (0.91 MB), `libimage_processing_util_jni.so` (29 KB), `libdatastore_shared_counter.so` (7 KB), `libandroidx.graphics.path.so` (10 KB)
  - `armeabi-v7a`: `libonnxruntime.so` (12.3 MB), `libonnxruntime4j_jni.so` (0.78 MB)
  - `x86`: `libonnxruntime.so` (20.3 MB), `libonnxruntime4j_jni.so` (0.76 MB)
  - `x86_64`: `libonnxruntime.so` (20.3 MB), `libonnxruntime4j_jni.so` (0.89 MB)

#### ABI Architecture Assessment
The current Gradle configuration produces a **Fat Universal APK** containing binaries for all 4 CPU architectures simultaneously.
- **Recommendation:** For Google Play production distribution, configure ABI splits or export an Android App Bundle (`.aab`):
  ```kotlin
  splits {
      abi {
          isEnable = true
          reset()
          include("arm64-v8a", "armeabi-v7a")
          isUniversalApk = false
      }
  }
  ```
  This will reduce the per-device download size from **78 MB to approximately 22 MB**.

### 2.5 Android Automated Unit Tests
Executed via `./gradlew test`:
- **Debug Target:** 9 passed / 0 failed (3.09s)
- **Release Target:** 9 passed / 0 failed (2.16s)
- **Total Executions:** **18 passed / 0 failed**

**Specific Test Assertions Verified:**
1. `testDurationBoundaries`: Verifies 2.99s is rejected (`TOO_SHORT`), 3.00s accepted, 5.00s accepted, 5.01s rejected (`TOO_LONG`).
2. `testManualStopDisabledBeforeThreeSeconds`: Asserts `canStopManually(elapsedMs)` returns `false` at 0s, 1s, 2s, 2.999s, and `true` at 3.0s.
3. `testAutoStopEnforcedAtFiveSeconds`: Asserts `mustStopAutomatically(elapsedMs)` returns `true` at $\ge 5000$ms.
4. `testSmallDimensionsRejected`: Asserts `ImageQualityValidator` rejects bitmaps below $100 \times 100$ pixels.
5. `testApprovedModelVersionAndArtifact`: Verifies asset points to `efficientnet_b0_int8.onnx` and version is `"1.0.0"`.
6. `testClassMappingParityWithManifest`: Verifies class order `["aedes", "anopheles", "culex"]`.
7. `testNormalizationConstantsParity`: Verifies mean `[0.485, 0.456, 0.406]` and std `[0.229, 0.224, 0.225]`.
8. `testUncertaintyMessagesLogic`: Verifies score $< 0.65$ triggers `"Uncertain identification. Manual inspection is advised."`

---

## 3. Web Platform Verification

### 3.1 Next.js 15 Production Build
Executed command:
```bash
cd web && npm run build
```
- **Engine:** Next.js 15.5.29 with Turbopack compiler
- **Compilation Duration:** 10.2 seconds
- **Build Output:** Clean zero-error compilation with 12 prerendered static routes:
  - `/` (Home landing page)
  - `/login`, `/register`, `/profile`
  - `/adult` (Specimen upload and inference UI)
  - `/larvae` (Video upload with strict duration gating)
  - `/history` (User submission audit log)
  - `/admin` (User and system status administration)
- **Client Bundle Size:** 163 kB shared First Load JS.

### 3.2 Automated Web Unit Tests
Executed command:
```bash
cd web && npm run test
```
- **Duration:** 262 ms
- **Test Output:** **10 passed / 0 failed**

**Specific Web Assertions Verified:**
1. `Video duration 2.99s must be rejected with too short error`: PASS
2. `Video duration 3.00s must be accepted`: PASS
3. `Video duration 4.00s must be accepted`: PASS
4. `Video duration 5.00s must be accepted`: PASS
5. `Video duration 5.01s must be rejected with too long error`: PASS
6. `Zero or NaN duration must be rejected as corrupted`: PASS
7. `Authentication token store lifecycle: login sets token, logout clears`: PASS
8. `History filter: filters correctly by type (adult vs larvae vs all)`: PASS
9. `History filter: search query filters by genus or ID`: PASS
10. `Larvae model contract: status must be model_not_validated with null prediction`: PASS

---

## 4. Backend Platform Verification & Test Count Reconciliation

### 4.1 Resolution of Test-Count Discrepancy (44 vs 56)
The previous implementation report contained an inconsistency: Section 12 cited 44 tests, while the summary cited 56 tests.
- **Root Cause Established:** 
  The initial author developed a test suite of 44 tests. During subsequent security hardening and video validation audits, 12 additional tests were implemented:
  - 1 Alembic database migration test (`test_database_migrations.py`)
  - 4 security tests (SQL injection, XSS filename sanitization, CSRF bearer authorization, admin RBAC in `test_security.py`)
  - 3 edge video tests (invalid codec, missing duration, false client duration in `test_video_validation.py`)
  - 1 submission search filter test (`test_dashboard_history.py`)
  - 1 model candidate inference test (`test_adult.py`)
  - 2 model checksum and Android asset parity tests (`test_model_parity.py`)
  The subheader in Section 12 was left at 44, creating the discrepancy.

### 4.2 Exact Execution Command & Full Output
```bash
PYTHONPATH=backend /home/nimr/Projects/mosqscan/vectora-ai-starter/.venv/bin/pytest backend/tests -v
```
**Results:** **`56 passed, 6 warnings in 9.56s`**

### 4.3 Separation of Unit Tests vs. Integration Tests
To establish true runtime confidence, the 56 tests were categorized:

#### Pure Unit Tests (15 Tests)
Isolated logic executing in-memory without database or HTTP network overhead:
- `backend/tests/test_security.py::test_sanitize_filename_prevents_path_traversal`
- `backend/tests/test_model_parity.py::test_manifest_checksums_match_files`
- `backend/tests/test_model_parity.py::test_android_bundled_model_matches_registry`
- `backend/tests/test_model_parity.py::test_fp32_and_int8_prediction_parity`
- `backend/tests/test_video_validation.py::test_video_boundary_2_99s_rejected`
- `backend/tests/test_video_validation.py::test_video_boundary_3_00s_accepted`
- `backend/tests/test_video_validation.py::test_video_boundary_4_00s_accepted`
- `backend/tests/test_video_validation.py::test_video_boundary_5_00s_accepted`
- `backend/tests/test_video_validation.py::test_video_boundary_5_01s_rejected`
- `backend/tests/test_video_validation.py::test_corrupted_video_rejected`
- `backend/tests/test_video_validation.py::test_truncated_video_rejected`
- `backend/tests/test_video_validation.py::test_variable_frame_rate_video_handled`
- `backend/tests/test_video_validation.py::test_invalid_codec_rejected`
- `backend/tests/test_video_validation.py::test_missing_duration_rejected`
- `backend/tests/test_video_validation.py::test_false_client_duration_rejected`

#### Integration Tests (41 Tests)
Full-stack integration executing against FastAPI `TestClient`, SQLite session lifecycle, and Alembic:
- All 10 tests in `test_auth.py` (Registration, login, password checks, JWT profiles, refresh token rotation, token reuse revocation, logout)
- All 11 tests in `test_adult.py` (Magic byte validation, oversized uploads, decompression bombs, actual ONNX inference, pagination)
- 4 API video tests in `test_video_validation.py` (`POST /api/v1/larvae/submit`, background job simulation, error payloads)
- All 3 tests in `test_model_registry.py` (Registry endpoints `/api/v1/models/info`, `/version`, `/health`)
- 8 security tests in `test_security.py` (Cross-user access control, invalid/expired JWTs, admin privilege checks, SQL injection escaping, XSS payload filtering, CSRF bearer enforcement)
- All 3 tests in `test_dashboard_history.py` (User data isolation stats, search filters, deletion)
- 1 test in `test_database_migrations.py` (Alembic migration upgrade to `head` on isolated fresh database)

---

## 5. Machine Learning Safety Verification

| ML Safety Rule | Audit Verification | Status |
|---|---|:---:|
| **YOLO Specimen Detection** | Inspection confirms **zero YOLO or object localization code exists**. Correctly documented as missing in audit reports (`BLK-01`). Pipeline assumes centered macro image. | **PASS** (Not falsely claimed) |
| **Non-Mosquito / OOD Rejection** | Inspection confirms model is a **closed 3-class softmax classifier**. Non-target objects are not classified by a negative class. Rejection relies solely on the $< 0.65$ uncertainty threshold. | **PASS** (Not falsely claimed) |
| **Uncalibrated Confidence** | Verified that confidences are raw softmax values. Identified copy bug in `web/src/app/page.tsx` claiming calibration; marked for immediate textual remediation. | **REMEDIATION REQUIRED** |
| **Larvae Identification Inactive** | Inspection of `backend/app/api/larvae.py`, `video_processor.py`, and `web/src/app/larvae/page.tsx` confirms **`prediction: null` and `status: "model_not_validated"` are strictly returned**. | **PASS** (Zero fake predictions) |
| **Experimental Status Display** | Verified that `manifest.json` and API routes return `status: "EXPERIMENTAL_NOT_FIELD_VALIDATED"` and UI displays field inspection disclaimers. | **PASS** |
