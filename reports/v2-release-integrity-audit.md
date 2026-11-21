# VECTORa AI — MASTER RELEASE INTEGRITY AUDIT (v2.0)

**Document:** `reports/v2-release-integrity-audit.md`  
**Date:** November 11, 2026  
**Auditor:** Senior Software Architect, Security Engineer, ML Quality Lead  
**Final Release Verdict:** **`REJECTED FOR PRODUCTION RELEASE — RELEASE BLOCKERS OPEN`**

---

## 1. Executive Summary & Verdict

This Master Release Integrity Audit evaluates the full Vectora AI 2.0 software suite: the native Android application, the responsive Next.js web application, the FastAPI backend platform, the shared ONNX inference pipeline, and the model registry.

### Core Audit Verdict: **NOT READY FOR PRODUCTION DEPLOYMENT**
While the software engineering foundation is robust (all 56 backend tests, 10 web unit tests, and 18 Android unit test executions pass with zero failures, and production builds compile cleanly), the product **CANNOT be approved for production release** due to critical machine learning and infrastructure gating factors:
1. **Model Dataset Size:** The deployed adult classifier is trained on only **44 original museum photographs**. It achieves poor uncalibrated performance (max confidence on field specimens is ~50%).
2. **Missing Specimen Localization (YOLO):** No object detection network exists to isolate mosquitoes from background clutter.
3. **Unvalidated Larvae Model:** The larvae classification network has not been evaluated against entomological ground truth and correctly remains disabled (`model_not_validated`).
4. **Physical Android Device Untested:** No physical Android smartphone was connected to ADB (`adb devices` was empty); camera sensor and autofocus behavior remain unverified on hardware.
5. **Security Gaps:** Rate limiting is currently stored in-memory rather than Redis, and password reset is a stub.

---

## 2. Model Artifact Consistency & Lineage Audit

