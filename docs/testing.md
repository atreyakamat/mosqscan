# Vectora AI — Comprehensive Test Strategy & Verification Guide

## 1. Overview

Testing in Vectora AI is mandatory across all layers:
1. Backend REST API, Security, & In-Memory Logic
2. Exact Video Duration Boundaries (OpenCV Decoding)
3. Model Registry & Cross-Platform Parity
4. Web Next.js Production Compilation & Routing
5. Native Android Unit & Rules Verification

---

## 2. Test Execution Commands

### 2.1 Backend Test Suite (Pytest)
```bash
# Run all 40 backend tests with verbose output
PYTHONPATH=backend vectora-ai-starter/.venv/bin/pytest backend/tests -v
```

Test modules executed:
- `test_auth.py`: User registration, duplicate detection, Argon2id login, JWT decode, rotating refresh cookies, token reuse detection, logout, password validation.
- `test_security.py`: Cross-user data isolation (User 2 blocked from viewing User 1 submissions, images, and deletion), path traversal (`sanitize_filename`), expired JWT rejection, admin RBAC enforcement.
- `test_adult.py`: JPEG/PNG uploads, magic byte signature validation, dimension enforcement (≥ 100×100), corruption rejection, ONNX inference execution, threshold uncertainty.
- `test_video_validation.py`: Exact boundary verification:
  - `2.99s` $\rightarrow$ `VIDEO_TOO_SHORT`
  - `3.00s` $\rightarrow$ Accepted
  - `4.00s` $\rightarrow$ Accepted
  - `5.00s` $\rightarrow$ Accepted
  - `5.01s` $\rightarrow$ `VIDEO_TOO_LONG`
  - Corrupted media $\rightarrow$ `VIDEO_CORRUPTED`
- `test_dashboard_history.py`: Strict user isolation in stats, unified submissions history, pagination, deletion.
- `test_model_registry.py`: Manifest loading, version string, model health check, and SHA-256 integrity.
- `test_model_parity.py`: Simultaneous execution of FP32 server model and INT8 mobile model on golden reference images.

---

### 2.2 Model Parity & Golden Tests
```bash
# Verify checksums against manifest
bash model-registry/verify_checksums.sh

# Run model parity test
PYTHONPATH=backend vectora-ai-starter/.venv/bin/pytest backend/tests/test_model_parity.py -v
```

---

### 2.3 Web Application Build Verification
```bash
cd web
npm run build
```
Validates:
- Strict TypeScript compile without errors
- Next.js production bundle generation (12 static pages)
- Client-side duration validation logic in `video-validation.ts`

---

### 2.4 Android Test Suite
```bash
cd android
JAVA_HOME=/home/nimr/.local/share/mise/installs/java/17.0.21+9 ANDROID_HOME=/home/nimr/Android/Sdk ./gradlew test
```
Validates:
- `VideoRecordingRulesTest`: Exact 3.0s manual stop lock, 5.0s auto-stop enforcement, <3.0s rejection.
- `ModelContractTest`: Class labels `["aedes", "anopheles", "culex"]`, model version `1.0.0`, input size `224`, ImageNet mean/std constants, calibrated uncertainty logic.
