"""Auth API routes."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Cookie, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.exceptions import AuthException, ValidationException, RateLimitException
from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.auth import (
    GenericMessageResponse,
    LoginRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RegisterRequest,
    TokenResponse,
    UserProfile,
)
from app.services import auth_service
from app.db.models import User
from app.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/register", status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Create a new user account."""
    try:
        user = auth_service.register_user(
            db, payload.email, payload.username, payload.password
        )
    except ValidationException as exc:
        return _error(exc.status_code, exc.error_code, exc.message)
    return {"id": user.id, "email": user.email, "username": user.username}


@router.post("/login")
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    """Authenticate and return access token + HttpOnly refresh cookie."""
    ip = _client_ip(request)
    try:
        access_token, refresh_token, expires_at = auth_service.login_user(
            db, payload.email, payload.password, ip
        )
    except (AuthException, RateLimitException) as exc:
        return _error(exc.status_code, exc.error_code, exc.message)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=7 * 24 * 3600,
        path="/api/v1/auth",
    )
    return TokenResponse(access_token=access_token)


@router.post("/refresh")
def refresh(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: str | None = Cookie(default=None),
):
    """Rotate refresh token."""
    if not refresh_token:
        return _error(401, "MISSING_TOKEN", "No refresh token provided")
    try:
        access_token, new_refresh, expires_at = auth_service.refresh_tokens(db, refresh_token)
    except AuthException as exc:
        return _error(exc.status_code, exc.error_code, exc.message)

    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=7 * 24 * 3600,
        path="/api/v1/auth",
    )
    return TokenResponse(access_token=access_token)


@router.post("/logout")
def logout(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: str | None = Cookie(default=None),
):
    """Revoke refresh token and clear cookie."""
    if refresh_token:
        auth_service.logout_user(db, refresh_token)
    response.delete_cookie(key="refresh_token", path="/api/v1/auth")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserProfile)
def me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return current_user


@router.post("/password-reset", response_model=GenericMessageResponse)
def password_reset(
    payload: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Initiate password reset workflow.
    Validates rate limits, generates cryptographic token hash, dispatches email.
    Always returns generic message to prevent account enumeration.
    """
    ip = _client_ip(request)
    try:
        auth_service.request_password_reset(db, payload.email, ip)
    except RateLimitException as exc:
        return _error(exc.status_code, exc.error_code, exc.message)

    return GenericMessageResponse(
        message="If that email exists, a reset link has been sent."
    )


@router.post("/password-reset/confirm", response_model=GenericMessageResponse)
def password_reset_confirm(
    payload: PasswordResetConfirmRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Confirm password reset with cryptographic token and new password.
    Validates rate limits, enforces single-use and expiration, updates hash,
    and invalidates all existing sessions (refresh tokens).
    """
    ip = _client_ip(request)
    try:
        auth_service.confirm_password_reset(
            db, payload.token, payload.new_password, ip
        )
    except (ValidationException, RateLimitException) as exc:
        return _error(exc.status_code, exc.error_code, exc.message)

    return GenericMessageResponse(
        message="Password has been reset successfully."
    )



# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

from fastapi.responses import JSONResponse


def _error(status_code: int, error_code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "error_code": error_code, "message": message},
    )
