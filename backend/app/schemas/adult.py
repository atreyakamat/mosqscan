"""Pydantic schemas for adult specimen submissions."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class IdentificationResultSchema(BaseModel):
    scan_id: str | None = None
    predicted_genus: str | None
    confidence: float | None
    raw_score: float | None = None
    raw_class_scores: dict[str, float] | None = None
    is_uncertain: bool
    uncertainty_message: str | None = None
    all_scores: dict[str, float] | None = None
    model_version: str
    model_status: str | None = "EXPERIMENTAL_NOT_FIELD_VALIDATED"
    evaluation_status: str | None = "EXPERIMENTAL_NOT_FIELD_VALIDATED"
    model_artifact: str
    model_checksum: str | None = None
    processing_time_ms: int
    inference_latency: str | None = None
    inference_latency_ms: int | None = None
    processing_timestamp: str | None = None
    review_recommendation: str | None = None
    quality_feedback: dict | None = None
    scientific_disclaimer: str | None = None

    model_config = {"from_attributes": True}


class SubmissionResponse(BaseModel):
    id: str
    scan_id: str | None = None
    status: str
    type: str
    created_at: datetime
    result: IdentificationResultSchema | None = None

    model_config = {"from_attributes": True}


class SubmissionListResponse(BaseModel):
    items: list[SubmissionResponse]
    total: int
    page: int
    page_size: int
