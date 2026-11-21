"""Authentication service."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import AuthException, ValidationException
from app.core.security import (
    clear_login_rate_limit,
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
    check_login_rate_limit,
)
from app.db.models import RefreshToken, User, UserRole

logger = logging.getLogger(__name__)


def register_user(db: Session, email: str, username: str, password: str) -> User:
    """Create a new user. Raises ValidationException on duplicate."""
    if db.query(User).filter(User.email == email).first():
        raise ValidationException("EMAIL_TAKEN", "Email is already registered")
    if db.query(User).filter(User.username == username).first():
        raise ValidationException("USERNAME_TAKEN", "Username is already taken")

    user = User(
        email=email,
        username=username,
        hashed_password=hash_password(password),
        role=UserRole.user,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("New user registered: %s", email)
    return user


def login_user(
    db: Session, email: str, password: str, ip: str
) -> tuple[str, str, datetime]:
    """
    Authenticate a user. Returns (access_token, refresh_token, refresh_expires_at).
    Applies rate limiting per IP. Raises AuthException on failure.
    """
    check_login_rate_limit(ip)

    user = db.query(User).filter(User.email == email, User.is_active == True).first()
    if not user or not verify_password(password, user.hashed_password):
        raise AuthException("INVALID_CREDENTIALS", "Invalid email or password")

    clear_login_rate_limit(ip)

    access_token = create_access_token({"sub": user.id})
    refresh_token_str, expires_at = create_refresh_token({"sub": user.id})

    token_hash = hash_token(refresh_token_str)
    rt = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(rt)
    db.commit()

    logger.info("User logged in: %s", email)
    return access_token, refresh_token_str, expires_at


def refresh_tokens(
    db: Session, refresh_token_str: str
) -> tuple[str, str, datetime]:
    """
    Rotate refresh token. Returns new (access_token, refresh_token, expires_at).
    Revokes old token. Raises AuthException if invalid/expired/revoked.
    """
    from jose import JWTError
    from app.core.security import decode_token

    try:
        payload = decode_token(refresh_token_str)
        if payload.get("type") != "refresh":
            raise AuthException("INVALID_TOKEN", "Invalid token type")
        user_id = payload.get("sub")
    except JWTError:
        raise AuthException("INVALID_TOKEN", "Invalid or expired refresh token")

    token_hash = hash_token(refresh_token_str)
    rt = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

    if not rt:
        raise AuthException("INVALID_TOKEN", "Refresh token not found")
    if rt.revoked:
        # Potential token reuse — revoke all tokens for this user
        db.query(RefreshToken).filter(RefreshToken.user_id == user_id).update({"revoked": True})
        db.commit()
        raise AuthException("TOKEN_REUSE", "Refresh token already used")
    if rt.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise AuthException("TOKEN_EXPIRED", "Refresh token has expired")

    # Revoke old token
    rt.revoked = True
    db.flush()

    # Issue new tokens
    access_token = create_access_token({"sub": user_id})
    new_refresh_str, expires_at = create_refresh_token({"sub": user_id})
    new_rt = RefreshToken(
        user_id=user_id,
        token_hash=hash_token(new_refresh_str),
        expires_at=expires_at,
    )
    db.add(new_rt)
    db.commit()

    return access_token, new_refresh_str, expires_at


def logout_user(db: Session, refresh_token_str: str) -> None:
    """Revoke a refresh token."""
    token_hash = hash_token(refresh_token_str)
    rt = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if rt:
        rt.revoked = True
        db.commit()


def request_password_reset(db: Session, email: str, ip: str) -> None:
    """
    Initiate a secure password reset.
    Rate-limited, generates cryptographic token, stores only SHA-256 hash,
    dispatches via configurable email provider without logging token.
    Generic return to prevent account enumeration.
    """
    import secrets
    from datetime import timedelta
    from app.config import settings
    from app.core.rate_limit import check_password_reset_rate_limit
    from app.db.models import PasswordResetToken
    from app.services.email_service import get_email_provider

    check_password_reset_rate_limit(ip)

    user = db.query(User).filter(User.email == email, User.is_active == True).first()
    if not user:
        # Prevent user enumeration: do not indicate failure if user not found
        logger.info("Password reset requested for unregistered/inactive email (generic response)")
        return

    # Invalidate previous unused reset tokens for this user
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used == False,
    ).update({"used": True})

    # Generate secure random token (32 bytes = 256 bits entropy)
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
    )

    reset_record = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        used=False,
    )
    db.add(reset_record)
    db.commit()

    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={raw_token}"
    email_provider = get_email_provider()
    email_provider.send_password_reset_email(user.email, reset_link)

    # Note: Sensitive token is strictly omitted from logging
    logger.info("Password reset token generated and dispatched for user id=%s", user.id)


def confirm_password_reset(
    db: Session, token: str, new_password: str, ip: str
) -> None:
    """
    Confirm password reset with raw token and new password.
    Enforces rate limits, validates single use, verifies expiration,
    updates password hash, invalidates all existing sessions (refresh tokens),
    and revokes all active reset tokens.
    """
    from app.core.rate_limit import check_password_reset_confirm_rate_limit
    from app.db.models import PasswordResetToken

    check_password_reset_confirm_rate_limit(ip)

    if len(new_password) < 8:
        raise ValidationException("WEAK_PASSWORD", "Password must be at least 8 characters")

    token_hash = hash_token(token)
    reset_record = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == token_hash)
        .first()
    )

    if not reset_record:
        raise ValidationException(
            "INVALID_OR_EXPIRED_TOKEN", "Invalid or expired reset token"
        )

    if reset_record.used:
        raise ValidationException(
            "TOKEN_ALREADY_USED", "Reset token has already been used"
        )

    expires_at = (
        reset_record.expires_at
        if reset_record.expires_at.tzinfo
        else reset_record.expires_at.replace(tzinfo=timezone.utc)
    )
    if expires_at < datetime.now(timezone.utc):
        raise ValidationException(
            "TOKEN_EXPIRED", "Reset token has expired"
        )

    user = db.query(User).filter(User.id == reset_record.user_id).first()
    if not user or not user.is_active:
        raise ValidationException(
            "USER_INACTIVE", "User account is not found or inactive"
        )

    # Update user password
    user.hashed_password = hash_password(new_password)

    # Mark token as used (single use enforcement)
    reset_record.used = True

    # Invalidate all prior sessions (refresh tokens) for security
    db.query(RefreshToken).filter(RefreshToken.user_id == user.id).update(
        {"revoked": True}
    )

    # Invalidate any other active reset tokens for this user
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.id != reset_record.id,
    ).update({"used": True})

    db.commit()
    logger.info("Password reset successfully completed for user id=%s", user.id)

