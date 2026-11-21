# Vectora AI v2.0 — Final Implementation Report

**Date:** November 11, 2026  
**System:** Vectora AI  
**Version:** 2.0.0  
**Architectural Paradigm:** One model version (`1.0.0`), One inference contract, Two user interfaces (Native Android & Next.js Web Platform).

---

## 1. Files Created

### Backend & API (`backend/`)
- `backend/app/main.py`: FastAPI application entrypoint with middleware, CORS, lifespan model validation, and router registrations.
- `backend/app/config.py`: Pydantic settings loading configuration from environment variables with production defaults.
- `backend/app/dependencies.py`: FastAPI dependencies for DB sessions, authenticated user context, and admin role verification.
- `backend/app/core/security.py`: Argon2 password hashing, JWT creation/decoding with rotation, file sanitization.
- `backend/app/core/audit.py`: Security and diagnostic event audit logging to structured JSON files.
- `backend/app/core/exceptions.py`: Custom HTTP exceptions for auth, validation, model, and rate limits.
- `backend/app/db/base.py`: Declarative base for SQLAlchemy models.
- `backend/app/db/models.py`: Database entities: `User`, `Submission`, `AuditLog`, `RefreshToken`.
- `backend/app/db/session.py`: Async and sync engine/sessionmaker setup with connection pooling.
- `backend/app/schemas/auth.py`: Pydantic v2 schemas for registration, login, token refresh, and user profile.
- `backend/app/schemas/adult.py`: Pydantic v2 schemas for adult mosquito classification requests and responses.
- `backend/app/schemas/larvae.py`: Pydantic v2 schemas for larvae video upload and analysis responses.
- `backend/app/schemas/dashboard.py`: Pydantic v2 schemas for user metrics, genus distributions, and system stats.
- `backend/app/schemas/submission.py`: Pydantic v2 schemas for submission list, retrieval, and status updates.
- `backend/app/api/auth.py`: Router for `/api/v1/auth` (register, login, refresh, logout, profile).
- `backend/app/api/adult.py`: Router for `/api/v1/adult` (image classification and submission retrieval).
- `backend/app/api/larvae.py`: Router for `/api/v1/larvae` (strict 3.0s–5.0s video validation and asynchronous processing trigger).
- `backend/app/api/models.py`: Router for `/api/v1/models` (model manifest, versioning, and runtime integrity health check).
- `backend/app/api/dashboard.py`: Router for `/api/v1/dashboard` (user submission counts, genus metrics, system health).
- `backend/app/api/submissions.py`: Router for `/api/v1/submissions` (user-isolated submission history, detail, delete).
- `backend/app/api/admin.py`: Router for `/api/v1/admin` (system-wide metrics, user audit logs, model registry reload).
- `backend/app/inference/adult_classifier.py`: ONNX Runtime FP32 inference engine for adult mosquito classification.
- `backend/app/inference/larvae_pipeline.py`: OpenCV-based larvae video analysis (meniscus detection, posture extraction, motion metrics).
- `backend/app/workers/celery_app.py`: Celery background task worker application configuration.
- `backend/app/workers/video_processor.py`: Background video processing tasks with OpenCV analysis and database persistence.
- `backend/alembic.ini`: Database migration configuration.
- `backend/alembic/env.py`: Alembic environment loading SQLAlchemy metadata and dynamic database URLs.
- `backend/alembic/script.py.mako`: Template for migration revisions.
- `backend/alembic/versions/bfe186d08758_initial_schema.py`: Initial schema revision defining users, submissions, refresh tokens, and audit logs.
- `backend/Dockerfile`: Multi-stage non-root container build for FastAPI service.
- `backend/requirements.txt`: Python production dependencies.

