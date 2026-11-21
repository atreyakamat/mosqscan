# Vectora AI — System Architecture

> [!NOTE]
> Vectora AI is a multi-platform mosquito identification system. Field researchers photograph or video adult mosquitoes; the system returns a genus-level identification (Aedes, Anopheles, or Culex) with a confidence score.

---

## High-Level Component Overview

```mermaid
flowchart TD
    subgraph Client["Client Layer"]
        AND["Android App\n(Kotlin · ONNX INT8)"]
        WEB["Web App\n(Next.js · React)"]
    end

    subgraph API["API Layer"]
        FAST["FastAPI Backend\n(Python 3.12 · Uvicorn)"]
        AUTH["Auth Service\n(Argon2id · JWT)"]
    end

    subgraph Workers["Async Workers"]
        CEL["Celery Worker\n(Redis broker)"]
        INF["Inference Engine\n(ONNX Runtime · CPU)"]
        VID["Video Pipeline\n(OpenCV)"]
    end

    subgraph Storage["Storage Layer"]
        PG["PostgreSQL\n(SQLAlchemy · Alembic)"]
        RED["Redis\n(task queue · cache)"]
        FS["File System\n(/app/media)"]
    end

    subgraph Registry["Model Registry"]
        MAN["manifest.json"]
        FP32["efficientnet_b0.onnx\n(FP32 · backend)"]
        INT8["efficientnet_b0_int8.onnx\n(INT8 · Android)"]
    end

    AND -->|"HTTPS REST"| FAST
    WEB -->|"HTTPS REST"| FAST
    FAST --> AUTH
    FAST --> PG
    FAST -->|"enqueue task"| RED
    RED --> CEL
    CEL --> INF
    CEL --> VID
    INF --> FP32
    INF --> FS
    VID --> FS
    CEL --> PG
    MAN --> FP32
    MAN --> INT8
    INT8 -.->|"bundled in APK"| AND
```

---

## Data Flow — Image Classification

```mermaid
sequenceDiagram
    participant U as User (Android/Web)
    participant A as FastAPI
    participant C as Celery Worker
    participant O as ONNX Runtime
    participant D as PostgreSQL

    U->>A: POST /scans (multipart: image file)
    A->>A: Validate JWT, file size, MIME type
    A->>D: INSERT scan record (status=pending)
    A->>C: Enqueue classify_image task
    A-->>U: 202 Accepted {scan_id}

    C->>O: Load FP32 model, run inference
    O-->>C: softmax probabilities [aedes, anopheles, culex]
    C->>C: Apply confidence threshold (0.65)
    C->>D: UPDATE scan (status=done, result, confidence)
    U->>A: GET /scans/{scan_id}
    A->>D: SELECT scan
    A-->>U: 200 OK {genus, confidence, message}
```

---

## Data Flow — Video Larvae Pipeline

```mermaid
sequenceDiagram
    participant U as User
    participant A as FastAPI
    participant C as Celery Worker
    participant V as OpenCV

    U->>A: POST /larvae-scans (multipart: video file)
    A->>A: Validate JWT, file size
    A->>A: Check video duration (server-side, authoritative)
    Note over A: Reject if < 3s or > 5s
    A-->>U: 400 if invalid duration
    A->>C: Enqueue process_larvae_video task
    A-->>U: 202 Accepted {scan_id}

    C->>V: Decode video, extract frames
    V-->>C: Frame array
    C->>C: Larvae model status = not_validated
    C-->>U: Result includes pipeline_available=true,\nprediction=null
```

---

## Technology Stack

| Layer | Technology | Version | Notes |
|-------|-----------|---------|-------|
| **Android client** | Kotlin | — | ONNX Runtime Android |
| **Android ML** | ONNX Runtime | — | INT8 quantized model bundled in APK |
| **Web client** | Next.js / React | — | Node 26, npm 11 |
| **API framework** | FastAPI | 0.115.5 | Async, OpenAPI auto-docs |
| **ASGI server** | Uvicorn | 0.32.1 | Multi-worker in production |
| **ML runtime** | ONNX Runtime | 1.20.1 | CPU-only (no CUDA) |
| **Task queue** | Celery | 5.4.0 | Redis broker |
| **Message broker / cache** | Redis | 5.2.1 | — |
| **Database** | PostgreSQL | — | SQLAlchemy 2 ORM |
| **Migrations** | Alembic | 1.14.0 | — |
| **Password hashing** | Argon2id | — | passlib + argon2-cffi |
| **Auth tokens** | JWT (HS256) | — | python-jose |
| **Video decoding** | OpenCV | 4.10.0.84 | Headless build |
| **Image processing** | Pillow | 11.0.0 | — |
| **Containerisation** | Docker + Compose | — | Multi-stage Dockerfile |

---

## Module Responsibilities

### `backend/app/api/`
Defines all HTTP route handlers (FastAPI routers). Responsible for:
- Request validation and authentication checks
- Dispatching Celery tasks for async processing
- Returning HTTP responses; no business logic

### `backend/app/core/`
Cross-cutting concerns:
- JWT creation and validation
- Configuration loading (`pydantic-settings`)
- Security utilities (password hashing, cookie helpers)

### `backend/app/db/`
Database layer:
- SQLAlchemy model definitions
- Alembic migration environment
- Session factory and dependency injection

### `backend/app/inference/`
ML inference module:
- Loads and caches the ONNX FP32 model
- Implements image pre-processing pipeline (resize → RGB → normalize)
- Applies confidence threshold and uncertainty messaging

### `backend/app/schemas/`
Pydantic request/response schemas for all API endpoints.

### `backend/app/services/`
Business logic layer (called by route handlers and workers):
- Scan lifecycle management
- File upload handling
- Video duration validation

### `backend/app/workers/`
Celery task definitions:
- `classify_image` — runs ONNX inference and writes result to DB
- `process_larvae_video` — video frame extraction pipeline
