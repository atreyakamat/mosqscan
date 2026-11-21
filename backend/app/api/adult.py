"""Adult specimen API routes."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenException, MediaException, NotFoundException
from app.db.models import User
from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.adult import SubmissionListResponse, SubmissionResponse
from app.services import adult_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/adult", tags=["adult"])


def _error(status_code: int, error_code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "error_code": error_code, "message": message},
    )


import json
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

def _build_submission_response(sub) -> dict:
    result = None
    if sub.identification_result:
        r = sub.identification_result
        feedback = getattr(sub, "_quality_feedback", None)
        if not feedback:
            feedback = {
                "crop_applied": len(sub.media_files) > 1 if sub.media_files else False,
                "crop_mode": "manual_specimen_crop" if (sub.media_files and len(sub.media_files) > 1) else "full_image_fallback",
                "scientific_disclaimer": "Visual genus-level identification only. Research pilot model. Not field-validated.",
            }
        
        raw_score = r.confidence
        is_uncertain = r.is_uncertain or (raw_score is not None and raw_score < 0.65)
        review_rec = "MANUAL_ENTOMOLOGICAL_INSPECTION_REQUIRED" if is_uncertain else "CONFIRMATORY_INSPECTION_ADVISED"

        result = {
            "scan_id": sub.id,
            "predicted_genus": r.predicted_genus,
            "confidence": r.confidence,
            "raw_score": raw_score,
            "raw_class_scores": r.all_scores,
            "all_scores": r.all_scores,
            "is_uncertain": is_uncertain,
            "uncertainty_message": r.uncertainty_message or ("Low confidence prediction. Manual inspection advised." if is_uncertain else None),
            "model_version": r.model_version,
            "model_status": "EXPERIMENTAL_NOT_FIELD_VALIDATED",
            "evaluation_status": "EXPERIMENTAL_NOT_FIELD_VALIDATED",
            "model_artifact": r.model_artifact,
            "model_checksum": "c3a3656f746a1bb2e7ac428e44670d89cf51f0d0f923ad3aa15420e8a4592cfa",
            "processing_timestamp": sub.created_at.isoformat() if hasattr(sub.created_at, "isoformat") else str(sub.created_at),
            "inference_latency": f"{r.processing_time_ms} ms",
            "inference_latency_ms": r.processing_time_ms,
            "processing_time_ms": r.processing_time_ms,
            "review_recommendation": review_rec,
            "quality_feedback": feedback,
            "scientific_disclaimer": (
                "Visual genus-level identification only. Research pilot model. Not field-validated. "
                "Species-level identification and pathogen detection are not supported."
            ),
        }
    return {
        "id": sub.id,
        "scan_id": sub.id,
        "status": sub.status,
        "type": sub.type,
        "created_at": sub.created_at,
        "result": result,
    }


@router.post("/submit", status_code=201)
async def submit_adult(
    file: UploadFile = File(...),
    crop_x: Optional[float] = Form(None),
    crop_y: Optional[float] = Form(None),
    crop_w: Optional[float] = Form(None),
    crop_h: Optional[float] = Form(None),
    crop_box: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload an adult mosquito image for genus identification with optional manual crop."""
    file_data = await file.read()

    crop_coords = None
    if crop_x is not None and crop_y is not None and crop_w is not None and crop_h is not None:
        crop_coords = (crop_x, crop_y, crop_w, crop_h)
    elif crop_box:
        try:
            parsed = json.loads(crop_box)
            if isinstance(parsed, dict) and "x" in parsed:
                crop_coords = (float(parsed["x"]), float(parsed["y"]), float(parsed["w"]), float(parsed["h"]))
            elif isinstance(parsed, (list, tuple)) and len(parsed) == 4:
                crop_coords = (float(parsed[0]), float(parsed[1]), float(parsed[2]), float(parsed[3]))
        except Exception:
            try:
                parts = [float(p.strip()) for p in crop_box.split(",") if p.strip()]
                if len(parts) == 4:
                    crop_coords = (parts[0], parts[1], parts[2], parts[3])
            except Exception:
                return _error(422, "INVALID_CROP_COORDINATES", "Invalid crop coordinates format")

    try:
        submission = await adult_service.process_adult_submission(
            db,
            current_user.id,
            file_data,
            file.filename or "upload",
            crop_coords=crop_coords,
        )
    except MediaException as exc:
        return _error(exc.status_code, exc.error_code, exc.message)
    except Exception:
        logger.exception("Unexpected error processing adult submission")
        return _error(500, "INTERNAL_ERROR", "An unexpected error occurred")

    return _build_submission_response(submission)


@router.get("/submissions")
def list_submissions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the current user's adult submissions (paginated)."""
    items, total = adult_service.list_submissions(db, current_user.id, page, page_size)
    return {
        "items": [_build_submission_response(s) for s in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/submissions/{submission_id}")
def get_submission(
    submission_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single submission and its result. Owner only."""
    try:
        sub = adult_service.get_submission(db, submission_id, current_user.id)
    except NotFoundException as exc:
        return _error(exc.status_code, exc.error_code, exc.message)
    except ForbiddenException as exc:
        return _error(exc.status_code, exc.error_code, exc.message)
    return _build_submission_response(sub)


@router.get("/submissions/{submission_id}/image")
def get_submission_image(
    submission_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Serve the original uploaded image. Owner only."""
    try:
        sub = adult_service.get_submission(db, submission_id, current_user.id)
    except (NotFoundException, ForbiddenException) as exc:
        return _error(exc.status_code, exc.error_code, exc.message)

    if not sub.media_files:
        return _error(404, "NOT_FOUND", "Image not found")

    media = sub.media_files[0]
    import os
    if not os.path.exists(media.file_path):
        return _error(404, "NOT_FOUND", "Image file not found on disk")

    return FileResponse(media.file_path, media_type=media.mime_type)