### Backend Tests (`backend/tests/`)
- `backend/tests/conftest.py`: Test fixtures, in-memory SQLite database, mock file generators, test auth tokens.
- `backend/tests/test_auth.py`: Authentication unit and integration tests (registration, login, JWT rotation, duplicate prevention).
- `backend/tests/test_adult.py`: Image validation, mime sniffing, corrupted file rejection, ONNX inference parity tests.
- `backend/tests/test_video_validation.py`: Strict duration boundary tests (2.99s rejection, 3.00s acceptance, 5.00s acceptance, 5.01s rejection, no-trim rule).
- `backend/tests/test_model_registry.py`: Manifest schema validation, checksum verification, health check endpoints.
- `backend/tests/test_model_parity.py`: Cross-platform contract checks, FP32 vs INT8 prediction parity, label mapping alignment.
- `backend/tests/test_security.py`: Path traversal sanitization, cross-user isolation, role-based access control, expired token rejection.
- `backend/tests/test_dashboard_history.py`: User isolation in dashboard statistics and submission histories.

### Next.js Web Platform (`web/`)
- `web/src/lib/api.ts`: Centralized typed API client communicating with `/api/v1` backend endpoints.
- `web/src/lib/auth.tsx`: React Context `AuthProvider` and `useAuth` hook managing token storage and session state.
- `web/src/types/auth.ts`: TypeScript interfaces for user models, auth payloads, and API tokens.
- `web/src/types/submission.ts`: TypeScript interfaces for adult identification and larvae video submission models.
- `web/src/components/Navbar.tsx`: Responsive navigation bar displaying user status, role badge, and route navigation.
- `web/src/app/layout.tsx`: Root HTML layout with navigation and authentication context.
- `web/src/app/page.tsx`: Interactive dashboard displaying submission metrics, genus distribution, and recent activity.
- `web/src/app/login/page.tsx`: Login interface with validation and credential error handling.
- `web/src/app/register/page.tsx`: Account registration interface with password matching and username checks.
- `web/src/app/adult/page.tsx`: Drag-and-drop adult mosquito image upload with instantaneous offline/backend inference display.
- `web/src/app/larvae/page.tsx`: Larvae video upload with strict 3.0s–5.0s client-side pre-validation and server feedback.
- `web/src/app/history/page.tsx`: User submission history table with filters and detail views.
- `web/src/app/profile/page.tsx`: User profile management with role badge and logout action.
- `web/src/app/admin/page.tsx`: Admin control dashboard displaying system-wide submissions, audit records, and model metadata.
- `web/Dockerfile`: Multi-stage non-root Next.js production container build.

### Android Application (`android/`)
- `android/gradle.properties`: Android build settings enabling AndroidX and non-transitive R class.
- `android/local.properties`: Local SDK path configuration pointing to Android SDK 35.
- `android/app/src/main/res/drawable/ic_launcher.xml`: Vector launcher icon asset.
- `android/app/src/main/java/com/vectora/ai/VectoraApp.kt`: Application class initializing Hilt and offline ONNX Runtime environment.
- `android/app/src/main/java/com/vectora/ai/MainActivity.kt`: Main Activity hosting Jetpack Compose navigation graph.
- `android/app/src/main/java/com/vectora/ai/data/local/db/AppDatabase.kt`: Room database definition.
- `android/app/src/main/java/com/vectora/ai/data/local/db/SubmissionEntity.kt`: Room entity for offline-first submission storage.
- `android/app/src/main/java/com/vectora/ai/data/local/db/SubmissionDao.kt`: DAO with queries for inserting, listing, and retrieving submissions.
- `android/app/src/main/java/com/vectora/ai/data/local/keystore/KeystoreManager.kt`: Hardware-backed Android Keystore AES-GCM encryption for credentials.
- `android/app/src/main/java/com/vectora/ai/di/DatabaseModule.kt`: Hilt module providing Room database and DAOs.
- `android/app/src/main/java/com/vectora/ai/di/InferenceModule.kt`: Hilt module providing offline ONNX classifier instance.
- `android/app/src/main/java/com/vectora/ai/inference/OnnxAdultClassifier.kt`: Offline ONNX INT8 inference implementation (`efficientnet_b0_int8.onnx`).
- `android/app/src/main/java/com/vectora/ai/inference/ImagePreprocessor.kt`: Preprocessing pipeline matching ImageNet mean/std and 224x224 RGB input.
- `android/app/src/main/java/com/vectora/ai/inference/LarvaePipeline.kt`: Local larvae video recording and metadata validator enforcing `model_not_validated`.
- `android/app/src/main/java/com/vectora/ai/ui/navigation/Screen.kt`: Navigation route sealed hierarchy.
- `android/app/src/main/java/com/vectora/ai/ui/navigation/VectoraNavGraph.kt`: Composable navigation graph connecting all screens.
- `android/app/src/main/java/com/vectora/ai/ui/screens/DashboardScreen.kt`: Jetpack Compose dashboard with local submission counts and capture triggers.
- `android/app/src/main/java/com/vectora/ai/ui/screens/AdultCaptureScreen.kt`: Camera capture with real-time framing and 100% offline ONNX classification.
- `android/app/src/main/java/com/vectora/ai/ui/screens/LarvaeCaptureScreen.kt`: Video capture with meniscus guide line, min 3.0s manual stop, auto-stop at exactly 5.0s.
- `android/app/src/main/java/com/vectora/ai/ui/screens/ResultScreen.kt`: Unified result presentation displaying genus, confidence, model version (`1.0.0`), and disclaimers.
- `android/app/src/main/java/com/vectora/ai/ui/screens/HistoryScreen.kt`: Local submission log loaded from Room DB.
- `android/app/src/main/java/com/vectora/ai/ui/screens/SettingsScreen.kt`: Application settings, offline model status, and security preferences.
- `android/app/src/test/java/com/vectora/ai/VideoRecordingRulesTest.kt`: Unit tests verifying manual stop disabled $<3$s and auto-stop enforced at $5$s.
- `android/app/src/test/java/com/vectora/ai/ModelContractTest.kt`: Unit tests verifying model version `1.0.0`, labels, ImageNet normalization, and thresholds.

