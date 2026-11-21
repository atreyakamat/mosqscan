"""Custom exceptions for Vectora AI backend."""
from __future__ import annotations

from fastapi import HTTPException, status


class VectoraException(Exception):
    """Base exception for Vectora AI."""

    def __init__(self, error_code: str, message: str, status_code: int = 400):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        super().__init__(message)

    def to_dict(self) -> dict:
        return {
            "success": False,
            "error_code": self.error_code,
            "message": self.message,
        }


class AuthException(VectoraException):
    """Authentication related exceptions."""

    def __init__(self, error_code: str, message: str):
        super().__init__(error_code, message, status_code=401)


class ForbiddenException(VectoraException):
    """Authorization / ownership related exceptions."""

    def __init__(self, error_code: str = "FORBIDDEN", message: str = "Access denied"):
        super().__init__(error_code, message, status_code=403)


class NotFoundException(VectoraException):
    """Resource not found exceptions."""

    def __init__(self, resource: str = "Resource"):
        super().__init__("NOT_FOUND", f"{resource} not found", status_code=404)


class ValidationException(VectoraException):
    """Input validation exceptions."""

    def __init__(self, error_code: str, message: str):
        super().__init__(error_code, message, status_code=422)


class RateLimitException(VectoraException):
    """Rate limiting exceptions."""

    def __init__(self, message: str = "Too many requests"):
        super().__init__("RATE_LIMITED", message, status_code=429)


class MediaException(VectoraException):
    """Media/file related exceptions."""

    def __init__(self, error_code: str, message: str):
        super().__init__(error_code, message, status_code=422)


class VideoException(VectoraException):
    """Video-specific exceptions."""

    def __init__(self, error_code: str, message: str):
        super().__init__(error_code, message, status_code=422)


class InferenceException(VectoraException):
    """ML inference related exceptions."""

    def __init__(self, message: str):
        super().__init__("INFERENCE_ERROR", message, status_code=500)
