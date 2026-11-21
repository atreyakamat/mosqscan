# Vectora AI — Backend Foundation Implementation Report

**Document Version:** 1.0.0  
**Date:** November 11, 2026  
**Status:** Completed and Verified  
**Canonical Repository Root:** `/home/nimr/Projects/mosqscan`

---

## 1. Executive Summary

This report documents the backend foundation implementation for Vectora AI.
All components follow ASD-STE100 principles.
Sentences are short.
Each sentence contains one instruction or statement of fact.
Technical terms are consistent across documents.
The implementation uses the frozen Exp B model artifacts.
No models were retrained.
No existing checkpoints or datasets were modified or deleted.
All 44 automated backend test cases pass.

---

## 2. Repository Structure

The canonical repository root is `/home/nimr/Projects/mosqscan`.
The monorepo contains four primary components:

- `backend/`: The FastAPI backend service.
- `models/`: The exported ONNX model artifacts.
- `model-registry/`: The model manifest and checksum verification scripts.
- `vectora-ai-starter/`: The machine learning experimentation workspace.

### Files Created or Updated

| Path | Action | Description |
| :--- | :--- | :--- |
| `backend/Dockerfile` | Updated | Multi-stage non-root container with curl, ffmpeg, and health check. |
| `backend/Dockerfile.worker` | Created | Celery video worker container for asynchronous larvae jobs. |
| `docker-compose.yml` | Created | Service orchestration for PostgreSQL, Redis, backend, and worker. |
| `.env.example` | Updated | Environment template with secure defaults. |
| `backend/app/services/storage_service.py` | Updated | Path traversal prevention with basename sanitization. |
| `backend/app/api/larvae.py` | Updated | Standardized JSON error response envelope. |
| `backend/app/api/models.py` | Updated | Dynamic model checksum lookup by filename in manifest. |
| `model-registry/manifest.json` | Updated | Added Exp B candidate models with `EXPERIMENTAL_NOT_FIELD_VALIDATED`. |
| `backend/tests/test_adult.py` | Updated | Added tests for oversized images and real specimen inference. |
| `backend/tests/test_video_validation.py` | Updated | Added tests for oversized videos and background job failure states. |
| `docs/openapi.json` | Created | Exported OpenAPI specification. |
| `reports/backend-implementation-report.md` | Created | Architecture and technical implementation report. |
| `reports/api-contract.md` | Created | API contract for web and mobile client teams. |
| `reports/backend-test-report.md` | Created | Test execution results and verification summary. |
| `reports/security-test-report.md` | Created | Security analysis, RBAC, and boundary tests. |

---

## 3. Technology Stack & Hardware Compatibility

The backend runs on an Intel Core i7-2600 processor.
This processor supports AVX instructions.
This processor does not support AVX2 instructions.

- **Language:** Python 3.12.
- **Web Framework:** FastAPI 0.115.
- **Validation:** Pydantic 2.10.
- **ORM:** SQLAlchemy 2.0 with PostgreSQL driver `psycopg2-binary`.
- **Database Migrations:** Alembic 1.14.
- **Inference Engine:** ONNX Runtime 1.20 with `CPUExecutionProvider`.
- **Image Processing:** Pillow 11.0 and OpenCV Headless 4.10.
- **Task Queue:** Celery 5.4 with Redis 5.2.
- **Container Platform:** Docker 29.9 and Docker Compose 5.6.

All dependencies execute correctly on AVX CPUs without AVX2.
Real model inference was executed and verified on the host system.

---

## 4. Authentication and Authorization

The authentication system is implemented in `app/api/auth.py` and `app/core/security.py`.

- Passwords use Argon2id hashing via `passlib` and `argon2-cffi`.
- Access tokens use JSON Web Tokens with the HS256 algorithm.
- Access tokens expire after 15 minutes.
- Refresh tokens expire after 7 days.
- Refresh tokens are stored in the database as SHA-256 hashes.
- Refresh tokens rotate upon every refresh call.
- The previous refresh token is immediately revoked.
- User accounts have an `is_active` status flag.
- Inactive users cannot log in.
- Inactive users cannot refresh tokens.
- Role-based authorization supports `user` and `admin` roles.
- Resource endpoints verify user ownership before granting access.

---

## 5. Adult Mosquito Identification API

The adult identification endpoint is `POST /api/v1/adult/submit`.
The implementation executes the following operations in sequence:

1. Receive the file stream through FastAPI `UploadFile`.
2. Inspect the first bytes of the file for valid signatures (`\xff\xd8\xff` for JPEG, `\x89PNG\r\n\x1a\n` for PNG).
3. Check the file size against the limit (`settings.MAX_IMAGE_SIZE_MB`, default 20 MB).
4. Safely decode the image with Pillow.
5. Inspect image dimensions. The image must measure at least 100 by 100 pixels.
6. Calculate image quality metrics using grayscale Laplacian variance.
7. Resize the image to 224 by 224 pixels with bilinear interpolation.
8. Normalize pixel values with ImageNet mean `[0.485, 0.456, 0.406]` and standard deviation `[0.229, 0.224, 0.225]`.
9. Construct a tensor of shape `(1, 3, 224, 224)`.
10. Run inference with ONNX Runtime using the approved FP32 model.
11. Compute Softmax probabilities over class logits.
12. Map probabilities to alphabetical genus order: Aedes (0), Anopheles (1), Culex (2).
13. Apply the configurable confidence threshold (default 0.50).
14. If top confidence is below the threshold, set `predicted_genus` to `null` and mark `is_uncertain=True`.
15. Set model status to `EXPERIMENTAL_NOT_FIELD_VALIDATED`.
16. Save the image file to private media storage.
17. Save submission and inference metadata to PostgreSQL.
18. Return the structured response.

