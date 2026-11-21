# Vectora AI — Backend Security Gaps and Threat Audit

**Date:** 2026-11-11  
**Auditor:** Senior Software Security & Quality Engineering  
**System:** Vectora AI Backend API  
**Status:** ACTION REQUIRED FOR PRODUCTION DEPLOYMENT

---

## 1. Executive Summary

This document reports the security posture of the Vectora AI backend.  
Core cryptographic mechanisms and resource isolation controls are correctly implemented and verified.  
Three security gaps were identified during the quality gate review:
1. Absence of explicit CSRF token header validation on cookie-based token refresh.
2. In-memory rate limiting that does not persist or synchronize across multi-worker environments.
3. A stubbed, non-functional password reset endpoint.

These items do not block local development or internal testing.  
They must be resolved before deploying the backend to public networks.

---

## 2. Verified Security Controls

The following security controls were verified through automated tests:

### 2.1 Password Hashing

- **Algorithm:** Argon2id (via `passlib[argon2]` and `argon2-cffi`).
- **Configuration:**
  - Memory cost: 65,536 KiB (64 MiB).
  - Time cost: 3 iterations.
  - Parallelism: 4 threads.
  - Salt: Cryptographically random per-password salt (16 bytes).
- **Verification:** Legacy SHA-256 and MD5 hashes are rejected. Argon2id hash verification passed in `test_auth.py`.

### 2.2 JWT Authentication

- **Algorithm:** HMAC-SHA256 (`HS256`).
- **Access Token Lifetime:** 15 minutes.
- **Payload Validation:** `sub` (user ID), `role`, `exp`, `iat`, and `token_type` are validated.
- **Verification:** Expired tokens, tokens with tampered signatures, and tokens with missing claims are rejected with HTTP 401.

### 2.3 Refresh Token Security

- **Storage:** Refresh tokens are hashed using SHA-256 before storage in PostgreSQL.
- **Rotation:** Every refresh request issues a new refresh token and revokes the prior token.
- **Reuse Detection:** If an already-revoked refresh token is submitted, the backend invalidates all active tokens associated with that user session.
- **Cookie Security:** Refresh tokens are delivered via `HttpOnly`, `SameSite=lax`, and `Secure` (in production) cookies.

### 2.4 Multi-Tenant Authorization and User Isolation

- Every database query for submissions, images, and job results enforces `WHERE user_id = current_user.id`.
- Accessing another user's submission or job returns HTTP 403 Forbidden.
- Role-based authorization (`admin`, `researcher`, `user`) protects administrative routes (`/api/v1/admin/*`).

### 2.5 Media Upload Hardening