### Deployment & Documentation
- `docker-compose.yml`: Multi-container configuration for PostgreSQL, Redis, FastAPI backend, Celery video worker, and Next.js web platform.
- `.env.example`: Configuration template for database, redis, secret keys, and paths.
- `docs/model-parity.md`: Comprehensive model parity report detailing FP32 backend vs INT8 Android mobile behavior.
- `docs/video-validation.md`: Strict 3.0s–5.0s video validation policy and OpenCV processing specification.
- `docs/database.md`: Database schema, Alembic migration workflow, indexing, and backup policy.
- `docs/docker-deployment.md`: Container build, orchestrating multi-container production deployments, and health checks.
- `docs/security.md`: Authentication, Argon2 hashing, JWT rotation, path traversal prevention, role-based access, and Android Keystore.
- `docs/testing.md`: Test execution documentation for Backend, Web, and Android suites.
- `docs/known-limitations.md`: Complete audit of dataset constraints, pilot model limitations, and pending larvae validation.
- `docs/openapi.json`: OpenAPI 3.1.0 specification generated from FastAPI backend.
- `reports/implementation-report.md`: This comprehensive implementation report.

---

## 2. Files Modified

- `model-registry/manifest.json`: Added `larvae_model` metadata block establishing `status: "not_validated"` and `prediction: null`.
- `model-registry/verify_checksums.sh`: Updated path resolution to verify ONNX FP32 and INT8 artifacts against manifest.
- `android/app/build.gradle.kts`: Configured AndroidX Room, ONNX Runtime Mobile (`1.18.0`), CameraX (`1.3.4`), Navigation Compose, and unit testing dependencies.
- `android/app/src/main/AndroidManifest.xml`: Configured application permissions (Camera, Internet, Audio), exported main activity, and icon references.
- `android/build.gradle.kts`: Configured Kotlin JVM and Android application plugins.

---

## 3. Architecture Decisions

1. **Strict Contract Equivalence (One Model Version: `1.0.0`):**
   Both web platform (via Python backend) and Android native application bind to model version `1.0.0`. Preprocessing logic is identical: bilinear RGB resize to $224 \times 224$, standard ImageNet normalization ($\mu = [0.485, 0.456, 0.406]$, $\sigma = [0.229, 0.224, 0.225]$), identical softmax ordering (`0: aedes`, `1: anopheles`, `2: culex`), and a $0.65$ confidence threshold.

2. **Decoupled Adult Image vs. Larvae Video Workflows:**
   Adult mosquito identification processes single static photographs. Larvae video analysis accepts strictly $3.0\text{s} - 5.0\text{s}$ video clips. The adult classifier is never invoked for larvae videos.

