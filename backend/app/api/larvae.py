"""Larvae video API routes."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import ForbiddenException, NotFoundException, VideoException
from app.db.models import User
from app.db.session import get_db
from app.dependencies import get_current_user
from app.services import larvae_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/larvae", tags=["larvae"])


def _error(status_code: int, error_code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "error_code": error_code, "message": message},
    )


@router.post("/submit", status_code=202)
async def submit_larvae(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a larvae video (3-5 seconds).
    Duration is validated by decoded media timestamps (not client metadata).
    Returns job_id immediately — processing is asynchronous.
    """
    max_bytes = settings.MAX_VIDEO_SIZE_MB * 1024 * 1024
    file_data = await file.read()
    if len(file_data) > max_bytes:
        return _error(422, "FILE_TOO_LARGE", f"Video exceeds {settings.MAX_VIDEO_SIZE_MB}MB limit")

    try:
        submission, job = await larvae_service.process_larvae_submission(
            db, current_user.id, file_data, file.filename or "video.mp4"
        )
    except VideoException as exc:
        return _error(exc.status_code, exc.error_code, exc.message)
    except Exception:
        logger.exception("Unexpected error processing larvae submission")
        return _error(500, "INTERNAL_ERROR", "An unexpected error occurred")

    return {
        "job_id": job.id,
        "submission_id": submission.id,
        "status": job.status,
        "message": "Video queued for processing",
    }


@router.get("/jobs/{job_id}")
def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the status of a larvae processing job. Owner only."""
    try:
        job = larvae_service.get_job(db, job_id, current_user.id)
    except (NotFoundException, ForbiddenException) as exc:
        return _error(exc.status_code, exc.error_code, exc.message)

    return {
        "job_id": job.id,
        "submission_id": job.submission_id,
        "status": job.status,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "error_message": job.error_message,
        "frame_count": job.frame_count,
        "valid_frames": job.valid_frames,
    }


@router.get("/submissions")
def list_larvae_submissions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the current user's larvae submissions (paginated)."""
    items, total = larvae_service.list_larvae_submissions(db, current_user.id, page, page_size)
    return {
        "items": [{"id": s.id, "status": s.status, "created_at": s.created_at} for s in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/submissions/{submission_id}")
def get_larvae_submission(
    submission_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a larvae submission result.
    Always returns model_not_validated status — larvae model is not field-validated.
    """
    try:
        sub = larvae_service.get_larvae_submission(db, submission_id, current_user.id)
    except (NotFoundException, ForbiddenException) as exc:
        return _error(exc.status_code, exc.error_code, exc.message)

    return {
        "submission_id": sub.id,
        "status": sub.status,
        "model_status": "model_not_validated",
        "message": (
            "Larvae identification model is not yet field-validated and "
            "must not be used for production predictions."
        ),
        "result": None,
    }
