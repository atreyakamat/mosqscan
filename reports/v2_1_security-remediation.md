# Vectora AI 2.1 — Security Remediation Report

## 1. Executive Summary

This document describes the security remediations completed for Vectora AI 2.1.
Two primary security vulnerabilities were resolved:
- **SEC-GAP-01**: Missing distributed rate limiting on authentication routes.
- **SEC-GAP-02**: Incomplete password reset flow with missing token lifecycle and session invalidation.

Both remediations were implemented, deployed to Docker, and verified with automated test suites.

---

## 2. Distributed Rate Limiter Architecture (SEC-GAP-01)

### 2.1 Design and Implementation
A sliding-window rate limiter was implemented in `backend/app/core/rate_limit.py`.
The limiter operates directly on Redis using an atomic Lua script.
This design prevents race conditions during high-concurrency requests.

#### Sliding Window Algorithm
1. The limiter assigns a unique key based on action prefix and client IP address (for example `rl:login:127.0.0.1`).
2. An atomic Redis Lua script executes the following operations:
   - Removes expired timestamps older than `now - window_seconds` using `ZREMRANGEBYSCORE`.
   - Counts current entries in the sorted set using `ZCARD`.
   - If count is less than `max_attempts`, adds `now` to the set with `ZADD` and sets key expiry with `EXPIRE`.
   - Returns allowed status (`1`) or blocked status (`0`), remaining quota, and retry duration.

### 2.2 Fault-Tolerant In-Memory Fallback
If Redis becomes unavailable, the rate limiter falls back to a thread-safe local in-memory sliding window.
- The fallback uses Python `threading.Lock` to guarantee thread safety.
- Expired timestamps are purged on each request.
- The system continues to enforce rate limits even during Redis server failures.
- When Redis recovers, the system restores Redis operations automatically.

### 2.3 Configuration Parameters
The rate limits are managed in `backend/app/config.py`:
- `LOGIN_RATE_LIMIT_ATTEMPTS`: 5 attempts.
- `LOGIN_RATE_LIMIT_WINDOW_SECONDS`: 900 seconds (15 minutes).
- `PASSWORD_RESET_RATE_LIMIT_ATTEMPTS`: 5 attempts.
- `PASSWORD_RESET_RATE_LIMIT_WINDOW_SECONDS`: 900 seconds (15 minutes).

### 2.4 Verification Results
The test suite in `backend/tests/test_rate_limit.py` contains 6 automated tests:
- `test_rate_limiter_allows_under_limit`: PASSED.
- `test_rate_limiter_blocks_over_limit`: PASSED.
- `test_rate_limiter_concurrent_requests`: PASSED (10 parallel threads tested).
- `test_rate_limiter_expiry`: PASSED (window expiry restores allowance).
- `test_redis_connection_failure_safe_fallback`: PASSED (in-memory fallback enforces limit during outage).
- `test_api_login_rate_limiting_enforced`: PASSED (HTTP 429 returned after 5 failed login attempts).

---

## 3. Secure Password Reset Workflow (SEC-GAP-02)

### 3.1 Architecture Overview
A complete password reset workflow was implemented across backend models, database migrations, email notification service, and API routes.

### 3.2 Token Lifecycle and Cryptography
1. **Token Generation**:
   - The server creates a cryptographically secure 256-bit random token using `secrets.token_urlsafe(32)`.
   - The token contains 43 URL-safe characters.
2. **Token Storage**:
   - The raw token is never written to the database.
   - The server computes the SHA-256 hash of the token: `hashlib.sha256(raw_token.encode()).hexdigest()`.
   - The database stores only the token hash, user ID, expiration timestamp, and `used` boolean flag in `password_reset_tokens`.
3. **Token Expiration**:
   - Tokens expire after 15 minutes (`PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 15`).
   - Expired or invalid tokens return HTTP 422 with `INVALID_OR_EXPIRED_TOKEN` or `TOKEN_EXPIRED`.
4. **Single-Use Enforcement**:
   - When a token is consumed, `used` is set to `True` within an atomic transaction.
   - Subsequent reset attempts with the same token fail immediately.

### 3.3 Session Revocation
When a password reset completes successfully:
- The user password hash is updated using Argon2id (`argon2.PasswordHasher`).
- All active refresh tokens for the user in `refresh_tokens` are revoked (`revoked = True`).
- Existing active sessions on all devices are terminated immediately.

### 3.4 Account Enumeration Defense
- Endpoint: `POST /api/v1/auth/password-reset`
- Request: `{"email": "user@example.com"}`
- If the email exists: A reset token is created and sent via email.
- If the email does not exist: No token is created.
- In both cases, the endpoint returns HTTP 200 with the exact same response:
  ```json
  {"message": "If that email exists, a reset link has been sent."}
  ```
- Attackers cannot verify whether an email address is registered.

### 3.5 Log Hygiene
- `backend/app/services/email_service.py` provides email delivery abstraction (`console` and `smtp` modes).
- The service redacts raw reset tokens in log messages: `token=REDACTED`.
- Automated test `test_password_reset_does_not_log_tokens` verifies that raw tokens never appear in application logs.

### 3.6 Verification Results
The test suite in `backend/tests/test_password_reset.py` contains 9 automated tests:
- `test_password_reset_request_for_existing_user`: PASSED.
- `test_password_reset_request_nonexistent_user_prevents_enumeration`: PASSED.
- `test_password_reset_confirm_successful_flow`: PASSED.
- `test_password_reset_token_single_use_enforcement`: PASSED.
- `test_password_reset_token_expiration`: PASSED.
- `test_password_reset_invalidates_existing_sessions`: PASSED.
- `test_password_reset_weak_password_rejected`: PASSED.
- `test_password_reset_rate_limiting`: PASSED.
- `test_password_reset_does_not_log_tokens`: PASSED.

---

## 4. Summary Table of Security Remediations

| Vulnerability ID | Description | Solution Implemented | Test Coverage |
| :--- | :--- | :--- | :--- |
| **SEC-GAP-01** | Missing Rate Limiting on Auth Routes | Redis atomic Lua sliding-window with local memory fallback | 6 unit/API tests + Live Docker test |
| **SEC-GAP-02** | Missing Password Reset Flow | SHA-256 hashed single-use tokens, 15m expiry, session invalidation | 9 unit/API tests + Live Docker test |
