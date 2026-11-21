# Vectora AI — Release Integrity Audit: Security Remediation & Controls Verification

**Document:** `reports/v2-security-remediation.md`  
**Date:** November 11, 2026  
**Auditor:** Senior Security & DevOps Engineer  
**Status:** AUDIT COMPLETE — 2 SECURITY GAPS IDENTIFIED (`SEC-GAP-01`, `SEC-GAP-02`)

---

## 1. Executive Summary

This audit evaluates the 7 critical security controls specified in the Vectora AI 2.0 Product Implementation Specification. Each control was inspected at the source code level, tested against regression test suites, and audited for architectural resilience.

### Control Status Matrix

| # | Security Control | Source File | Implementation Status | Test Coverage |
|---|---|---|:---:|:---:|
| 1 | **CSRF Validation** | `backend/app/dependencies.py` | **PASS** | `test_csrf_protection_requires_bearer_token` |
| 2 | **Redis-Backed Rate Limiting** | `backend/app/core/security.py` | **GAP** (In-memory dict, not Redis) | Partial (Called in `login_user`) |
| 3 | **Password Reset** | `backend/app/api/auth.py` | **GAP** (Stub endpoint only) | Untested |
| 4 | **Refresh-Token Rotation** | `backend/app/services/auth_service.py` | **PASS** | `test_refresh_token_rotation` |
| 5 | **Refresh-Token Reuse Detection** | `backend/app/services/auth_service.py` | **PASS** | `test_refresh_token_rotation` |
| 6 | **Cookie Security** | `backend/app/api/auth.py` | **PASS** | `test_login_success`, `test_refresh_token_rotation` |
| 7 | **Cross-User Authorization** | `backend/app/services/adult_service.py`, `backend/app/api/submissions.py` | **PASS** | `test_cross_user_submission_access_forbidden` |

---

## 2. Detailed Audit by Control

