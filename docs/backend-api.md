# Backend API Reference — Vectora AI

> [!NOTE]
> The Vectora AI backend is a FastAPI application served by Uvicorn. Interactive API documentation (Swagger UI) is available at `/docs` and ReDoc at `/redoc` in development.

---

## Base URL

| Environment | URL |
|-------------|-----|
| Local development | `http://localhost:8000` |
| Docker Compose (internal) | `http://backend:8000` |
| Production | `https://api.vectora.example.com` |

---

## Authentication

Vectora AI uses a **dual-token** scheme:

| Token | Storage | Lifetime | Purpose |
|-------|---------|---------|---------|
| **Access token** (JWT, HS256) | `Authorization: Bearer <token>` header | 15 minutes | Authorise API requests |
| **Refresh token** | `HttpOnly` Secure cookie (`refresh_token`) | 7 days | Obtain new access tokens |

### Obtain Tokens — Login

```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=hunter2
```

**Response `200 OK`:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```
The refresh token is set as an `HttpOnly` cookie automatically.

### Refresh Access Token

```http
POST /auth/refresh
Cookie: refresh_token=<token>
```

**Response `200 OK`:** Same structure as login.

### Logout

```http
POST /auth/logout
Authorization: Bearer <access_token>
```

Invalidates the refresh token cookie.

---

## Endpoints

### Authentication

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/auth/register` | None | Create a new user account |
| `POST` | `/auth/login` | None | Authenticate and receive tokens |
| `POST` | `/auth/refresh` | Cookie | Refresh the access token |
| `POST` | `/auth/logout` | Bearer | Revoke refresh token |

---

### Adult Mosquito Scans

#### `POST /scans` — Submit an Image for Classification

```http
POST /scans
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

file=<image file>
```

**Constraints:**
- Max file size: 20 MB (configurable via `MAX_IMAGE_SIZE_MB`)
- Accepted MIME types: `image/jpeg`, `image/png`, `image/webp`

**Response `202 Accepted`:**
```json
{
  "scan_id": "a1b2c3d4-...",
  "status": "pending"
}
```

---

#### `GET /scans/{scan_id}` — Retrieve Scan Result

```http
GET /scans/a1b2c3d4-...
Authorization: Bearer <access_token>
```

**Response `200 OK` (completed):**
```json
{
  "scan_id": "a1b2c3d4-...",
  "status": "done",
  "created_at": "2026-11-11T10:00:00Z",
  "result": {
    "predicted_genus": "aedes",
    "confidence": 0.812,
    "above_threshold": true,
    "probabilities": {
      "aedes": 0.812,
      "anopheles": 0.103,
      "culex": 0.085
    },
    "message": null
  }
}
```

**Response `200 OK` (below confidence threshold):**
```json
{
  "scan_id": "...",
  "status": "done",
  "result": {
    "predicted_genus": "aedes",
    "confidence": 0.541,
    "above_threshold": false,
    "message": "Uncertain identification. Manual inspection is advised."
  }
}
```

**Response `200 OK` (still processing):**
```json
{
  "scan_id": "...",
  "status": "pending",
  "result": null
}
```

---

#### `GET /scans` — List My Scans

```http
GET /scans?page=1&per_page=20
Authorization: Bearer <access_token>
```

Returns a paginated list of scans belonging to the authenticated user.

**Response `200 OK`:**
```json
{
  "items": [ ... ],
  "total": 42,
  "page": 1,
  "per_page": 20
}
```

---

#### `DELETE /scans/{scan_id}` — Delete a Scan

```http
DELETE /scans/a1b2c3d4-...
Authorization: Bearer <access_token>
```

Only the scan owner may delete it. Returns `204 No Content`.

---

### Larvae Video Scans

#### `POST /larvae-scans` — Submit a Video

```http
POST /larvae-scans
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

file=<video file>
```

**Constraints:**
- Accepted duration: **3–5 seconds (inclusive)** — server-side check is authoritative
- Max file size: 100 MB
- Accepted MIME types: `video/mp4`, `video/quicktime`

**Response `202 Accepted`:**
```json
{
  "scan_id": "...",
  "status": "pending"
}
```

**Response `400 Bad Request` (invalid duration):**
```json
{
  "error": "VIDEO_DURATION_INVALID",
  "message": "Video must be between 3 and 5 seconds. Received 1.8 seconds.",
  "detail": {
    "duration_seconds": 1.8,
    "min_seconds": 3,
    "max_seconds": 5
  }
}
```

#### `GET /larvae-scans/{scan_id}` — Retrieve Larvae Scan Result

```http
GET /larvae-scans/...
Authorization: Bearer <access_token>
```

**Response `200 OK`:**
```json
{
  "scan_id": "...",
  "status": "done",
  "result": {
    "prediction": null,
    "pipeline_available": true,
    "message": "Larvae identification model is not yet field-validated and must not be used for production predictions."
  }
}
```

---

### Health

#### `GET /health` — Health Check

```http
GET /health
```

No authentication required. Used by Docker health checks and load balancers.

**Response `200 OK`:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "model_registry_version": "1.0.0"
}
```

---

## Error Codes

| HTTP Status | Error Code | Meaning |
|-------------|-----------|---------|
| `400` | `VALIDATION_ERROR` | Request body or query parameter failed validation |
| `400` | `VIDEO_DURATION_INVALID` | Video shorter than 3s or longer than 5s |
| `400` | `FILE_TOO_LARGE` | Upload exceeds size limit |
| `400` | `UNSUPPORTED_FILE_TYPE` | MIME type not accepted |
| `401` | `UNAUTHORIZED` | Missing or expired access token |
| `403` | `FORBIDDEN` | Authenticated but not authorised (e.g., accessing another user's scan) |
| `404` | `NOT_FOUND` | Resource does not exist |
| `409` | `CONFLICT` | Duplicate resource (e.g., email already registered) |
| `422` | `UNPROCESSABLE_ENTITY` | FastAPI/Pydantic validation error (schema mismatch) |
| `429` | `RATE_LIMITED` | Too many requests |
| `500` | `INTERNAL_SERVER_ERROR` | Unexpected server error |
| `503` | `SERVICE_UNAVAILABLE` | Inference engine or database unavailable |

---

## Rate Limiting

| Endpoint group | Limit |
|---------------|-------|
| `POST /auth/login` | 10 requests / minute / IP |
| `POST /auth/register` | 5 requests / minute / IP |
| `POST /scans` | 30 requests / minute / user |
| `POST /larvae-scans` | 10 requests / minute / user |
| All other endpoints | 120 requests / minute / user |

Exceeded limits return `429 Too Many Requests` with a `Retry-After` header.

---

## Pagination

All list endpoints support:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | `1` | Page number (1-indexed) |
| `per_page` | integer | `20` | Items per page (max 100) |

---

## OpenAPI Schema

The full OpenAPI 3.1 schema is auto-generated by FastAPI:
- **Swagger UI:** `GET /docs`
- **ReDoc:** `GET /redoc`
- **Raw JSON:** `GET /openapi.json`
