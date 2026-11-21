"""Security utilities: JWT, password hashing, rate limiting."""
from __future__ import annotations

import hashlib
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from jose import JWTError, jwt

from app.config import settings

# ---------------------------------------------------------------------------
# Argon2id password hashing
# ---------------------------------------------------------------------------
_ph = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
    salt_len=16,
)


def hash_password(plain: str) -> str:
    """Hash a plaintext password with Argon2id."""
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against an Argon2id hash."""
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    """Check if the hash needs to be rehashed with updated parameters."""
    return _ph.check_needs_rehash(hashed)


# ---------------------------------------------------------------------------
# Token hashing (for refresh token storage)
# ---------------------------------------------------------------------------

def hash_token(token: str) -> str:
    """SHA-256 hash a token for secure storage."""
    return hashlib.sha256(token.encode()).hexdigest()


# ---------------------------------------------------------------------------
# JWT access tokens
# ---------------------------------------------------------------------------

def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict[str, Any]) -> tuple[str, datetime]:
    """Create a signed JWT refresh token. Returns (token, expires_at)."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh", "jti": secrets.token_hex(16)})
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, expire


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


# ---------------------------------------------------------------------------
# Rate limiting (Redis-backed with in-memory fallback)
# ---------------------------------------------------------------------------
from app.core.rate_limit import (
    check_login_rate_limit,
    clear_login_rate_limit,
    check_password_reset_rate_limit,
    check_password_reset_confirm_rate_limit,
    rate_limiter,
)

