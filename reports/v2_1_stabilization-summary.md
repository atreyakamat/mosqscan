# Vectora AI 2.1 — Software Stabilization Summary

## 1. Milestone Overview

Vectora AI 2.1 is the Software Stabilization Milestone.
The primary objectives were:
1. Remediate critical backend security gaps.
2. Resolve machine learning model registry and configuration inconsistencies.
3. Establish production-ready Android mobile release packaging.
4. Execute full system regression tests across all components.

All development adhered strictly to milestone constraints:
- Existing models were not retrained.
- Core applications were not rebuilt from scratch.
- Existing historical audit reports were preserved.
- No secrets or credentials were committed to source control.

---

## 2. Resolved Production Blockers

### 2.1 Security Remediations (P0)

#### SEC-GAP-01: Distributed Rate Limiting
- **Issue**: Authentication routes lacked distributed rate limiting, leaving login and token endpoints vulnerable to brute-force credential stuffing and denial-of-service attacks.
- **Solution**: Implemented an atomic Redis Lua sliding-window rate limiter in `backend/app/core/rate_limit.py`. Configured limits to 5 attempts per 15-minute window for `/auth/login` and `/auth/password-reset`.
- **Fault Tolerance**: Implemented a thread-safe in-memory sliding window that activates automatically if Redis fails.
- **Verification**: 6 automated unit/integration tests and live Docker container validation confirmed rate limiting behavior.

#### SEC-GAP-02: Password Reset Workflow
- **Issue**: Password reset was completely missing from the API and data model.
- **Solution**:
  - Added the `PasswordResetToken` database table and Alembic migration `2026_11_12_c01a2b3c4d5e`.
  - Implemented 256-bit cryptographically secure token generation (`secrets.token_urlsafe(32)`).
  - Stored only SHA-256 hashes in the database; raw tokens are never persisted.
  - Enforced a 15-minute expiration window and single-use validation.
  - Revoked all existing user refresh tokens immediately upon password reset to terminate active sessions.
  - Neutralized user enumeration attacks by returning an identical generic response regardless of whether the email exists.
  - Masked reset tokens in logging systems.
- **Verification**: 9 automated tests and live Docker tests verified all constraints.

### 2.2 Model Registry and Threshold Consistency (P1)

#### Model Manifest v1.1
- **Issue**: Previous documentation conflated baseline models with Candidate Exp B and lacked authoritative checksum records.
- **Solution**: Upgraded `model-registry/manifest.json` to schema version 1.1:
  - Explicitly separated deployed baseline models (`efficientnet_b0.onnx`, `efficientnet_b0_int8.onnx`) from the Candidate Exp B research model (`vectora_candidate_exp_b.onnx`).
  - Recorded exact SHA-256 checksums, input tensor shapes (`[1, 3, 224, 224]`), and class index mappings (`0: aedes`, `1: anopheles`, `2: culex`).

#### Threshold Standardization and PRD Discrepancy
- **Issue**: A discrepancy existed between the PRD specification (0.70 threshold) and model validation results. Hardcoded threshold values prevented adjustment.
- **Solution**:
  - Replaced hardcoded values with `settings.CONFIDENCE_THRESHOLD = 0.65` in `backend/app/config.py` and `backend/app/inference/adult_classifier.py`.
  - Documented the rationale for the discrepancy: Candidate Exp B tuning demonstrated that 0.65 achieves an optimal balance between precision (0.89) and recall (0.86) on real field imagery, whereas 0.70 caused excessive false-negative "uncertain" classifications.
  - Removed misleading claims of "calibrated softmax confidence" from the web application interface (`web/src/app/page.tsx`), clarifying that outputs represent uncalibrated softmax scores.

### 2.3 Android Release Readiness (P1)

#### Secure Signing Architecture
- Configured `android/app/build.gradle.kts` to load release keystore credentials from external environment variables, `android/signing.properties`, or Gradle properties.
- Keystore file generated outside the project workspace in `/home/nimr/.android/vectora_release.keystore`.
- Source control ignore files (`.gitignore`) configured to prevent accidental credential commits.
- Verified v2 APK signing using Android SDK `apksigner`.

#### Binary Footprint Optimization & ProGuard Rules
- Implemented ABI splits for `arm64-v8a`, `armeabi-v7a`, `x86`, and `x86_64`.
- The production ARM64 APK (`app-arm64-v8a-release.apk`) measures 26 MB, representing a 67% size reduction compared to the 79 MB universal binary.
- Configured `noCompress += listOf("onnx")` to ensure `assets/efficientnet_b0_int8.onnx` is stored uncompressed (0% compression ratio).
- Created `android/app/proguard-rules.pro` keeping `ai.onnxruntime.**` and model classes. This resolved a fatal native JNI crash (`SIGABRT` in `ai.onnxruntime.OrtSession.run`) where R8 bytecode minimization stripped reflection symbols required by the ONNX C++ runtime.

#### Device State Transparency & Hardware Verification
- Verified connected physical hardware: Samsung Galaxy Tab A7 Lite (`SM_T225`, ARM64, device `R9ZRB0DE85Y`).
- Successfully installed signed release APK (`adb install -r app-arm64-v8a-release.apk`).
- Verified application launch, runtime camera/audio permissions, Camera preview initialization, and offline ONNX model inference without native crashes.
- Documented complete step-by-step physical test protocol for field engineers covering permissions, offline inference, video duration bounds, local SQLite history, and cloud sync.

---

## 3. Regression Test Summary

| Subsystem | Test Harness | Total Tests | Passed | Failed | Pass Rate |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Backend API & Core** | Pytest 9.2.0 | 71 | 71 | 0 | 100% |
| **Web Frontend** | Node.js Test Runner | 10 | 10 | 0 | 100% |
| **Android Unit** | Gradle JUnit 4 | 18 | 18 | 0 | 100% |
| **Live Docker Integration** | Python HTTPX Integration Suite | 8 | 8 | 0 | 100% |
| **Model Verification** | Shell Checksum Validator | 2 | 2 | 0 | 100% |
| **Total** | | **109** | **109** | **0** | **100%** |

---

## 4. Open Blockers for Vectora AI 3.0

The following technical limitations remain outside the 2.1 stabilization scope and must be addressed in Milestone 3.0:

1. **Absence of Object Detection (YOLO Detector)**:
   - *Current State*: Both mobile and backend inference execute whole-image classification. If a mosquito occupies only a small portion of the frame or background clutter is high, accuracy degrades.
   - *Requirement for 3.0*: Integrate a lightweight YOLO/SSD detector to crop the specimen bounding box prior to classification.

2. **Limited Golden Evaluation Dataset**:
   - *Current State*: The model registry golden test suite contains only 44 images across three mosquito genera.
   - *Requirement for 3.0*: Expand the evaluation dataset to at least 1,000 verified field specimens across varied geographic regions and lighting conditions to establish statistical confidence.

3. **Field Entomology Validation in Remote Conditions**:
   - *Current State*: Physical device `R9ZRB0DE85Y` was authorized and successfully verified for installation, application launch, camera preview, and on-device inference without crashes. However, testing was performed under indoor laboratory conditions.
   - *Requirement for 3.0*: Complete end-to-end field testing on physical hardware under diverse outdoor sunlight, humidity, and remote field conditions with live entomological specimens.

