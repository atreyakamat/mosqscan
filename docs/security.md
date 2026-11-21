# Vectora AI — Security Architecture & Threat Model

## 1. Authentication & Token Management

- **Password Hashing**: Uses `Argon2id` (RFC 9106) with memory cost 64 MB, 2 iterations, 2 parallelism lanes. Plaintext passwords are never stored or logged.
- **Access Tokens**: Short-lived (15 minutes) signed JWT (`HS256`).
- **Refresh Tokens**: Rotating 7-day tokens stored as SHA-256 hashes in database.
- **Refresh Cookie**: Transmitted as `HttpOnly; SameSite=Lax` cookie.
- **Token Reuse Detection**: If a revoked refresh token is presented, all active sessions for that user account are instantly revoked.
- **Mobile Credentials**: Stored in hardware-backed `AndroidKeyStore` using AES-256-GCM encryption. Never stored in plaintext SharedPreferences.

---

## 2. Authorization & Data Ownership

- **Strict User Scoping**: Queries for submissions, media files, and processing jobs always filter by `user_id == current_user.id`. Cross-user access returns `403 Forbidden`.
- **Role-Based Access Control (RBAC)**: Only accounts with `role == 'admin'` can access `/api/v1/admin/*` endpoints.

---

## 3. Upload & File Protection

- **File Sanitization**: `sanitize_filename` strips directory traversal (`../`, `..\`), replaces path separators, strips null bytes, and removes leading dots.
- **File Signature Inspection**: Magic byte inspection verifies genuine JPEG (`\xff\xd8\xff`) and PNG (`\x89PNG\r\n\x1a\n`) payloads. Extension spoofing is rejected.
- **Internal Paths Hidden**: API responses never expose disk file paths.