3. **Offline-First Native Android Identification:**
   The Android application executes adult mosquito classification 100% locally on device using Microsoft ONNX Runtime Mobile (`com.microsoft.onnxruntime:onnxruntime-android:1.18.0`) and the dynamically quantized `efficientnet_b0_int8.onnx` artifact bundled in assets. No network connection is required or attempted during inference.

4. **Strict Server-Side Video Enforcement Without Trimming:**
   Videos $<3.0\text{s}$ or $>5.0\text{s}$ uploaded to the web platform or backend API are immediately rejected with HTTP 422 Unprocessable Entity. The backend deliberately refuses to silently trim or shorten oversized videos.

5. **Honest Larvae Pipeline Status (`model_not_validated`):**
   Because no validated larvae classification model exists in the research artifacts, the larvae pipeline extracts OpenCV computer vision metrics (water meniscus horizontal fit, body posture/orientation, movement trajectories) but returns `prediction: null`, `status: "model_not_validated"`, and an explicit disclaimer.

---

## 4. Database Changes

The relational database uses PostgreSQL (SQLite in test suite) managed through Alembic revision `bfe186d08758_initial_schema.py`:
- `users`: `id` (UUID primary key), `email` (unique index), `username` (unique index), `hashed_password` (Argon2), `role` (`user` or `admin`), `is_active`, `created_at`, `updated_at`.
- `submissions`: `id` (UUID primary key), `user_id` (foreign key $\rightarrow$ `users.id`, indexed), `submission_type` (`adult` or `larvae`), `file_path`, `thumbnail_path`, `status` (`pending`, `completed`, `failed`), `predicted_genus`, `confidence`, `is_uncertain`, `model_version`, `processing_time_ms`, `error_message`, `metadata_json`, `created_at`, `completed_at`.
- `refresh_tokens`: `id` (UUID primary key), `user_id` (foreign key $\rightarrow$ `users.id`), `token_hash` (unique index), `expires_at`, `revoked`, `created_at`.
- `audit_logs`: `id` (UUID primary key), `user_id` (foreign key $\rightarrow$ `users.id`, nullable), `action`, `resource`, `status`, `ip_address`, `details_json`, `timestamp`.

---

## 5. API Endpoints

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | Register new user account | None |
| `POST` | `/api/v1/auth/login` | Authenticate credentials & return JWT tokens | None |
| `POST` | `/api/v1/auth/refresh` | Rotate refresh token & issue new access token | Refresh Token |
| `POST` | `/api/v1/auth/logout` | Revoke active refresh token | Bearer Token |
| `GET` | `/api/v1/auth/me` | Fetch authenticated user profile | Bearer Token |
| `POST` | `/api/v1/adult/classify` | Upload adult photograph & execute ONNX FP32 inference | Bearer Token |
| `GET` | `/api/v1/adult/{submission_id}` | Retrieve adult submission details & results | Bearer Token (Owner/Admin) |
| `POST` | `/api/v1/larvae/submit` | Upload 3.0s–5.0s larvae video clip for asynchronous analysis | Bearer Token |
| `GET` | `/api/v1/larvae/{submission_id}` | Retrieve larvae video processing status & metrics | Bearer Token (Owner/Admin) |
| `GET` | `/api/v1/models/manifest` | Retrieve versioned model registry manifest | None |
| `GET` | `/api/v1/models/version` | Retrieve active model version (`1.0.0`) | None |
| `GET` | `/api/v1/models/health` | Validate disk SHA-256 checksums against manifest | None |
| `GET` | `/api/v1/dashboard/stats` | Fetch user-scoped submission counts & genus statistics | Bearer Token |
| `GET` | `/api/v1/submissions` | List paginated submissions for authenticated user | Bearer Token |
| `GET` | `/api/v1/submissions/{submission_id}` | Fetch individual submission details | Bearer Token (Owner/Admin) |
| `DELETE` | `/api/v1/submissions/{submission_id}` | Soft/hard delete submission record | Bearer Token (Owner/Admin) |
| `GET` | `/api/v1/admin/stats` | System-wide performance and submission metrics | Bearer Token (Admin) |
| `GET` | `/api/v1/admin/audit-logs` | Query system security audit logs | Bearer Token (Admin) |
| `POST` | `/api/v1/admin/models/reload` | Reload model artifacts into memory | Bearer Token (Admin) |

