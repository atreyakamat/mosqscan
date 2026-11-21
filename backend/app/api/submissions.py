"""Unified submissions and history API routes."""
from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenException, NotFoundException
from app.db.models import IdentificationResult, MediaFile, Submission, SubmissionStatus, SubmissionType, User
from app.db.session import get_db
from app.dependencies import get_current_user

router = APIRouter(prefix="/submissions", tags=["submissions"])


def _error(status_code: int, error_code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "error_code": error_code, "message": message},
    )


def _format_submission(sub: Submission) -> dict:
    result = None
    if sub.identification_result:
        r = sub.identification_result
        result = {
            "predicted_genus": r.predicted_genus,
            "confidence": r.confidence,
            "is_uncertain": r.is_uncertain,
            "uncertainty_message": r.uncertainty_message,
            "all_scores": r.all_scores,
            "model_version": r.model_version,
            "model_artifact": r.model_artifact,
            "processing_time_ms": r.processing_time_ms,
        }

    job_info = None
    if sub.processing_job:
        j = sub.processing_job
        job_info = {
            "job_id": j.id,
            "status": j.status,
            "frame_count": j.frame_count,
            "valid_frames": j.valid_frames,
            "error_message": j.error_message,
        }

    media_info = []
    for m in sub.media_files:
        media_info.append({
            "id": m.id,
            "filename": m.original_filename,
            "mime_type": m.mime_type,
            "file_size": m.file_size,
            "sha256": m.sha256_checksum,
        })

    return {
        "id": sub.id,
        "type": sub.type,
        "status": sub.status,
        "created_at": sub.created_at.isoformat() if sub.created_at else None,
        "updated_at": sub.updated_at.isoformat() if sub.updated_at else None,
        "result": result,
        "job": job_info,
        "media": media_info,
    }


@router.get("")
def list_all_submissions(
    type: Optional[str] = Query(None, description="Filter by type: adult or larvae"),
    status: Optional[str] = Query(None, description="Filter by status"),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List authenticated user's submissions with filtering and pagination."""
    query = db.query(Submission).filter(Submission.user_id == current_user.id)

    if type:
        query = query.filter(Submission.type == type)
    if status:
        query = query.filter(Submission.status == status)
    if date_from:
        query = query.filter(Submission.created_at >= date_from)
    if date_to:
        query = query.filter(Submission.created_at <= date_to)
    if search:
        search_pattern = f"%{search}%"
        query = (
            query.outerjoin(Submission.identification_result)
            .outerjoin(Submission.media_files)
            .filter(
                or_(
                    Submission.id.ilike(search_pattern),
                    IdentificationResult.predicted_genus.ilike(search_pattern),
                    MediaFile.original_filename.ilike(search_pattern),
                )
            )
            .distinct()
        )

    total = query.count()
    items = (
        query.order_by(Submission.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": [_format_submission(s) for s in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{submission_id}")
def get_submission_detail(
    submission_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve full submission details. Strictly enforces user ownership."""
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        return _error(404, "NOT_FOUND", "Submission not found")
    if sub.user_id != current_user.id:
        return _error(403, "FORBIDDEN", "You do not have access to this submission")

    return _format_submission(sub)


@router.delete("/{submission_id}")
def delete_submission(
    submission_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a submission and its associated media. Strictly enforces user ownership."""
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        return _error(404, "NOT_FOUND", "Submission not found")
    if sub.user_id != current_user.id:
        return _error(403, "FORBIDDEN", "You do not have access to this submission")

    # Clean up media files on disk
    for media in sub.media_files:
        if os.path.exists(media.file_path):
            try:
                os.unlink(media.file_path)
            except OSError:
                pass

    db.delete(sub)
    db.commit()
    return {"success": True, "message": "Submission deleted successfully"}
