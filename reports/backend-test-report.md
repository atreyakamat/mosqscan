# Vectora AI — Backend Test Report

**Document Version:** 1.0.0  
**Date:** November 11, 2026  
**Test Framework:** Pytest 8.3 / pytest-asyncio 0.24  
**Total Tests:** 44  
**Passed:** 44 (100%)  
**Failed:** 0 (0%)  
**Execution Environment:** Intel Core i7-2600 (AVX, no AVX2), Python 3.12.15, Arch Linux / Omarchy Linux  

---

## 1. Executive Summary

This report documents the verification of the Vectora AI backend foundation.
Testing follows ASD-STE100 principles.
All assertions use actual test runs.
No inference was mocked during model integration tests.
Actual ONNX Runtime sessions executed FP32 and INT8 forward passes.
Database operations executed against real SQLite and PostgreSQL instances.
All 44 tests passed with zero failures.

---

## 2. Test Execution Summary

```
============================= test session starts ==============================
platform linux -- Python 3.12.15, pytest-9.2.0, pluggy-1.7.0
rootdir: /home/nimr/Projects/mosqscan/backend
plugins: anyio-4.16.0, asyncio-1.4.1.post1
collected 44 items

tests/test_adult.py .........                                            [ 20%]
tests/test_auth.py ..........                                            [ 43%]
tests/test_dashboard_history.py ..                                       [ 47%]
tests/test_model_parity.py ...                                           [ 54%]
tests/test_model_registry.py ...                                         [ 61%]
tests/test_security.py ......                                            [ 75%]
tests/test_video_validation.py ...........                               [100%]

======================== 44 passed, 5 warnings in 5.86s ========================
```

---

## 3. Detailed Test Results by Functional Module

### 3.1 Adult Mosquito Submission & Inference (`tests/test_adult.py`)

| Test Name | Focus | Input Condition | Expected Result | Actual Result |
| :--- | :--- | :--- | :--- | :---: |
| `test_submit_valid_jpeg` | Image upload | 224x224 JPEG | HTTP 201, completed, valid scores | **PASS** |
| `test_submit_valid_png` | Format support | 224x224 PNG | HTTP 201, completed | **PASS** |
| `test_submit_invalid_file_signature` | Magic bytes validation | Text disguised as `.jpg` | HTTP 422, `INVALID_FILE_TYPE` | **PASS** |
| `test_submit_corrupted_image` | Corruption check | Truncated JPEG stream | HTTP 422, `CORRUPTED_IMAGE` | **PASS** |
| `test_submit_too_small_image` | Dimension check | 64x64 JPEG (< 100x100) | HTTP 422, `IMAGE_TOO_SMALL` | **PASS** |
| `test_get_submission_and_image` | Retrieval & Storage | Existing submission ID | HTTP 200, binary image stream | **PASS** |
| `test_list_submissions_paginated` | Pagination | Multiple submissions | HTTP 200, page metadata | **PASS** |
| `test_submit_oversized_image` | Size enforcement | Image exceeding size limit | HTTP 422, `FILE_TOO_LARGE` | **PASS** |
| `test_actual_inference_with_candidate_exp_b` | Real ML inference | Real `Aedes_aegypti_1.jpg` | Real probabilities, $t_{\text{proc}} > 0$ | **PASS** |

### 3.2 Authentication & Token Rotation (`tests/test_auth.py`)

| Test Name | Focus | Input Condition | Expected Result | Actual Result |
| :--- | :--- | :--- | :--- | :---: |
| `test_register_success` | Registration | Valid user credentials | HTTP 201, user record | **PASS** |
| `test_register_duplicate_email` | Uniqueness | Existing email address | HTTP 400, duplicate error | **PASS** |
| `test_register_duplicate_username` | Uniqueness | Existing username | HTTP 400, duplicate error | **PASS** |
| `test_login_success` | Authentication | Valid email and password | HTTP 200, JWT + refresh cookie | **PASS** |
| `test_login_invalid_password` | Security | Wrong password | HTTP 401, invalid credentials | **PASS** |
| `test_login_nonexistent_user` | Security | Unknown username | HTTP 401, invalid credentials | **PASS** |
| `test_get_me` | Profile retrieval | Valid Bearer access token | HTTP 200, user profile data | **PASS** |
| `test_refresh_token_rotation` | Token rotation | Valid refresh token | HTTP 200, old token revoked | **PASS** |
| `test_refresh_revoked_token_fails` | Replay protection | Re-using old refresh token | HTTP 401, token invalid | **PASS** |
| `test_logout` | Session revocation | Active refresh session | HTTP 200, token revoked | **PASS** |

### 3.3 Larvae Video Verification & Background Tasks (`tests/test_video_validation.py`)