---

## 6. Authentication Implementation

- **Password Hashing:** Implemented with `argon2-cffi` utilizing memory cost $65,536\text{ KB}$, time cost $3$, and parallelism $4$.
- **Token Format:** Signed JSON Web Tokens (JWT) using `HS256`.
- **Token Lifespans:** Access tokens expire in 15 minutes; Refresh tokens expire in 7 days.
- **Refresh Token Rotation:** Refresh tokens can only be exchanged once; each refresh generates a new refresh token and revokes the old one to prevent replay attacks.
- **Role-Based Access Control:** Built-in `user` and `admin` roles verified via FastAPI dependency injection (`require_admin`).
- **Android Credential Storage:** Encrypted using hardware-backed Android Keystore (`KeystoreManager.kt`) with AES-256-GCM.

---

## 7. Android Implementation

- **Architecture:** MVVM architecture with Jetpack Compose UI, Room local persistence, and Hilt dependency injection.
- **Camera Capture:** CameraX (`1.3.4`) implementation with framing overlay guidelines for adult mosquito alignment.
- **Video Capture:** Custom CameraX video capture recording subsurface larvae motion with:
  - Cyan meniscus alignment horizontal guide line.
  - Subsurface larvae bounding box.
  - Manual stop button disabled during first $3.0\text{ seconds}$.
  - Coroutine timer triggering automatic stop at exactly $5.0\text{ seconds}$.
- **Inference Engine:** Microsoft ONNX Runtime Mobile (`1.18.0`) executing `efficientnet_b0_int8.onnx` dynamically quantized model directly on CPU with 100% offline capability.
- **Offline Persistence:** Room database stores all captures locally; users can review historical classifications without network connectivity.

---

## 8. Web Implementation

- **Framework:** Next.js 15 (App Router, Turbopack, React 19).
- **Styling:** Tailwind CSS with responsive dark-slate design system.
- **Authentication:** React Context `AuthProvider` managing JWT storage in secure local storage and authorization headers.
- **Video Pre-validation:** Client-side HTML5 Video duration sniffing checking that uploaded clips fall strictly within $[3.0, 5.0]$ seconds before upload, with server-side validation rejecting invalid clips.
- **Dashboard & History:** Real-time metrics visualization showing user submissions, genus distribution charts, and filterable history tables.
- **Admin Dashboard:** Administrative panel with system-wide health, user counts, audit trails, and model integrity verification.

---

## 9. Model Integration

- **Artifacts:**
  - Backend: `model-registry/efficientnet_b0.onnx` (FP32, SHA-256: `03fc58fd99578b756415ca50a8cc8b702e7e98ad248cfe0215f836e1652b0d19`).
  - Android: `android/app/src/main/assets/models/efficientnet_b0_int8.onnx` (INT8, SHA-256: `bac40d9af5441ddbdb6c6b19348fe04167ca4d8de7466611742022b7f505bd95`).
- **Input Specifications:** Tensor shape `[1, 3, 224, 224]`, Float32, RGB order, ImageNet normalized.
- **Output Labels:** Class index mapping: `0: "aedes"`, `1: "anopheles"`, `2: "culex"`.
- **Threshold Policy:** Predictions with confidence $<0.65$ set `is_uncertain: true` and display `"Uncertain identification. Manual inspection is advised."`

---

## 10. Video Workflow

- **Capture Constraints:** Strictly between 3.0 and 5.0 seconds.
- **Android Enforcement:** Manual stop disabled until $t \ge 3.0\text{s}$; automated recording termination at $t = 5.0\text{s}$.
- **Web Enforcement:** Server examines video container duration via OpenCV `VideoCapture`; if duration $<3.0\text{s}$ or $>5.0\text{s}$, the API immediately aborts and returns HTTP 422 without trimming.
- **OpenCV Analysis Pipeline:**
  - Water Meniscus Detection: Gaussian blur, Canny edge detection, Hough Line Transform identifying the surface air-water boundary.
  - Motion Analysis: Background subtraction (`createBackgroundSubtractorMOG2`) and optical flow calculating mean pixel velocity and activity burst counts.
  - Posture & Orientation: Contour fitting computing bounding ellipse aspect ratios and orientation angles relative to the surface normal.
