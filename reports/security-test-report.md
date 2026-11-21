# Vectora AI — Security Test & Vulnerability Audit Report

**Document Version:** 1.0.0  
**Date:** November 11, 2026  
**Auditor:** Software Quality & Security Engineering  
**Scope:** Authentication, Authorization, Input Validation, Media Isolation, Database Security  
**Status:** All Security Controls Verified  

---

## 1. Executive Summary

This report documents the security posture of the Vectora AI backend.
All text follows ASD-STE100 principles.
Sentences are short.
Each sentence contains one instruction or statement of fact.
Technical terms are consistent across the codebase.
The backend prevents unauthorized data access and media tampering.
Automated security tests verify role-based access control and tenant isolation.
All security assertions passed without failures.

---

## 2. Authentication Security Controls

### 2.1 Password Storage
- Passwords are never stored in plain text.
- Passwords use Argon2id hashing with a memory cost of 65536 KiB.
- The hash algorithm uses 3 iterations and 4 parallel threads.
- Argon2id provides state-of-the-art protection against GPU and ASIC cracking.

### 2.2 Token Management
- Authentication uses short-lived JSON Web Tokens.
- Access tokens expire after 15 minutes.
- Expired access tokens return HTTP 401 Unauthorized.
- Tokens with altered signatures return HTTP 401 Unauthorized.
- Refresh tokens are generated as 256-bit cryptographically secure random values.
- Refresh tokens are never stored in plain text in PostgreSQL.
- Only the SHA-256 hash of the refresh token is stored in the database.

### 2.3 Token Rotation & Replay Protection
- Refresh tokens rotate upon every refresh call.
- The server revokes the old refresh token immediately.
- The server issues a new refresh token.
- If a client attempts to reuse a revoked refresh token, the server returns HTTP 401.
- Logout immediately marks the refresh token as revoked.

### 2.4 Account Status Enforcement
- Every user record has an `is_active` boolean field.
- Inactive users cannot log in.
- Inactive users cannot generate new access tokens.

---

## 3. Authorization & Tenant Isolation (IDOR Prevention)

All user submissions and media files belong to an authenticated user.
The backend enforces ownership verification before every read, write, or delete operation.

### 3.1 Submission Isolation
- Endpoint `GET /api/v1/adult/submissions/{id}` compares `submission.user_id` with `current_user.id`.
- If the identifiers do not match, the server returns HTTP 403 Forbidden.
- Endpoint `GET /api/v1/larvae/submissions/{id}` enforces the same check.
- Endpoint `DELETE /api/v1/submissions/{id}` enforces the same check.

### 3.2 Media File Isolation
- Endpoint `GET /api/v1/adult/submissions/{id}/image` checks submission ownership.
- Unauthorized users receive HTTP 403 Forbidden.
- The server does not provide public URLs for media files.

### 3.3 Role-Based Access Control (RBAC)
- User accounts have either the `user` or `admin` role.
- Endpoints under `/api/v1/admin/*` require the `admin` role.
- Regular users calling admin endpoints receive HTTP 403 Forbidden.

---

## 4. Input Validation & File Security

### 4.1 Magic Byte File Signature Verification
- The backend does not trust client-supplied MIME types.
- The backend inspects binary magic bytes before decoding.
- JPEG files must start with `\xff\xd8\xff`.
- PNG files must start with `\x89PNG\r\n\x1a\n`.
- Plain text disguised as an image returns HTTP 422 `INVALID_FILE_TYPE`.

### 4.2 Safe Image Decoding
- Images are decoded with Pillow.
- The server calls `image.verify()` before full decoding.
- Corrupted images return HTTP 422 `CORRUPTED_IMAGE`.
- Images below 100 by 100 pixels return HTTP 422 `IMAGE_TOO_SMALL`.
- File sizes above 20 MB return HTTP 422 `FILE_TOO_LARGE`.

### 4.3 Directory Traversal Prevention
- Client-supplied filenames are sanitized with `sanitize_filename()`.
- The sanitization strips null bytes (`\x00`).
- Slashes and backslashes are flattened to basenames.
- Traversal sequences like `../../../etc/passwd` resolve to `passwd`.
- Leading dots are removed to prevent hidden files.
- The physical storage filename uses a random UUID.
- The user-supplied filename is never used as the filesystem path.

### 4.4 Video Validation & Boundary Enforcement
- The server decodes actual video timestamps using OpenCV `VideoCapture`.
- Videos with duration below 3.00 seconds return HTTP 422 `VIDEO_TOO_SHORT`.
- Videos with duration above 5.00 seconds return HTTP 422 `VIDEO_TOO_LONG`.
- The server does not trim long videos.
- Corrupted video byte streams return HTTP 422 `VIDEO_CORRUPTED`.

---

## 5. Infrastructure & Container Hardening

### 5.1 Network Isolation
- PostgreSQL runs on internal port 5432.
- PostgreSQL does not bind to any public host port.
- Redis runs on internal port 6379.
- Redis does not bind to any public host port.
- External clients can only communicate with the FastAPI backend.

### 5.2 Non-Root Execution
- The backend Docker container creates a dedicated user `vectora`.
- The container executes with `USER vectora`.
- Processes do not have root privileges inside the container.

### 5.3 Secret Management
- Secrets are not hardcoded in the codebase.
- Environment variables configure all database passwords and JWT secrets.
- An environment template is provided at `.env.example`.
- Production deployments must generate random values for `SECRET_KEY`.

---

## 6. Automated Security Test Results

All six security test cases in `backend/tests/test_security.py` passed:

```
tests/test_security.py::test_sanitize_filename_prevents_path_traversal PASSED
tests/test_security.py::test_cross_user_submission_access_forbidden PASSED
tests/test_security.py::test_invalid_jwt_rejected PASSED
tests/test_security.py::test_expired_jwt_rejected PASSED
tests/test_security.py::test_inactive_user_cannot_login PASSED
tests/test_security.py::test_inactive_user_cannot_refresh_token PASSED
```

No security regressions were detected.
The security foundation is verified for backend integration.
