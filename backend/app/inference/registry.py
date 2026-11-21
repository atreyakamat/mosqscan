"""Model registry — loads manifest.json and provides model metadata."""
from __future__ import annotations

import json
import logging
import os
from functools import lru_cache

from app.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def load_manifest() -> dict:
    """Load and cache the model registry manifest."""
    path = settings.MODEL_MANIFEST_PATH
    if not os.path.exists(path):
        logger.warning("Manifest not found at %s, using defaults", path)
        return {}
    with open(path) as f:
        return json.load(f)


def get_adult_classifier_info() -> dict:
    """Return adult classifier metadata from the manifest."""
    manifest = load_manifest()
    return manifest.get("adult_classifier", {})


def get_model_version() -> str:
    """Return the current model version string."""
    manifest = load_manifest()
    return manifest.get("model_version", "unknown")


def get_larvae_model_info() -> dict:
    """Return larvae model info (always not_validated)."""
    manifest = load_manifest()
    return manifest.get("larvae_model", {"status": "not_validated"})