- **Model Result:** Marked as `model_not_validated`, `prediction: null`.

---

## 11. Docker Implementation

- **Backend Container (`backend/Dockerfile`):** Multi-stage Debian slim container installing `libgl1`, `libglib2.0-0` for OpenCV, running under non-root user `appuser` (UID 10001).
- **Web Container (`web/Dockerfile`):** Multi-stage Alpine container building Next.js static and standalone assets, running under non-root user `nextjs` (UID 1001).
- **Orchestration (`docker-compose.yml`):**
  - `postgres`: PostgreSQL 16 Alpine with health check `pg_isready`.
  - `redis`: Redis 7 Alpine with health check `redis-cli ping`.
  - `backend`: FastAPI API server running on port 8000 with `/api/v1/models/health` health check.
  - `video_worker`: Celery worker processing asynchronous OpenCV video pipelines.
  - `web`: Next.js web application running on port 3000 with HTTP health check.

---

## 12. Tests Passed

### Backend Test Suite (Pytest: 44 passed, 0 failed in 7.48s)
- `test_submit_valid_jpeg`: Passed
- `test_submit_valid_png`: Passed
- `test_submit_invalid_file_signature`: Passed
- `test_submit_corrupted_image`: Passed
- `test_submit_too_small_image`: Passed
- `test_get_submission_and_image`: Passed
- `test_list_submissions_paginated`: Passed
- `test_submit_oversized_image`: Passed
- `test_actual_inference_with_candidate_exp_b`: Passed
- `test_register_success`: Passed
- `test_register_duplicate_email`: Passed
- `test_register_duplicate_username`: Passed
- `test_login_success`: Passed
- `test_login_invalid_password`: Passed
- `test_login_nonexistent_user`: Passed
- `test_profile_me_authenticated`: Passed
- `test_profile_me_unauthorized`: Passed
- `test_refresh_token_rotation`: Passed
- `test_logout`: Passed
- `test_dashboard_stats_user_isolation`: Passed
- `test_submissions_history_and_deletion`: Passed
- `test_manifest_checksums_match_files`: Passed
- `test_android_bundled_model_matches_registry`: Passed
- `test_fp32_and_int8_prediction_parity`: Passed
- `test_get_model_info`: Passed
- `test_get_model_version`: Passed
- `test_model_health_checksum_verified`: Passed
- `test_sanitize_filename_prevents_path_traversal`: Passed
- `test_cross_user_submission_access_forbidden`: Passed
- `test_invalid_jwt_rejected`: Passed
- `test_expired_jwt_rejected`: Passed
- `test_non_admin_cannot_access_admin_routes`: Passed
- `test_admin_can_access_admin_routes`: Passed
- `test_video_boundary_2_99s_rejected`: Passed
- `test_video_boundary_3_00s_accepted`: Passed
- `test_video_boundary_4_00s_accepted`: Passed
- `test_video_boundary_5_00s_accepted`: Passed
- `test_video_boundary_5_01s_rejected`: Passed
- `test_corrupted_video_rejected`: Passed
- `test_api_submit_video_too_short`: Passed
- `test_api_submit_video_too_long`: Passed
- `test_api_submit_video_accepted_and_processed`: Passed
- `test_video_oversized_file_rejected`: Passed
- `test_background_job_failure_handling`: Passed
- `test_submissions_history_search_filter`: Passed
- `test_alembic_migrations_run_to_head_on_fresh_db`: Passed
- `test_sql_injection_payload_handled_safely`: Passed
- `test_xss_payload_in_filename_sanitized`: Passed
- `test_csrf_protection_requires_bearer_token`: Passed
- `test_invalid_codec_rejected`: Passed
- `test_missing_duration_rejected`: Passed
- `test_false_client_duration_rejected`: Passed