- **MIME & Signature Verification:** Real file headers are inspected using `python-magic` / byte signatures. Uploads with mismatched extensions (e.g., `.exe` renamed to `.jpg`) are rejected.
- **Decompression Bomb Protection:** Pillow's `Image.MAX_IMAGE_PIXELS` is enforced ($8192 \times 8192$). Decompression bombs raise HTTP 422 and terminate processing without memory exhaustion.
- **File Size Caps:** 20MB for adult images; 100MB for larvae videos. Enforced before stream processing.
- **Path Traversal Mitigation:** Storage keys use sanitized UUIDs (`uuid4().hex`). User-supplied filenames are stripped of directory separators (`/`, `\`) and null bytes.

---

## 3. Confirmed Security Gaps

### 3.1 Gap 1: CSRF Protection on Cookie-Based Token Refresh

- **Severity:** Medium
- **Location:** `backend/app/api/auth.py` (`POST /api/v1/auth/refresh`)
- **Vulnerability Description:**  
  The refresh endpoint retrieves the refresh token from an HTTP-only cookie (`refresh_token`).  
  The browser automatically includes this cookie in cross-site requests subject to `SameSite=lax` policies.  
  While `SameSite=lax` blocks standard cross-site POST form submissions, it does not provide defense-in-depth against subdomain takeovers, legacy browsers, or top-level navigation variations.  
  The endpoint does not currently require a matching CSRF header token (e.g., `X-CSRF-Token`).
- **Remediation Plan:**
  1. Implement a double-submit CSRF cookie pattern or generate an anti-CSRF token on login.
  2. Require an `X-CSRF-Token` header on all `POST /api/v1/auth/refresh` requests.
  3. Validate that the header matches the anti-CSRF token before issuing new tokens.

### 3.2 Gap 2: In-Memory Rate Limiting

- **Severity:** Medium
- **Location:** `backend/app/core/security.py` (`_rate_limit_store`)
- **Vulnerability Description:**  
  Rate limiting for authentication endpoints uses an in-memory dictionary.  
  In a production deployment with multiple Uvicorn worker processes or horizontal container replicas, this memory is not shared.  
  An attacker can bypass rate limits by distributing requests across worker processes.  
  Additionally, server restarts clear the rate-limit history, allowing immediate brute-force retries.
- **Remediation Plan:**
  1. Migrate the rate-limiting store from in-memory Python structures to Redis.
  2. Implement an atomic sliding-window algorithm using Redis transactions (`MULTI`/`EXEC`) or Lua scripts.
  3. Rate limit by client IP address and by target username/email.

### 3.3 Gap 3: Non-Functional Password Reset Flow

- **Severity:** Low (Incomplete Feature)
- **Location:** `backend/app/api/auth.py` (`POST /api/v1/auth/password-reset`)
- **Vulnerability Description:**  
  The password reset route is currently a placeholder:
  ```python
  @router.post("/password-reset")
  def request_password_reset(data: PasswordResetRequest):
      return {"message": "If this email is registered, a reset link will be sent."}
  ```
  The endpoint does not generate cryptographic reset tokens.  
  It does not record reset requests in the database.  
  No password update endpoint exists to complete a reset.
- **Remediation Plan:**
  1. Create a `password_resets` table with `user_id`, `token_hash`, and `expires_at` (15-minute validity).
  2. Generate a secure random token (`secrets.token_urlsafe(32)`) and store its SHA-256 hash.
  3. Implement an email delivery adapter for dispatching reset links.
  4. Create `POST /api/v1/auth/password-reset/confirm` to validate the token and update the password.

---

## 4. Threat and Risk Matrix

| Threat ID | Description | Component | Likelihood | Impact | Current Mitigations | Action Required |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **THR-01** | Brute-force credential stuffing | `/api/v1/auth/login` | Medium | High | Argon2id cost; in-memory limiter | Migrate rate limiter to Redis |
| **THR-02** | Refresh token theft / replay | `/api/v1/auth/refresh` | Low | High | SHA-256 hash in DB; token rotation; reuse invalidation | Add `X-CSRF-Token` header |
| **THR-03** | Decompression bomb / DoS | `/api/v1/adult/submit` | Low | High | PIL pixel cap (67M px); 20MB file cap | Verified passing; maintain caps |
| **THR-04** | Variable frame rate video DoS | `/api/v1/larvae/submit` | Medium | Medium | ffprobe duration check; OpenCV decode check | Verified passing; maintain checks |
| **THR-05** | Unauthorized resource snooping | `/api/v1/submissions/*` | Medium | High | Row-level tenant isolation | Verified passing; maintain checks |
| **THR-06** | Out-of-Distribution spoofing | `/api/v1/adult/submit` | High | High | Status set to `EXPERIMENTAL_NOT_FIELD_VALIDATED` | Implement YOLO specimen detector & calibrated rejection |

---

## 5. Prioritized Remediation Roadmap

1. **Sprint 1 (Pre-Staging):**  
   - Replace in-memory rate limiter with Redis-backed atomic sliding window.  
   - Add double-submit CSRF token requirement to `/api/v1/auth/refresh`.
2. **Sprint 2 (Pre-Production):**  
   - Implement functional password reset token generation and verification endpoints.  
   - Configure external SMTP/SES service provider for password reset emails.
3. **Sprint 3 (ML Pipeline):**  
   - Integrate YOLOv11n specimen detection pipeline.  
   - Calibrate classification confidence with temperature scaling on held-out field datasets.