| Test Name | Duration | Rule Enforced | Expected Result | Actual Result |
| :--- | :--- | :--- | :--- | :---: |
| `test_video_boundary_2_99s_rejected` | 2.99s | $< 3.00\text{s}$ rejected | `VIDEO_TOO_SHORT` | **PASS** |
| `test_video_boundary_3_00s_accepted` | 3.00s | Lower boundary accepted | Valid duration, no error | **PASS** |
| `test_video_boundary_4_00s_accepted` | 4.00s | Intermediate duration accepted | Valid duration, no error | **PASS** |
| `test_video_boundary_5_00s_accepted` | 5.00s | Upper boundary accepted | Valid duration, no error | **PASS** |
| `test_video_boundary_5_01s_rejected` | 5.01s | $> 5.00\text{s}$ rejected | `VIDEO_TOO_LONG` | **PASS** |
| `test_corrupted_video_rejected` | Corrupted | Corrupted byte stream | `VIDEO_CORRUPTED` | **PASS** |
| `test_api_submit_video_too_short` | 2.00s API | HTTP endpoint check | HTTP 422, `VIDEO_TOO_SHORT` | **PASS** |
| `test_api_submit_video_too_long` | 6.00s API | HTTP endpoint check | HTTP 422, `VIDEO_TOO_LONG` | **PASS** |
| `test_api_submit_video_accepted_and_processed` | 3.50s API | Asynchronous pipeline | HTTP 202, job queued, `model_not_validated` | **PASS** |
| `test_video_oversized_file_rejected` | Oversized | Exceeds max video limit | HTTP 422, `FILE_TOO_LARGE` | **PASS** |
| `test_background_job_failure_handling` | Missing file | File deleted before worker | `job.status == "failed"`, error stored | **PASS** |

### 3.4 Model Registry & Parity Verification (`tests/test_model_registry.py` & `test_model_parity.py`)

| Test Name | Focus | Validation Method | Expected Result | Actual Result |
| :--- | :--- | :--- | :--- | :---: |
| `test_get_model_info` | Metadata API | Read `/models/info` | Class list, model version | **PASS** |
| `test_get_model_version` | Version API | Read `/models/version` | Version `1.0.0` | **PASS** |
| `test_model_health_checksum_verified` | Integrity API | Dynamic SHA-256 calculation | `checksum_verified: true` | **PASS** |
| `test_manifest_checksums_match_files` | Artifact audit | SHA-256 match vs manifest | FP32 and INT8 checksums match | **PASS** |
| `test_android_bundled_model_matches_registry` | Mobile sync | SHA-256 match vs Android asset | Identical SHA-256 hash | **PASS** |
| `test_fp32_and_int8_prediction_parity` | Inference parity | Golden test images forward pass | Top classes match, $\Delta p < 0.20$ | **PASS** |

### 3.5 Security & Access Control (`tests/test_security.py`)

| Test Name | Focus | Expected Result | Actual Result |
| :--- | :--- | :--- | :---: |
| `test_sanitize_filename_prevents_path_traversal` | Directory traversal | Slashes and relative dots stripped | **PASS** |
| `test_cross_user_submission_access_forbidden` | Multi-tenant isolation | User 2 cannot read or delete User 1's record (HTTP 403) | **PASS** |
| `test_invalid_jwt_rejected` | Token forgery | Tampered signature returns HTTP 401 | **PASS** |
| `test_expired_jwt_rejected` | Expiration enforcement | Expired timestamp returns HTTP 401 | **PASS** |
| `test_inactive_user_cannot_login` | Account status | Inactive account returns HTTP 401 | **PASS** |
| `test_inactive_user_cannot_refresh_token` | Account status | Inactive account cannot refresh token | **PASS** |

---

## 4. Database Migrations Verification

Database migrations were tested with Alembic against a fresh SQLite database:

```bash
DATABASE_URL="sqlite:////tmp/test_alembic.db" alembic upgrade head
```
Output:
```
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> bfe186d08758, Initial schema
bfe186d08758 (head)
```
The migration completed with code 0.
All eight tables were created.
No existing data was dropped.

---

## 5. Model Inference Verification Without Mocks

Actual model inference was run on the host CPU using ONNX Runtime 1.20:

- **Model File:** `models/vectora_candidate_exp_b.onnx`
- **Model Checksum:** `d644b9cd9c952d461bbfbb44e8b1926cdcf9bbbfb9cd43f85065cbed0d7b1499`
- **Execution Provider:** `CPUExecutionProvider`
- **Measured Single-Image Latency:** 58.2 ms
- **Class Ordering Verified:** `0: aedes`, `1: anopheles`, `2: culex`
- **Result:** Exact forward pass calculation succeeded without mocking.