### 2.1 CSRF Validation
- **Source File:** [`backend/app/dependencies.py`](file:///home/nimr/Projects/mosqscan/backend/app/dependencies.py#L35-L60)
- **Implementation Method:**
  API state mutation routes (`POST /api/v1/adult/submit`, `POST /api/v1/larvae/submit`, `DELETE /api/v1/submissions/{id}`) do not accept ambient cookie credentials for authorization. Instead, they strictly require an explicit `Authorization: Bearer <JWT_ACCESS_TOKEN>` header extracted via `HTTPBearer()`. Because browsers do not automatically attach custom `Authorization` headers on cross-site requests, cross-site request forgery is mitigated by design.
- **Test Name:** `test_csrf_protection_requires_bearer_token` in [`backend/tests/test_security.py`](file:///home/nimr/Projects/mosqscan/backend/tests/test_security.py#L109-L116)
- **Actual Test Output:**
  ```text
  backend/tests/test_security.py::test_csrf_protection_requires_bearer_token PASSED [ 71%]
  ```
- **Verdict:** **PASS**

---

### 2.2 Redis-Backed Rate Limiting
- **Source File:** [`backend/app/core/security.py`](file:///home/nimr/Projects/mosqscan/backend/app/core/security.py#L87-L117)
- **Implementation Method:**
  The current implementation uses a local in-memory Python dictionary:
  ```python
  _rate_limit_store: dict[str, list[float]] = {}

  def check_login_rate_limit(ip: str) -> None:
      now = time.time()
      window = settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS # 900s
      limit = settings.LOGIN_RATE_LIMIT_ATTEMPTS         # 5
      attempts = [t for t in _rate_limit_store.get(ip, []) if now - t < window]
      if len(attempts) >= limit:
          raise RateLimitException(...)
      attempts.append(now)
      _rate_limit_store[ip] = attempts
  ```
- **Security Gap Identified (`SEC-GAP-01`):**
  While `REDIS_URL` is configured in `.env` and `settings.py`, the rate limiter does **NOT connect to Redis**. Under a multi-worker Uvicorn deployment or containerized cluster, the rate limit state is partitioned per worker process and is cleared on application restart.
- **Test Name:** None dedicated. Executed indirectly during invalid login attempts in `test_auth.py`.
- **Verdict:** **GAP** — Must be migrated to `redis.setex` / sliding window Lua script before production deployment.

---

### 2.3 Password Reset Workflow
- **Source File:** [`backend/app/api/auth.py`](file:///home/nimr/Projects/mosqscan/backend/app/api/auth.py#L116-L125)
- **Implementation Method:**
  ```python
  @router.post("/password-reset")
  def password_reset(payload: PasswordResetRequest):
      """Initiate password reset (stub — email not implemented)."""
      logger.info("Password reset requested for %s", payload.email)
      return {
          "message": "If that email exists, a reset link has been sent."
      }
  ```
- **Security Gap Identified (`SEC-GAP-02`):**
  The endpoint is an unauthenticated stub. It prevents account enumeration by returning a constant generic message, but it does **not generate a cryptographic reset token**, does not store an expiry timestamp in the database, and does not provide an endpoint to consume the token and submit a new password.
- **Test Name:** No unit or integration test exists for this endpoint.
- **Verdict:** **INCOMPLETE** — Missing token generation and update password endpoint.

---

### 2.4 Refresh-Token Rotation
- **Source File:** [`backend/app/services/auth_service.py`](file:///home/nimr/Projects/mosqscan/backend/app/services/auth_service.py#L75-L122)
- **Implementation Method:**
  When `/api/v1/auth/refresh` is invoked:
  1. The existing refresh token is decoded and verified against JWT secret and expiry.
  2. The SHA-256 hash of the token is queried in the `refresh_tokens` database table.
  3. The current token record is immediately marked `revoked = True`.
  4. A new cryptographic refresh token is generated with a fresh 7-day expiration timestamp.
  5. The new token's SHA-256 hash is inserted into `refresh_tokens`.
  6. A new 15-minute access token and new refresh cookie are returned to the caller.
- **Test Name:** `test_refresh_token_rotation` in [`backend/tests/test_auth.py`](file:///home/nimr/Projects/mosqscan/backend/tests/test_auth.py#L83-L105)
- **Actual Test Output:**
  ```text
  backend/tests/test_auth.py::test_refresh_token_rotation PASSED [ 35%]
  ```
- **Verdict:** **PASS**

---

### 2.5 Refresh-Token Reuse Detection
- **Source File:** [`backend/app/services/auth_service.py`](file:///home/nimr/Projects/mosqscan/backend/app/services/auth_service.py#L98-L106)
- **Implementation Method:**
  If a client submits a refresh token whose hash in `refresh_tokens` already has `revoked == True` (indicating an old token was intercepted or reused):
  ```python
  if db_token.revoked:
      # Potential token reuse — revoke ALL tokens for this user
      db.query(RefreshToken).filter(
          RefreshToken.user_id == db_token.user_id
      ).update({"revoked": True})
      db.commit()
      raise AuthException(
          status_code=401,
          error_code="TOKEN_REUSE",
          message="Refresh token has already been used. Session revoked.",
      )
  ```
- **Test Name:** `test_refresh_token_rotation` (second phase) in [`backend/tests/test_auth.py`](file:///home/nimr/Projects/mosqscan/backend/tests/test_auth.py#L101-L105)
- **Actual Test Output:**
  ```python
  # Using old refresh token again must fail (token reuse detection)
  reuse_res = client.post("/api/v1/auth/refresh", cookies={"refresh_token": old_refresh})
  assert reuse_res.status_code == 401
  assert reuse_res.json()["error_code"] == "TOKEN_REUSE"
  ```
  ```text
  backend/tests/test_auth.py::test_refresh_token_rotation PASSED [ 35%]
  ```
- **Verdict:** **PASS**

---

### 2.6 Cookie Security
- **Source File:** [`backend/app/api/auth.py`](file:///home/nimr/Projects/mosqscan/backend/app/api/auth.py#L58-L68,L84-L94)
- **Implementation Method:**
  Refresh tokens are issued via HTTP response headers with the following flags:
  ```python
  response.set_cookie(
      key="refresh_token",
      value=refresh_token,
      httponly=True,             # Blocks JavaScript document.cookie access
      secure=True,               # Transmitted only over HTTPS (or localhost testing)
      samesite="lax",            # Prevents ambient transmission on cross-origin POST
      max_age=7 * 24 * 3600,     # Explicit 7-day TTL
      path="/api/v1/auth",       # Scoped strictly to auth routes; omitted on data routes
  )
  ```
- **Test Name:** `test_login_success` in `backend/tests/test_auth.py`
- **Actual Test Output:**
  ```text
  backend/tests/test_auth.py::test_login_success PASSED [ 26%]
  ```
- **Verdict:** **PASS**

---

### 2.7 Cross-User Authorization (Broken Object Level Authorization — BOLA)
- **Source File:**
  - [`backend/app/services/adult_service.py`](file:///home/nimr/Projects/mosqscan/backend/app/services/adult_service.py#L130-L135)
  - [`backend/app/api/submissions.py`](file:///home/nimr/Projects/mosqscan/backend/app/api/submissions.py#L136-L165)
- **Implementation Method:**
  Every data-access and data-mutation route enforces ownership derived directly from the verified JWT sub claim (`current_user.id`), not from client query parameters:
  ```python
  if submission.user_id != user.id:
      raise AuthorizationError("Access denied to this resource")
  ```
- **Test Name:** `test_cross_user_submission_access_forbidden` in [`backend/tests/test_security.py`](file:///home/nimr/Projects/mosqscan/backend/tests/test_security.py#L30-L45)
- **Actual Test Output:**
  ```text
  backend/tests/test_security.py::test_cross_user_submission_access_forbidden PASSED [ 58%]
  ```
  Verified that User 2 attempting to view User 1's submission details, download User 1's specimen photograph, or delete User 1's submission receives `HTTP 403 Forbidden`.
- **Verdict:** **PASS**

---

## 3. Remediation Action Plan

1. **`SEC-GAP-01` (Redis Rate Limiting):**
   - Replace `_rate_limit_store` in `backend/app/core/security.py` with an async Redis client calling `redis.set(f"rl:{ip}", count, ex=900)`. Fall back to memory dictionary only if Redis connection fails.
2. **`SEC-GAP-02` (Password Reset Completion):**
   - Implement `POST /api/v1/auth/password-reset/confirm` accepting `{"token": str, "new_password": str}`.
   - Implement a cryptographic token generator storing `reset_token_hash` and `reset_expires_at` in the `users` table.
