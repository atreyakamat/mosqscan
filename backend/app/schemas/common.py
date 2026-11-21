"""Common Pydantic schemas and error response models."""
from __future__ import annotations

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str | None = None
