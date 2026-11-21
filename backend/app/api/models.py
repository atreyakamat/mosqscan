"""Model registry and management API routes."""
from __future__ import annotations

import hashlib
import os
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import settings
from app.inference.registry import get_adult_classifier_info, get_larvae_model_info, get_model_version, load_manifest

router = APIRouter(prefix="/models", tags=["models"])


@router.get("")
@router.get("/info")
@router.get("/manifest")
def get_model_info():
    """Return approved model registry metadata."""
    manifest = load_manifest()
    return {
        "product": manifest.get("product", "Vectora AI"),
        "model_version": get_model_version(),
        "created_at": manifest.get("created_at"),
        "adult_classifier": get_adult_classifier_info(),
        "larvae_model": get_larvae_model_info(),
    }


@router.get("/version")
def get_version():
    """Return current model version."""
    return {"model_version": get_model_version()}


@router.get("/health")
def get_model_health():
    """Verify approved model artifact presence and checksum integrity."""
    model_path = os.path.join(settings.MODEL_REGISTRY_PATH, settings.ADULT_MODEL_ARTIFACT)
    if not os.path.exists(model_path):
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "error": f"Model artifact not found at {model_path}",
                "model_version": get_model_version(),
            },
        )

    # Checksum verification against manifest
    manifest = load_manifest()
    artifacts = (
        manifest.get("adult_classifier", {})
        .get("artifacts", {})
    )
    expected_sha = None
    for art in artifacts.values():
        if isinstance(art, dict) and art.get("file") == settings.ADULT_MODEL_ARTIFACT:
            expected_sha = art.get("sha256")
            break

    if expected_sha is None:
        expected_sha = artifacts.get("fp32_onnx", {}).get("sha256")

    with open(model_path, "rb") as f:
        actual_sha = hashlib.sha256(f.read()).hexdigest()

    checksum_ok = (expected_sha is None) or (actual_sha == expected_sha)

    return {
        "status": "healthy" if checksum_ok else "degraded",
        "model_version": get_model_version(),
        "artifact": settings.ADULT_MODEL_ARTIFACT,
        "checksum_verified": checksum_ok,
        "actual_sha256": actual_sha,
    }
