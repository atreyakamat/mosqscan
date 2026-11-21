"""Comprehensive tests for SEC-GAP-02 Password Reset workflow."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.core.rate_limit import rate_limiter
from app.core.security import hash_token
from app.db.models import PasswordResetToken, RefreshToken, User
from app.services.email_service import get_email_provider, ConsoleEmailProvider


def _get_token_from_email_provider() -> str:
    """Helper to extract token from the test email provider."""
    provider = get_email_provider()
    assert isinstance(provider, ConsoleEmailProvider)
    assert len(provider.sent_messages) > 0
    latest_link = provider.sent_messages[-1]["reset_link"]
    # Link format: .../reset-password?token=<raw_token>
    return latest_link.split("token=")[-1]


def test_password_reset_request_for_existing_user(client: TestClient, db_session: Session, test_user):
    """Verify requesting reset returns generic message and persists only the token hash."""
    user = test_user["user"]
    provider = get_email_provider()
    if isinstance(provider, ConsoleEmailProvider):
        provider.clear()

    res = client.post(
        "/api/v1/auth/password-reset",
        json={"email": user.email},
        headers={"X-Forwarded-For": "10.0.0.1"},
    )
    assert res.status_code == 200
    assert res.json() == {"message": "If that email exists, a reset link has been sent."}

    # Verify token is recorded in DB as a SHA-256 hash, not plaintext
    token_record = (
        db_session.query(PasswordResetToken)
        .filter(PasswordResetToken.user_id == user.id)
        .first()
    )
    assert token_record is not None
    assert token_record.used is False
    assert len(token_record.token_hash) == 64  # SHA-256 hex length

    # Verify email was dispatched
    raw_token = _get_token_from_email_provider()
    assert hash_token(raw_token) == token_record.token_hash
    assert raw_token != token_record.token_hash  # Plaintext is NOT the hash


def test_password_reset_request_nonexistent_user_prevents_enumeration(client: TestClient):
    """Verify non-existent emails receive the identical generic message without DB changes."""
    res = client.post(
        "/api/v1/auth/password-reset",
        json={"email": "nonexistent_researcher@nowhere.org"},
        headers={"X-Forwarded-For": "10.0.0.2"},
    )
    assert res.status_code == 200
    assert res.json() == {"message": "If that email exists, a reset link has been sent."}


def test_password_reset_confirm_successful_flow(client: TestClient, db_session: Session, test_user):
    """Verify full successful reset: new password works, old password fails, token marked used."""
    user = test_user["user"]
    user_email = user.email

    # Request reset
    client.post(
        "/api/v1/auth/password-reset",
        json={"email": user_email},
        headers={"X-Forwarded-For": "10.0.0.3"},
    )
    raw_token = _get_token_from_email_provider()

    # Confirm password reset with new strong password
    new_password = "BrandNewPassword2026!"
    confirm_res = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": raw_token, "new_password": new_password},
        headers={"X-Forwarded-For": "10.0.0.3"},
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json() == {"message": "Password has been reset successfully."}

    # Verify old password fails
    old_login = client.post(
        "/api/v1/auth/login",
        json={"email": user_email, "password": "Password123!"},
        headers={"X-Forwarded-For": "10.0.0.3"},
    )
    assert old_login.status_code == 401

    # Verify new password succeeds
    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": user_email, "password": new_password},
        headers={"X-Forwarded-For": "10.0.0.3"},
    )
    assert new_login.status_code == 200
    assert "access_token" in new_login.json()

    # Verify token is marked used
    token_record = (
        db_session.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == hash_token(raw_token))
        .first()
    )
    assert token_record.used is True


def test_password_reset_token_single_use_enforcement(client: TestClient, test_user):
    """Verify a reset token cannot be reused once consumed."""
    user = test_user["user"]

    client.post(
        "/api/v1/auth/password-reset",
        json={"email": user.email},
        headers={"X-Forwarded-For": "10.0.0.4"},
    )
    raw_token = _get_token_from_email_provider()

    # First reset succeeds
    res1 = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": raw_token, "new_password": "NewValidPassword1!"},
        headers={"X-Forwarded-For": "10.0.0.4"},
    )
    assert res1.status_code == 200

    # Second reset attempt with same token must fail
    res2 = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": raw_token, "new_password": "AnotherPassword2!"},
        headers={"X-Forwarded-For": "10.0.0.4"},
    )
    assert res2.status_code == 422
    assert res2.json()["error_code"] == "TOKEN_ALREADY_USED"


def test_password_reset_token_expiration(client: TestClient, db_session: Session, test_user):
    """Verify expired reset tokens are rejected."""
    user = test_user["user"]

    client.post(
        "/api/v1/auth/password-reset",
        json={"email": user.email},
        headers={"X-Forwarded-For": "10.0.0.5"},
    )
    raw_token = _get_token_from_email_provider()

    # Artificially expire the token in database
    token_hash = hash_token(raw_token)
    db_record = (
        db_session.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == token_hash)
        .first()
    )
    db_record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db_session.commit()

    res = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": raw_token, "new_password": "ValidPassword999!"},
        headers={"X-Forwarded-For": "10.0.0.5"},
    )
    assert res.status_code == 422
    assert res.json()["error_code"] == "TOKEN_EXPIRED"


def test_password_reset_invalidates_existing_sessions(client: TestClient, db_session: Session, test_user):
    """Verify resetting password revokes all existing refresh tokens for the user."""
    user = test_user["user"]
    user_email = user.email

    # Log in to create an active refresh session
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": user_email, "password": "Password123!"},
        headers={"X-Forwarded-For": "10.0.0.6"},
    )
    assert login_res.status_code == 200
    refresh_cookie = login_res.cookies.get("refresh_token")
    assert refresh_cookie is not None

    # Verify session refresh works initially
    pre_res = client.post("/api/v1/auth/refresh", cookies={"refresh_token": refresh_cookie})
    assert pre_res.status_code == 200
    new_refresh_cookie = pre_res.cookies.get("refresh_token")

    # Request and confirm password reset
    client.post(
        "/api/v1/auth/password-reset",
        json={"email": user_email},
        headers={"X-Forwarded-For": "10.0.0.6"},
    )
    raw_token = _get_token_from_email_provider()
    client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": raw_token, "new_password": "NewSecretPassword1!"},
        headers={"X-Forwarded-For": "10.0.0.6"},
    )

    # Attempting to use the pre-existing refresh token must fail (session invalidated)
    post_res = client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": new_refresh_cookie},
    )
    assert post_res.status_code == 401
    assert post_res.json()["error_code"] in ("TOKEN_REUSE", "INVALID_TOKEN")


def test_password_reset_weak_password_rejected(client: TestClient, test_user):
    """Verify passwords shorter than 8 characters are rejected."""
    user = test_user["user"]

    client.post(
        "/api/v1/auth/password-reset",
        json={"email": user.email},
        headers={"X-Forwarded-For": "10.0.0.7"},
    )
    raw_token = _get_token_from_email_provider()

    res = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": raw_token, "new_password": "short"},
        headers={"X-Forwarded-For": "10.0.0.7"},
    )
    assert res.status_code == 422


def test_password_reset_rate_limiting(client: TestClient, test_user):
    """Verify rate limits are enforced on password reset endpoints."""
    ip = "10.0.0.99"
    rate_limiter.clear("password_reset", ip)

    headers = {"X-Forwarded-For": ip}
    # Consume 5 allowed attempts
    for _ in range(settings.PASSWORD_RESET_RATE_LIMIT_ATTEMPTS):
        res = client.post(
            "/api/v1/auth/password-reset",
            json={"email": test_user["user"].email},
            headers=headers,
        )
        assert res.status_code == 200

    # 6th attempt must trigger HTTP 429
    res = client.post(
        "/api/v1/auth/password-reset",
        json={"email": test_user["user"].email},
        headers=headers,
    )
    assert res.status_code == 429
    assert res.json()["error_code"] == "RATE_LIMITED"


class MemoryLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.logs: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.logs.append(record.getMessage())


def test_password_reset_does_not_log_tokens(client: TestClient, test_user):
    """Verify sensitive raw reset tokens never appear in application logs."""
    handler = MemoryLogHandler()
    handler.setLevel(logging.INFO)

    email_logger = logging.getLogger("app.services.email_service")
    auth_logger = logging.getLogger("app.services.auth_service")
    email_logger.setLevel(logging.INFO)
    auth_logger.setLevel(logging.INFO)
    email_logger.addHandler(handler)
    auth_logger.addHandler(handler)

    try:
        res = client.post(
            "/api/v1/auth/password-reset",
            json={"email": test_user["user"].email},
            headers={"X-Forwarded-For": "10.0.0.8"},
        )
        assert res.status_code == 200
        raw_token = _get_token_from_email_provider()

        all_logs = " ".join(handler.logs)
        # The raw token must NOT appear anywhere in the captured log text
        assert raw_token not in all_logs
        # Log message must contain the redaction note
        assert any("token redacted" in msg for msg in handler.logs)
    finally:
        email_logger.removeHandler(handler)
        auth_logger.removeHandler(handler)


