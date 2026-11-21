# Vectora AI — API Contract Specification

**Document Version:** 1.0.0  
**Date:** November 11, 2026  
**Target Clients:** Web Frontend (Next.js), Mobile Client (Android Kotlin CameraX)  
**OpenAPI Specification:** [`docs/openapi.json`](file:///home/nimr/Projects/mosqscan/docs/openapi.json)

---

## 1. Overview

This document specifies the stable API contract for Vectora AI.
All endpoints use the prefix `/api/v1`.
All requests and responses use the JSON format.
Multipart file uploads use the `multipart/form-data` format.
All timestamps use UTC in ISO-8601 format (`YYYY-MM-DDTHH:MM:SSZ`).
All entities use UUID string identifiers.

---

## 2. Standard Response Envelope

All API responses use a standard envelope.

### Successful Response
```json
{
  "success": true,
  "data": { ... }
}
```
*Note: Certain resource endpoints return the resource object directly at the top level for REST compatibility.*

### Error Response
```json
{
  "success": false,
  "error_code": "ERROR_CODE_STRING",
  "message": "Human-readable description of the error.",
  "detail": []
}
```

### Standard HTTP Status Codes

| Code | Meaning | Reason |
| :---: | :--- | :--- |
| **200** | OK | Request succeeded. |
| **201** | Created | Resource created successfully. |
| **202** | Accepted | Job queued for asynchronous background processing. |
| **400** | Bad Request | Request body or parameters are malformed. |
| **401** | Unauthorized | Authentication token is missing, expired, or invalid. |
| **403** | Forbidden | User does not own this resource or lacks permission. |
| **404** | Not Found | Requested entity does not exist. |
| **422** | Unprocessable Entity | Validation failed (corrupted file, wrong duration, wrong dimensions). |
| **429** | Too Many Requests | Rate limit exceeded. |
| **500** | Internal Error | Server encountered an unexpected error. |
| **503** | Service Unavailable | Model artifact missing or corrupted. |

---

## 3. Authentication Endpoints

### 3.1 Register User
- **Method:** `POST`
- **Route:** `/api/v1/auth/register`
- **Authentication:** None
- **Request Body:**
  ```json
  {
    "email": "field_worker@vectora.ai",
    "username": "field_worker_01",
    "password": "SecurePassword123!"
  }
  ```
- **Password Rules:** Minimum 8 characters. Must contain at least one uppercase letter, one lowercase letter, one digit, and one special symbol.
- **Success Response (201 Created):**
  ```json
  {
    "id": "e568bb99-a389-4d6a-8b1e-fe6800000001",
    "email": "field_worker@vectora.ai",
    "username": "field_worker_01",
    "role": "user",
    "is_active": true,
    "created_at": "2026-11-11T12:00:00Z"
  }
  ```

### 3.2 Login
- **Method:** `POST`
- **Route:** `/api/v1/auth/login`
- **Authentication:** None
- **Request Body:**
  ```json
  {
    "email_or_username": "field_worker_01",
    "password": "SecurePassword123!"
  }
  ```
- **Success Response (200 OK):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "a1b2c3d4e5f6...",
    "token_type": "bearer",
    "expires_in": 900
  }
  ```
- **Note:** The response also sets an HTTP-only secure cookie named `refresh_token`.

### 3.3 Refresh Access Token
- **Method:** `POST`
- **Route:** `/api/v1/auth/refresh`
- **Authentication:** None (accepts refresh token in request body or cookie)
- **Request Body:**
  ```json
  {
    "refresh_token": "a1b2c3d4e5f6..."
  }
  ```
- **Success Response (200 OK):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "f6e5d4c3b2a1...",
    "token_type": "bearer",
    "expires_in": 900
  }
  ```
- **Behavior:** The submitted refresh token is immediately revoked. A new refresh token is issued.

### 3.4 Logout
- **Method:** `POST`
- **Route:** `/api/v1/auth/logout`
- **Authentication:** Optional refresh token
- **Success Response (200 OK):**
  ```json
  {
    "message": "Successfully logged out"
  }
  ```

### 3.5 Get Current User Profile
- **Method:** `GET`
- **Route:** `/api/v1/auth/me`
- **Authentication:** `Bearer <access_token>`
- **Success Response (200 OK):**
  ```json
  {
    "id": "e568bb99-a389-4d6a-8b1e-fe6800000001",
    "email": "field_worker@vectora.ai",
    "username": "field_worker_01",
    "role": "user",
    "is_active": true,
    "created_at": "2026-11-11T12:00:00Z"
  }
  ```

---

## 4. Adult Mosquito Identification API

### 4.1 Submit Image for Identification
- **Method:** `POST`
- **Route:** `/api/v1/adult/submit`
- **Authentication:** `Bearer <access_token>`
- **Content-Type:** `multipart/form-data`
- **Form Fields:**
  - `file`: Image binary data (JPEG or PNG).
- **Validation Rules:**
  - File size must not exceed 20 MB.
  - Image dimensions must measure at least 100 by 100 pixels.
  - Magic bytes must match JPEG or PNG signatures.
- **Success Response (201 Created):**
  ```json
  {
    "id": "60a4f32c-7b81-42cb-9964-16a44c688321",
    "status": "completed",
    "type": "adult",
    "created_at": "2026-11-11T14:30:00Z",
    "result": {
      "predicted_genus": "aedes",
      "confidence": 0.8841,
      "is_uncertain": false,
      "uncertainty_message": null,
      "all_scores": {
        "aedes": 0.8841,
        "anopheles": 0.0432,
        "culex": 0.0727
      },
      "model_version": "1.0.0",
      "model_artifact": "vectora_candidate_exp_b.onnx",
      "processing_time_ms": 58
    }
  }
  ```

