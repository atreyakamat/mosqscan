"""Storage service for media files."""
from __future__ import annotations

import hashlib
import logging
import os
import re
import uuid
from pathlib import Path

import aiofiles

from app.config import settings

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal and other exploits.
    Strips directory components and replaces dangerous characters.
    """
    # Replace null bytes
    filename = filename.replace("\x00", "_")
    # Normalize backslashes to forward slashes before basename
    filename = filename.replace("\\", "/")
    # Take only the basename (strip any directory traversal)
    filename = os.path.basename(filename)
    # Allow only safe characters
    filename = re.sub(r"[^\w.\-]", "_", filename)
    # Strip leading dots to prevent hidden files
    filename = filename.lstrip(".")
    return filename or "upload"


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def save_media_file(
    data: bytes,
    original_filename: str,
    sub_folder: str = "images",
) -> dict:
    """
    Save uploaded bytes to storage. Returns metadata dict.
    Never exposes the full file path in return value.
    """
    safe_name = sanitize_filename(original_filename)
    ext = Path(safe_name).suffix.lower()
    stored_name = f"{uuid.uuid4().hex}{ext}"

    storage_root = Path(settings.MEDIA_STORAGE_PATH) / sub_folder
    storage_root.mkdir(parents=True, exist_ok=True)
    file_path = storage_root / stored_name

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(data)

    checksum = compute_sha256(data)
    logger.info("Saved media file %s (%d bytes, sha256=%s)", stored_name, len(data), checksum)

    return {
        "original_filename": safe_name,
        "stored_filename": stored_name,
        "file_path": str(file_path),
        "file_size": len(data),
        "sha256_checksum": checksum,
    }
