"""Pydantic schemas for larvae video submissions."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class LarvaeJobResponse(BaseModel):
    job_id: str
    submission_id: str
    status: str
    message: str = "Video queued for processing"


class LarvaeJobStatusResponse(BaseModel):
    job_id: str
    submission_id: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    frame_count: int | None
    valid_frames: int | None


class LarvaeResultResponse(BaseModel):
    submission_id: str
    status: str
    model_status: str = "model_not_validated"
    message: str = (
        "Larvae identification model is not yet field-validated and "
        "must not be used for production predictions."
    )
    result: None = None
