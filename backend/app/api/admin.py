"""Administrative API routes."""
from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import AuditEvent, User, UserRole
from app.db.session import get_db
from app.dependencies import require_admin
from app.inference.registry import get_model_version

router = APIRouter(prefix="/admin", tags=["admin"])


class UpdateRoleRequest(BaseModel):
    role: str


class UpdateStatusRequest(BaseModel):
    is_active: bool


@router.get("/users")
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all user accounts (admin only)."""
    query = db.query(User).order_by(User.created_at.desc())
    total = query.count()
    users = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [
            {
                "id": u.id,
                "email": u.email,
                "username": u.username,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.patch("/users/{user_id}/status")
def update_user_status(
    user_id: str,
    payload: UpdateStatusRequest,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Enable or disable a user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse(status_code=404, content={"success": False, "error_code": "NOT_FOUND", "message": "User not found"})

    user.is_active = payload.is_active
    db.commit()
    return {"success": True, "user_id": user.id, "is_active": user.is_active}


@router.patch("/users/{user_id}/role")
def update_user_role(
    user_id: str,
    payload: UpdateRoleRequest,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update user role (user or admin)."""
    if payload.role not in [r.value for r in UserRole]:
        return JSONResponse(
            status_code=422,
            content={"success": False, "error_code": "INVALID_ROLE", "message": f"Role must be one of: {[r.value for r in UserRole]}"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse(status_code=404, content={"success": False, "error_code": "NOT_FOUND", "message": "User not found"})

    user.role = UserRole(payload.role)
    db.commit()
    return {"success": True, "user_id": user.id, "role": user.role}


@router.get("/system")
def get_system_status(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get system health and storage status."""
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    storage_writable = os.access(os.path.dirname(settings.MEDIA_STORAGE_PATH) or "/tmp", os.W_OK)
    model_exists = os.path.exists(
        os.path.join(settings.MODEL_REGISTRY_PATH, settings.ADULT_MODEL_ARTIFACT)
    )

    return {
        "status": "healthy" if db_ok and model_exists else "degraded",
        "environment": settings.ENVIRONMENT,
        "database_connected": db_ok,
        "storage_writable": storage_writable,
        "model_file_present": model_exists,
        "model_version": get_model_version(),
    }


@router.get("/audit-events")
def list_audit_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List system audit log events."""
    query = db.query(AuditEvent).order_by(AuditEvent.created_at.desc())
    total = query.count()
    events = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [
            {
                "id": e.id,
                "user_id": e.user_id,
                "event_type": e.event_type,
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
                "ip_address": e.ip_address,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