---

## 6. Larvae Video API

The larvae video endpoint is `POST /api/v1/larvae/submit`.
The implementation enforces strict duration rules:

- Videos with duration below 3.0 seconds are rejected with error code `VIDEO_TOO_SHORT`.
- Videos with duration equal to 3.0, 4.0, or 5.0 seconds are accepted.
- Videos with duration above 5.0 seconds are rejected with error code `VIDEO_TOO_LONG`.
- The system decodes actual media timestamps using OpenCV `VideoCapture`.
- The system does not trust client-supplied duration.
- The system does not trim long videos.
- The system does not process rejected videos.
- Corrupted videos return error code `VIDEO_CORRUPTED`.
- Oversized videos return error code `FILE_TOO_LARGE`.
- Accepted videos create a database record with status `queued`.
- A background worker analyzes the video frames asynchronously.
- The larvae model returns `status: "model_not_validated"`.
- Genus prediction returns `null` because no field-validated model exists.

---

## 7. Database Models and Schema

The database uses UUID identifiers and UTC timestamps.
The schema is defined in `app/db/models.py`.

- `users`: User identity, email, username, Argon2id password hash, role, active flag.
- `refresh_tokens`: Cryptographic hash of refresh tokens, expiration timestamp, revoked flag.
- `submissions`: Type (`adult` or `larvae`), processing status, owner identifier.
- `media_files`: File path, original name, stored name, MIME type, file size, SHA-256 hash.
- `identification_results`: Predicted genus, confidence, model version, processing time, all class scores, uncertainty flags.
- `processing_jobs`: Background worker state, frame count, valid frames, error message.
- `model_versions`: Model metadata, input dimensions, normalization values, artifact hashes.
- `audit_events`: Security event log, IP address, user agent, event type, resource identifier.

Database migrations are managed with Alembic.
Migration revision `bfe186d08758` contains the initial schema.
Upgrades and rollbacks execute cleanly without data loss.

---

## 8. Private Media Storage

Uploaded media files are stored outside PostgreSQL.
Files are placed in `settings.MEDIA_STORAGE_PATH` (default `/app/media` in Docker).
Subdirectories separate `images/` and `videos/`.
File paths are not exposed to clients.
Filenames are sanitized to prevent directory traversal attacks.
Access to media files requires authentication.
The retrieval endpoint `GET /api/v1/adult/submissions/{id}/image` verifies user ownership.
Unauthorized users receive HTTP 403 Forbidden.

---

## 9. Model Registry & Provenance

The backend loads the model manifest from `settings.MODEL_MANIFEST_PATH`.
The approved candidate model is `vectora-efficientnet-b0-exp-b`.
Artifacts are linked directly to training experiment B:

- **FP32 Backend Artifact:** `models/vectora_candidate_exp_b.onnx`
  - SHA-256: `d644b9cd9c952d461bbfbb44e8b1926cdcf9bbbfb9cd43f85065cbed0d7b1499`
  - Size: 16,035,577 bytes
- **INT8 Android Artifact:** `models/vectora_candidate_exp_b_int8.onnx`
  - SHA-256: `6d7e830699f4ca3f3b67c538c2f77a592f88288845dfa00d94c7837ccef68803`
  - Size: 4,362,942 bytes

The endpoint `GET /api/v1/models/health` verifies model checksums on disk against the manifest.
If checksums do not match, the health endpoint returns status `degraded`.

---

## 10. Docker Architecture

The application defines four container services in `docker-compose.yml`:

```
+-------------------------------------------------------+
|                    Docker Network                     |
|                                                       |
|  +--------------------+       +--------------------+  |
|  |     PostgreSQL     |       |       Redis        |  |
|  |    (No Host Port)  |       |   (No Host Port)   |  |
|  +---------^----------+       +---------^----------+  |
|            |                            |             |
|            +------------+  +------------+             |
|                         |  |                          |
|                  +------+--+-----+                    |
|                  |    Backend    | <- 127.0.0.1:8000  |
|                  +---------------+                    |
|                         |                             |
|                  +------+--------+                    |
|                  |  Video Worker |                    |
|                  +---------------+                    |
+-------------------------------------------------------+
```

1. **`postgres`:** PostgreSQL 16 Alpine. Internal network only. No host port binding.
2. **`redis`:** Redis 7 Alpine. Internal network only. No host port binding.
3. **`backend`:** FastAPI web server. Binds to `127.0.0.1:8000`. Runs as non-root user `vectora`.
4. **`video_worker`:** Celery worker for larvae video analysis. Runs as non-root user `vectora`.

Containers use named volumes: `postgres_data`, `redis_data`, and `media_storage`.

---

## 11. Commands to Run the Backend

### Local Development (Python Virtual Environment)
```bash
# Navigate to backend directory
cd backend

# Activate virtual environment
source ../vectora-ai-starter/.venv/bin/activate

# Run database migrations
alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Production Deployment (Docker Compose)
```bash
# Copy environment configuration
cp .env.example .env

# Build and start all services in detached mode
docker compose up -d --build

# Check service status and health
docker compose ps

# View backend logs
docker compose logs -f backend

# Stop services
docker compose down
```

### Running Test Suite
```bash
cd backend
PYTHONPATH=. pytest tests/ -v
```

---

## 12. Known Limitations

1. **Dataset Scope:** The adult mosquito model is trained on 44 original Indian mosquito photographs. It is not validated for clinical or public health decisions.
2. **Larvae Classifier:** Larvae video analysis detects motion and meniscus orientation, but taxonomic classification returns `model_not_validated` until an entomologist-verified dataset is acquired.
3. **Hardware Instruction Set:** Host CPU does not support AVX2. ONNX Runtime uses default CPU thread execution without AVX2 optimizations.
