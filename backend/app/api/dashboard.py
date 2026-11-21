"""User dashboard API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models import IdentificationResult, Submission, SubmissionStatus, SubmissionType, User
from app.db.session import get_db
from app.dependencies import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
def get_user_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return summary statistics for the authenticated user only.
    Never display statistics from other users.
    """
    user_id = current_user.id

    total = db.query(Submission).filter(Submission.user_id == user_id).count()
    adult_count = (
        db.query(Submission)
        .filter(Submission.user_id == user_id, Submission.type == SubmissionType.adult)
        .count()
    )
    larvae_count = (
        db.query(Submission)
        .filter(Submission.user_id == user_id, Submission.type == SubmissionType.larvae)
        .count()
    )
    failed_count = (
        db.query(Submission)
        .filter(Submission.user_id == user_id, Submission.status == SubmissionStatus.failed)
        .count()
    )

    # Identifications
    results = (
        db.query(IdentificationResult)
        .join(Submission, IdentificationResult.submission_id == Submission.id)
        .filter(Submission.user_id == user_id)
        .all()
    )

    uncertain_count = sum(1 for r in results if r.is_uncertain)
    successful_count = sum(
        1 for r in results if not r.is_uncertain and r.predicted_genus is not None
    )

    # Recent submissions
    recent_subs = (
        db.query(Submission)
        .filter(Submission.user_id == user_id)
        .order_by(Submission.created_at.desc())
        .limit(10)
        .all()
    )

    recent_activity = []
    for s in recent_subs:
        genus = None
        confidence = None
        is_uncertain = False
        if s.identification_result:
            genus = s.identification_result.predicted_genus
            confidence = s.identification_result.confidence
            is_uncertain = s.identification_result.is_uncertain

        recent_activity.append({
            "id": s.id,
            "type": s.type,
            "status": s.status,
            "predicted_genus": genus,
            "confidence": confidence,
            "is_uncertain": is_uncertain,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        })

    return {
        "total_submissions": total,
        "adult_submissions": adult_count,
        "larvae_submissions": larvae_count,
        "successful_identifications": successful_count,
        "uncertain_identifications": uncertain_count,
        "failed_submissions": failed_count,
        "recent_activity": recent_activity,
    }
