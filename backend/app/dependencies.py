"""FastAPI shared dependencies."""
from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import AuthException, ForbiddenException
from app.core.security import decode_token
from app.db.models import User, UserRole
from app.db.session import get_db


def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
) -> User:
    """Extract and validate the JWT from the Authorization header."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error_code": "UNAUTHORIZED", "message": "Not authenticated"},
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not authorization or not authorization.startswith("Bearer "):
        raise credentials_exception
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_exception
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if user is None:
        raise credentials_exception
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that requires the authenticated user to have the admin role."""
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_code": "FORBIDDEN", "message": "Admin access required"},
        )
    return current_user