### 4.2 Uncertain Identification Response Example
When maximum confidence is below the configurable threshold (default 0.50):
```json
{
  "id": "71b5a43d-8c92-53dc-aa75-27b55d799432",
  "status": "completed",
  "type": "adult",
  "created_at": "2026-11-11T14:32:00Z",
  "result": {
    "predicted_genus": null,
    "confidence": 0.3860,
    "is_uncertain": true,
    "uncertainty_message": "Uncertain identification. Manual inspection is advised.",
    "all_scores": {
      "aedes": 0.3860,
      "anopheles": 0.3618,
      "culex": 0.2522
    },
    "model_version": "1.0.0",
    "model_artifact": "vectora_candidate_exp_b.onnx",
    "processing_time_ms": 52
  }
}
```

### 4.3 Get Adult Submission by ID
- **Method:** `GET`
- **Route:** `/api/v1/adult/submissions/{submission_id}`
- **Authentication:** `Bearer <access_token>`
- **Ownership:** Enforced. Users can only access their own submissions.

### 4.4 Get Submission Image Data
- **Method:** `GET`
- **Route:** `/api/v1/adult/submissions/{submission_id}/image`
- **Authentication:** `Bearer <access_token>`
- **Response:** Raw binary image with appropriate `Content-Type: image/jpeg` or `image/png`.

### 4.5 List Adult Submissions (Paginated)
- **Method:** `GET`
- **Route:** `/api/v1/adult/submissions?page=1&page_size=20`
- **Authentication:** `Bearer <access_token>`
- **Success Response (200 OK):**
  ```json
  {
    "items": [ ... ],
    "total": 42,
    "page": 1,
    "page_size": 20
  }
  ```

---

## 5. Larvae Video API

### 5.1 Submit Larvae Video
- **Method:** `POST`
- **Route:** `/api/v1/larvae/submit`
- **Authentication:** `Bearer <access_token>`
- **Content-Type:** `multipart/form-data`
- **Form Fields:**
  - `file`: Video binary data (MP4 or WebM).
- **Duration Boundary Rules:**
  - Duration < 3.00 seconds: Rejected with `422 Unprocessable Entity` (`error_code: VIDEO_TOO_SHORT`).
  - Duration 3.00 to 5.00 seconds: Accepted for processing.
  - Duration > 5.00 seconds: Rejected with `422 Unprocessable Entity` (`error_code: VIDEO_TOO_LONG`).
- **Success Response (202 Accepted):**
  ```json
  {
    "job_id": "90e1f43a-2a10-48cb-8123-55d66e811122",
    "submission_id": "80d2e31b-1b09-37ba-7012-44c55d700011",
    "status": "queued",
    "message": "Video queued for processing"
  }
  ```

### 5.2 Get Video Processing Job Status
- **Method:** `GET`
- **Route:** `/api/v1/larvae/jobs/{job_id}`
- **Authentication:** `Bearer <access_token>`
- **Success Response (200 OK):**
  ```json
  {
    "id": "90e1f43a-2a10-48cb-8123-55d66e811122",
    "submission_id": "80d2e31b-1b09-37ba-7012-44c55d700011",
    "status": "completed",
    "frame_count": 350,
    "valid_frames": 342,
    "started_at": "2026-11-11T14:40:01Z",
    "completed_at": "2026-11-11T14:40:03Z",
    "error_message": null
  }
  ```

### 5.3 Get Larvae Submission Result
- **Method:** `GET`
- **Route:** `/api/v1/larvae/submissions/{submission_id}`
- **Authentication:** `Bearer <access_token>`
- **Success Response (200 OK):**
  ```json
  {
    "id": "80d2e31b-1b09-37ba-7012-44c55d700011",
    "type": "larvae",
    "status": "completed",
    "model_status": "model_not_validated",
    "message": "Larvae identification model is not yet field-validated and must not be used for production predictions.",
    "analysis": {
      "meniscus_detected": true,
      "motion_detected": true,
      "avg_orientation_deg": 44.2,
      "valid_frames": 342,
      "total_frames": 350
    }
  }
  ```

---

## 6. Model Registry Information Endpoints

### 6.1 Get Active Model Information
- **Method:** `GET`
- **Route:** `/api/v1/models/info`
- **Authentication:** None
- **Success Response (200 OK):**
  ```json
  {
    "product": "Vectora AI",
    "model_version": "1.0.0",
    "created_at": "2026-11-11",
    "adult_classifier": {
      "architecture": "torchvision.efficientnet_b0",
      "num_classes": 3,
      "classes": ["aedes", "anopheles", "culex"],
      "input_size": [224, 224],
      "input_color_format": "RGB",
      "confidence_threshold": 0.50,
      "status": "EXPERIMENTAL_NOT_FIELD_VALIDATED",
      "scientific_disclaimer": "Visual identification only. Research pilot model. Not field-validated."
    },
    "larvae_model": {
      "status": "not_validated",
      "prediction": null,
      "message": "Larvae identification model is not yet field-validated and must not be used for production predictions."
    }
  }
  ```

### 6.2 Get Model Health & Checksum Verification
- **Method:** `GET`
- **Route:** `/api/v1/models/health`
- **Authentication:** None
- **Success Response (200 OK):**
  ```json
  {
    "status": "healthy",
    "model_version": "1.0.0",
    "artifact": "vectora_candidate_exp_b.onnx",
    "checksum_verified": true,
    "actual_sha256": "d644b9cd9c952d461bbfbb44e8b1926cdcf9bbbfb9cd43f85065cbed0d7b1499"
  }
  ```