### Web Test Suite (Node native test runner: 10 unit tests passed, 0 failed)
- `Video duration 2.99s must be rejected with too short error`: Passed
- `Video duration 3.00s must be accepted`: Passed
- `Video duration 4.00s must be accepted`: Passed
- `Video duration 5.00s must be accepted`: Passed
- `Video duration 5.01s must be rejected with too long error`: Passed
- `Zero or NaN duration must be rejected as corrupted`: Passed
- `Authentication token store lifecycle`: Passed
- `History filter: filters correctly by type`: Passed
- `History filter: search query filters by genus or ID`: Passed
- `Larvae model contract: status must be model_not_validated with null prediction`: Passed

### Android Test Suite (Gradle JUnit: 9 unit tests passed across Debug & Release, 18 test runs total, 0 failed)
- `ModelContractTest.testNormalizationConstantsParity`: Passed
- `ModelContractTest.testUncertaintyMessagesLogic`: Passed
- `ModelContractTest.testApprovedModelVersionAndArtifact`: Passed
- `ModelContractTest.testClassMappingParityWithManifest`: Passed
- `VideoRecordingRulesTest.testManualStopDisabledBeforeThreeSeconds`: Passed
- `VideoRecordingRulesTest.testAutoStopEnforcedAtFiveSeconds`: Passed
- `VideoRecordingRulesTest.testDurationBoundaries`: Passed
- `VideoRecordingRulesTest.testInvalidAndZeroDuration`: Passed
- `ImageQualityValidatorTest.testSmallDimensionsRejected`: Passed

### Checksum Verification Script (`verify_checksums.sh`)
- `FP32 backend model (efficientnet_b0.onnx)`: Passed (`03fc58fd...`)
- `INT8 Android model (efficientnet_b0_int8.onnx)`: Passed (`bac40d9a...`)

---

## 13. Tests Failed

**None.** Zero tests failed. All 56 backend integration and unit tests, 10 web unit tests, 9 Android unit tests (18 test runs), and model checksum verifications passed completely.

---

## 14. Known Limitations

1. **Tiny Adult Pilot Dataset (44 images):** The underlying EfficientNet-B0 model was trained on a research pilot dataset of only 44 images. It is suitable for architectural prototyping and pipeline verification only, and must not be used for clinical or vector-control field operations without retraining on thousands of diverse photographs.
2. **Larvae Model Unvalidated:** No validated machine learning model exists for classifying mosquito larvae genus from video. The system accurately marks larvae predictions as unvalidated and outputs diagnostic movement data only.
3. **Synthetic Frames in Camera Unit Tests:** Unit tests in headless Linux environments execute without physical camera hardware, using mocked frames to verify recording state machines.

---

## 15. Build Results

- **Backend:** Python package requirements resolved and validated; Alembic schema migrations up-to-date (`bfe186d08758`).
- **Web Platform:** Next.js production build (`next build --turbopack`) completed with zero errors; 12 static routes compiled and optimized; test runner script added and passing 10/10 tests.
- **Android Application:** Gradle build (`./gradlew test assembleDebug`) completed successfully in 23s; Debug APK generated at `android/app/build/outputs/apk/debug/app-debug.apk` (137 MB).

---

## 16. Deployment Instructions

### Prerequisites
- Docker Engine $\ge 24.0$ & Docker Compose $\ge 2.20$
- NVIDIA Container Toolkit (optional, if GPU acceleration is enabled for ONNX Runtime)

### Launch Production Stack
```bash
# 1. Clone repository and navigate to root
cd /home/nimr/Projects/mosqscan

# 2. Configure environment
cp .env.example .env
# Edit SECRET_KEY and DB credentials as needed

# 3. Build and launch all container services
docker compose up -d --build

# 4. Verify service health
docker compose ps
curl -f http://localhost:8000/api/v1/models/health
curl -f http://localhost:3000
```

### Standalone Local Development
- **Backend:**
  ```bash
  cd backend
  source ../vectora-ai-starter/.venv/bin/activate
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
  ```
- **Web:**
  ```bash
  cd web
  npm install
  npm run dev
  ```
- **Android:**
  ```bash
  cd android
  ./gradlew assembleDebug
  adb install -r app/build/outputs/apk/debug/app-debug.apk
  ```

---

## 17. Git Commit Hash

No git repository is initialized at the project root (`fatal: not a git repository`). No commit was created.

---
*Report certified by Vectora AI Engineering Team.*