Detailed analysis is documented in [`reports/v2-model-consistency.md`](file:///home/nimr/Projects/mosqscan/reports/v2-model-consistency.md).

### 2.1 Artifact Lineage Resolution
The inquiry regarding checksum differences between the deployed models and proposed Exp B candidate is resolved:
- **Deployed Models:**
  - **FP32 ONNX (Backend):** [`efficientnet_b0.onnx`](file:///home/nimr/Projects/mosqscan/vectora-ai-starter/models/efficientnet_b0.onnx) (`SHA-256: 03fc58fd99578b756415ca50a8cc8b702e7e98ad248cfe0215f836e1652b0d19`)
  - **INT8 ONNX (Android Mobile):** [`efficientnet_b0_int8.onnx`](file:///home/nimr/Projects/mosqscan/android/app/src/main/assets/efficientnet_b0_int8.onnx) (`SHA-256: bac40d9af5441ddbdb6c6b19348fe04167ca4d8de7466611742022b7f505bd95`)
  - **Provenance:** Exported directly from the **Baseline checkpoint** (`vectora-ai-starter/models/efficientnet_b0_best.pt`, frozen feature extractor).
- **Candidate Exp B Models:**
  - **FP32 ONNX:** [`vectora_candidate_exp_b.onnx`](file:///home/nimr/Projects/mosqscan/models/vectora_candidate_exp_b.onnx) (`SHA-256: d644b9cd9c952d461bbfbb44e8b1926cdcf9bbbfb9cd43f85065cbed0d7b1499`)
  - **INT8 ONNX:** [`vectora_candidate_exp_b_int8.onnx`](file:///home/nimr/Projects/mosqscan/models/vectora_candidate_exp_b_int8.onnx) (`SHA-256: 6d7e830699f4ca3f3b67c538c2f77a592f88288845dfa00d94c7837ccef68803`)
  - **Provenance:** Exported from `vectora-ai-starter/experiments/exp_B_unfreeze_stage7_8_best.pt` (unfrozen stages 7 and 8).

> [!CAUTION]
> The deployed artifacts are **different model weights**, not intentional re-exports. Max absolute logit difference is `0.0566`. Backend and Android are currently synchronized on the Baseline model pair (`03fc58fd...` and `bac40d9a...`). Do not promote Exp B without updating both platforms simultaneously.

### 2.2 Numerical Prediction Comparison on Ground-Truth Specimens

| Specimen | Ground Truth | Baseline FP32 (`03fc...`) | Baseline INT8 (`bac4...`) | Candidate Exp B FP32 (`d644...`) | Candidate Exp B INT8 (`6d7e...`) |
|---|---|---|---|---|---|
| `Aedes_aegypti_1.jpg` | *Aedes* | **Aedes (50.1%)** | **Aedes (40.0%)** | **Aedes (44.2%)** | **Aedes (38.6%)** |
| `Anopheles_stephensi_1.jpg` | *Anopheles* | Culex (45.8%) ❌ | **Anopheles (36.8%)** ✅ | Culex (50.5%) ❌ | **Anopheles (40.4%)** ✅ |
| `Culex_quinquefasciatus_1.jpg` | *Culex* | Aedes (40.8%) ❌ | **Culex (40.0%)** ✅ | Aedes (38.4%) ❌ | Aedes (35.7%) ❌ |
| `Aedes_aegypti_10.jpg` | *Aedes* | **Aedes (41.7%)** | **Aedes (36.0%)** | **Aedes (41.2%)** | Anopheles (38.9%) ❌ |
| `Anopheles_stephensi_5.jpg` | *Anopheles* | Aedes (40.5%) ❌ | **Anopheles (36.2%)** ✅ | Culex (38.9%) ❌ | **Anopheles (39.7%)** ✅ |
| `Culex_quinquefasciatus_10.jpg` | *Culex* | **Culex (44.1%)** | Aedes (36.2%) ❌ | **Culex (41.7%)** | Anopheles (36.7%) ❌ |

---

## 3. Inference Contract Consistency & Threshold Reconciliation

### 3.1 Threshold Conflict Resolution
- Discrepancy Found: `0.40` in training metrics report, `0.50` in `manifest.json` and `.env.example`, `0.65` in backend classifier, Android classifier, web UI, and documentation.
- **Resolution:**
  - **`0.65` is the authoritative safety threshold.** Predictions $< 0.65$ trigger `"Uncertain identification. Manual inspection is advised."`
  - Manifest and configuration files must align strictly to `0.65`.
  - **Strict Requirement:** Do not describe the threshold as calibrated. The model outputs uncalibrated softmax logits. Text in `web/src/app/page.tsx` claiming *"calibrated confidence thresholds"* is flagged for remediation.

### 3.2 Preprocessing Parity Check

| Preprocessing Step | Backend Python Engine | Android Kotlin Engine | Parity Status |
|---|---|---|:---:|
| Color Space | PIL `convert("RGB")` | Bitwise RGB extraction | **MATCH** |
| Dimensions | $224 \times 224$ pixels | $224 \times 224$ pixels | **MATCH** |
| Interpolation | Bilinear (`Resampling.BILINEAR`) | Bilinear (`createScaledBitmap(..., true)`) | **MATCH** |
| Normalization Mean | `[0.485, 0.456, 0.406]` | `floatArrayOf(0.485f, 0.456f, 0.406f)` | **MATCH** |
| Normalization Std | `[0.229, 0.224, 0.225]` | `floatArrayOf(0.229f, 0.224f, 0.225f)` | **MATCH** |
| Output Classes | `0: aedes, 1: anopheles, 2: culex` | `0: aedes, 1: anopheles, 2: culex` | **MATCH** |
| Softmax Exponentiation | Numerically stable max-subtraction | Numerically stable max-subtraction | **MATCH** |

---

## 4. Security Remediation Audit

Detailed analysis is documented in [`reports/v2-security-remediation.md`](file:///home/nimr/Projects/mosqscan/reports/v2-security-remediation.md).

| Control Area | Implementation Mechanism | Test Assertion | Audit Finding |
|---|---|---|:---:|
| **CSRF Validation** | State-changing routes require `Authorization: Bearer <JWT>` header | `test_csrf_protection_requires_bearer_token` | **PASS** |
| **Rate Limiting** | Sliding window counter in `_rate_limit_store` | Indirectly via `test_auth.py` | **GAP** (In-memory dict, not Redis) |
| **Password Reset** | `POST /api/v1/auth/password-reset` returns constant message | Untested | **INCOMPLETE** (Stub only) |
| **Refresh Rotation** | Revokes old token, issues new refresh cookie | `test_refresh_token_rotation` | **PASS** |
| **Token Reuse Revocation** | Reusing revoked token terminates all user sessions | `test_refresh_token_rotation` (phase 2) | **PASS** |
| **Cookie Security** | `HttpOnly`, `Secure`, `SameSite=Lax`, path-scoped | `test_login_success` | **PASS** |
| **Cross-User Isolation** | Validates `submission.user_id == current_user.id` | `test_cross_user_submission_access_forbidden` | **PASS** |

---

## 5. API Contract Reconciliation

### 5.1 Authoritative Contract Status
- **Authoritative Specification:** [`docs/openapi.json`](file:///home/nimr/Projects/mosqscan/docs/openapi.json) (28 routes total).
- **Backend FastAPI Routes:** Exactly 28 endpoints matching `docs/openapi.json` with zero missing paths or method mismatches.
- **Web API Client ([`web/src/lib/api.ts`](file:///home/nimr/Projects/mosqscan/web/src/lib/api.ts)):** Maps cleanly to all 28 backend endpoints.
- **Android Client ([`SyncManager.kt`](file:///home/nimr/Projects/mosqscan/android/app/src/main/java/com/vectora/ai/sync/SyncManager.kt)):** Operates in local offline mode via Room DB. Cloud sync network transport is not wired to Retrofit HTTP routes.

---

## 6. Test Suite Reconciliation

Detailed analysis is documented in [`reports/v2-cross-platform-verification.md`](file:///home/nimr/Projects/mosqscan/reports/v2-cross-platform-verification.md).

### 6.1 Test Count Resolution (44 vs 56)
- **Discrepancy:** Report previously mentioned both 44 and 56 tests.
- **Resolution:** 44 was the baseline test count; 12 security, migration, and boundary tests were added subsequently. Section 12 subheader was updated to reflect the full 56 tests.

### 6.2 Test Execution Results

```text
======================= TEST SUITE EXECUTION SUMMARY =======================
Backend Tests:  PYTHONPATH=backend pytest backend/tests -v
                --> 56 passed, 0 failed in 9.56s
                (15 Unit Tests, 41 Integration Tests)

Web Tests:      cd web && npm test
                --> 10 passed, 0 failed in 262ms

Android Tests:  cd android && ./gradlew test
                --> 18 passed (9 Debug, 9 Release), 0 failed in 4s

Model Checksum: bash model-registry/verify_checksums.sh
                --> 2 passed, 0 failed (FP32 & INT8 SHA-256 intact)
=============================================================================
```

---

## 7. Android Hardware & Packaging Audit

- **Physical Device Check:** `adb devices` $\rightarrow$ empty. **No physical device verification claimed.**
- **Release Packaging:**
  - `cd android && ./gradlew assembleRelease` $\rightarrow$ `BUILD SUCCESSFUL in 3m 15s`.
  - Release APK: [`android/app/build/outputs/apk/release/app-release-unsigned.apk`](file:///home/nimr/Projects/mosqscan/android/app/build/outputs/apk/release/app-release-unsigned.apk).
  - APK Size: **78 MB** (reduced from 137 MB Debug APK via R8 minification).
  - Architecture: **Fat universal APK** containing 4 ABIs (`arm64-v8a`, `armeabi-v7a`, `x86`, `x86_64`). ABI splitting is recommended for Play Store release (~22 MB per device).

---

## 8. Machine Learning Safety Verification

1. **YOLO Specimen Detection:** Inspection confirms **zero YOLO code exists in the repository**. Gated as an open blocker (`BLK-01`).
2. **Non-Mosquito Rejection:** The classifier is a closed 3-class model. Rejection is handled strictly via the $< 0.65$ uncertainty threshold.
3. **Larvae Classification:** Returns `prediction: null` and `status: "model_not_validated"`. No fake predictions.
4. **Experimental Disclaimer:** All interfaces display field inspection disclaimers.

---

## 9. Git & Release Management Status

- **Repository Root:** `/home/nimr/Projects/mosqscan` is **NOT a git repository**. Subdirectories `vectora-ai-starter/` and `web/` contain independent git repositories.
- **Branching Action:** In strict accordance with execution instructions ("Do not commit changes without approval"), **no git commits or repository modifications were forced**.

---

## 10. Master Requirements & Release Blockers Matrix

### Requirements Status

| Category | Requirement | Status | Notes |
|---|---|:---:|---|
| **Platform** | Native Android application with CameraX | **PASS** | Compiles, packages, passes unit tests |
| **Platform** | Responsive Next.js 15 web platform | **PASS** | Prerenders 12 static routes, passes unit tests |
| **Platform** | Unified FastAPI backend | **PASS** | 28 endpoints with OpenAPI parity, passes 56 tests |
| **Platform** | Offline mobile inference | **PASS** | Bundled `efficientnet_b0_int8.onnx` via ONNX Runtime Mobile |
| **Video** | Strict 3.0s–5.0s validation (no trimming) | **PASS** | Validated on backend and web with 10 test boundaries |
| **Video** | Android 3s manual stop, 5s auto stop | **PASS** | Enforced in `VideoRecordingRules.kt` |
| **Larvae** | Honest unvalidated status | **PASS** | Returns `model_not_validated`, prediction `null` |
| **Security** | Refresh-token rotation & reuse detection | **PASS** | Validated via `test_refresh_token_rotation` |
| **Security** | BOLA / cross-user data isolation | **PASS** | Validated via `test_cross_user_submission_access_forbidden` |
| **Security** | Redis-backed rate limiting | **FAIL / GAP** | Implemented using in-memory dict (`SEC-GAP-01`) |
| **Security** | Complete password reset workflow | **INCOMPLETE** | Stub endpoint only (`SEC-GAP-02`) |
| **AI** | Model field validation | **FAIL / BLOCKED** | 44-image pilot baseline; max confidence ~50% |
| **AI** | YOLO specimen detector | **INCOMPLETE** | Missing from codebase (`BLK-01`) |
| **Hardware**| Physical camera hardware verification | **INCOMPLETE** | No Android device connected (`BLK-04`) |

---

### Master Release Blockers Table

| Blocker ID | Domain | Severity | Description | Resolution Requirement |
|---|---|:---:|---|---|
| **`BLK-01`** | ML Architecture | **Critical** | Missing YOLO specimen detector | Implement object detection network to crop specimen region |
| **`BLK-02`** | ML Generalization | **Critical** | Model trained on only 44 images | Retrain EfficientNet on multi-site field dataset with >1,000 specimens |
| **`BLK-03`** | AI Parity Drift | **High** | Deployed models are Baseline, not Exp B | Standardize candidate promotion and dual-platform asset deployment |
| **`BLK-04`** | Hardware Verification | **High** | Physical Android device unverified | Run CameraX capture and 5s auto-stop on physical handset |
| **`BLK-05`** | Security | **Medium** | Rate limiter uses in-memory store | Connect `check_login_rate_limit` to Redis cluster |
| **`BLK-06`** | Security | **Medium** | Password reset is a stub | Implement reset token database model and confirmation route |

---

## 11. Conclusion & Audit Sign-Off

The Vectora AI 2.0 release integrity audit is complete. All existing artifacts, models, checkpoints, and reports have been preserved. In strict accordance with the instructions, **the audit process has concluded and production readiness is explicitly withheld** until the 6 release blockers above are resolved.
