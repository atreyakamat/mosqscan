"""Adult specimen service — validation, storage, inference, persistence."""
from __future__ import annotations

import io
import logging
from typing import Optional, Tuple

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import MediaException
from app.db.models import IdentificationResult, MediaFile, Submission, SubmissionStatus, SubmissionType
from app.inference.adult_classifier import get_classifier
from app.services.storage_service import save_media_file

logger = logging.getLogger(__name__)

# Allowed magic bytes
_JPEG_MAGIC = b"\xff\xd8\xff"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _detect_mime(data: bytes) -> str:
    """Detect MIME type from magic bytes. Raises MediaException on unsupported type."""
    if data[:3] == _JPEG_MAGIC:
        return "image/jpeg"
    if data[:8] == _PNG_MAGIC:
        return "image/png"
    raise MediaException("INVALID_FILE_TYPE", "Only JPEG and PNG images are accepted")


def _validate_image_data(data: bytes, max_mb: int) -> Image.Image:
    """Full image validation and EXIF transpose. Returns opened PIL Image."""
    max_bytes = max_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise MediaException("FILE_TOO_LARGE", f"Image exceeds {max_mb}MB limit")

    _detect_mime(data)

    try:
        image = Image.open(io.BytesIO(data))
        image.verify()  # check for corruption
        image = Image.open(io.BytesIO(data))  # re-open after verify
        # Apply EXIF orientation before processing so dimensions and orientation match reality
        image = ImageOps.exif_transpose(image)
    except Image.DecompressionBombError:
        raise MediaException("DECOMPRESSION_BOMB", "Image exceeds maximum allowed pixel count")
    except UnidentifiedImageError:
        raise MediaException("CORRUPTED_IMAGE", "Image file is corrupted or unreadable")
    except Exception:
        raise MediaException("CORRUPTED_IMAGE", "Image file is corrupted or unreadable")

    w, h = image.size
    if w < 100 or h < 100:
        raise MediaException(
            "IMAGE_TOO_SMALL",
            f"Image dimensions {w}×{h} are below minimum 100×100",
        )
    MAX_DIMENSION = 8192
    if w > MAX_DIMENSION or h > MAX_DIMENSION:
        raise MediaException(
            "IMAGE_DIMENSIONS_EXCEEDED",
            f"Image dimensions {w}×{h} exceed maximum allowed {MAX_DIMENSION}×{MAX_DIMENSION}",
        )

    return image


def _evaluate_image_quality(image: Image.Image) -> dict:
    """Evaluate image quality metrics (blur, brightness)."""
    try:
        gray = np.array(image.convert("L"), dtype=np.float32)
        if gray.shape[0] > 4 and gray.shape[1] > 4:
            # Simple discrete Laplacian approximation
            laplacian = (
                np.roll(gray, 1, axis=0)
                + np.roll(gray, -1, axis=0)
                + np.roll(gray, 1, axis=1)
                + np.roll(gray, -1, axis=1)
                - 4.0 * gray
            )[1:-1, 1:-1]
            blur_variance = float(np.var(laplacian))
        else:
            blur_variance = 0.0

        mean_brightness = float(np.mean(gray))
        is_blurry = blur_variance < 30.0
        is_underexposed = mean_brightness < 35.0
        is_overexposed = mean_brightness > 225.0

        notes = []
        if is_blurry:
            notes.append("Potential image blur detected.")
        if is_underexposed:
            notes.append("Low lighting / underexposed.")
        if is_overexposed:
            notes.append("High glare / overexposed.")

        return {
            "blur_score": round(blur_variance, 2),
            "is_blurry": is_blurry,
            "brightness": round(mean_brightness, 2),
            "quality_feedback": " ".join(notes) if notes else "Specimen image quality acceptable.",
        }
    except Exception as exc:
        logger.warning("Quality check non-fatal error: %s", exc)
        return {
            "blur_score": 0.0,
            "is_blurry": False,
            "brightness": 128.0,
            "quality_feedback": "Quality check bypassed.",
        }


def _validate_and_apply_crop(
    image: Image.Image,
    crop_coords: Optional[Tuple[float, float, float, float]],
) -> Tuple[Image.Image, dict]:
    """
    Validate normalized crop coordinates (x, y, w, h) in range [0, 1].
    Apply crop to full resolution image before resizing to 224x224.
    Returns (cropped_pil_image, crop_metadata).
    """
    img_w, img_h = image.size
    if crop_coords is None:
        return image, {
            "crop_applied": False,
            "crop_mode": "full_image_fallback",
            "notes": "Full image used without manual specimen crop. Specimen framing advised.",
        }

    x, y, cw, ch = crop_coords
    if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
        raise MediaException("INVALID_CROP_COORDINATES", "Crop coordinates x and y must be in [0.0, 1.0]")
    if not (0.0 < cw <= 1.0 and 0.0 < ch <= 1.0):
        raise MediaException("INVALID_CROP_COORDINATES", "Crop dimensions width and height must be positive and <= 1.0")
    if (x + cw) > 1.05 or (y + ch) > 1.05:
        raise MediaException("INVALID_CROP_COORDINATES", "Crop bounding box extends beyond image boundaries")

    # Map normalized coordinates to pixel coordinates
    left = max(0, int(x * img_w))
    top = max(0, int(y * img_h))
    right = min(img_w, int((x + cw) * img_w))
    bottom = min(img_h, int((y + ch) * img_h))

    crop_w = right - left
    crop_h = bottom - top

    if crop_w < 20 or crop_h < 20:
        raise MediaException(
            "CROP_TOO_SMALL",
            f"Cropped region ({crop_w}x{crop_h}) is below minimum 20x20 pixels",
        )

    cropped = image.crop((left, top, right, bottom))
    return cropped, {
        "crop_applied": True,
        "crop_mode": "manual_specimen_crop",
        "crop_box_normalized": {"x": round(x, 4), "y": round(y, 4), "w": round(cw, 4), "h": round(ch, 4)},
        "crop_box_pixels": {"left": left, "top": top, "right": right, "bottom": bottom, "w": crop_w, "h": crop_h},
        "original_dimensions": [img_w, img_h],
        "notes": "Specimen region extracted prior to model preprocessing.",
    }


async def process_adult_submission(
    db: Session,
    user_id: str,
    file_data: bytes,
    original_filename: str,
    crop_coords: Optional[Tuple[float, float, float, float]] = None,
) -> Submission:
    """
    Validate image, apply specimen crop to full-resolution image, run inference,
    persist artifacts, and return the Submission.
    """
    image = _validate_image_data(file_data, settings.MAX_IMAGE_SIZE_MB)
    mime = _detect_mime(file_data)

    # 1. Evaluate image quality on original image
    quality_metrics = _evaluate_image_quality(image)

    # 2. Apply manual crop to unscaled image prior to model input
    cropped_image, crop_meta = _validate_and_apply_crop(image, crop_coords)

    # 3. Create submission record
    submission = Submission(
        user_id=user_id,
        type=SubmissionType.adult,
        status=SubmissionStatus.processing,
    )
    db.add(submission)
    db.flush()

    # 4. Save original photograph (preserved for audit)
    meta = await save_media_file(file_data, original_filename, sub_folder="images")
    media = MediaFile(
        submission_id=submission.id,
        mime_type=mime,
        **meta,
    )
    db.add(media)
    db.flush()

    # 5. If cropped, save the crop as a separate processing artifact
    if crop_meta.get("crop_applied"):
        crop_buf = io.BytesIO()
        cropped_image.convert("RGB").save(crop_buf, format="JPEG", quality=95)
        crop_bytes = crop_buf.getvalue()
        crop_filename = f"crop_{submission.id}.jpg"
        crop_meta_saved = await save_media_file(crop_bytes, crop_filename, sub_folder="crops")
        crop_media = MediaFile(
            submission_id=submission.id,
            mime_type="image/jpeg",
            **crop_meta_saved,
        )
        db.add(crop_media)
        db.flush()

    # 6. Run model inference off the event loop using the cropped image
    try:
        classifier = get_classifier()
        result_data = await classifier.predict_async(cropped_image)
    except Exception:
        logger.exception("Inference failed for submission %s", submission.id)
        submission.status = SubmissionStatus.failed
        db.commit()
        raise

    # 7. Merge quality feedback and crop metadata
    combined_feedback = {
        **quality_metrics,
        **crop_meta,
        "scientific_disclaimer": "Visual identification only. Research pilot model. Not field-validated.",
    }

    # 8. Persist identification result
    result = IdentificationResult(
        submission_id=submission.id,
        predicted_genus=result_data["predicted_genus"],
        confidence=result_data["confidence"],
        model_version=result_data["model_version"],
        model_artifact=result_data["model_artifact"],
        processing_time_ms=result_data["processing_time_ms"],
        is_uncertain=result_data["is_uncertain"],
        uncertainty_message=result_data["uncertainty_message"],
        all_scores=result_data["all_scores"],
    )
    db.add(result)
    submission.status = SubmissionStatus.completed
    db.commit()
    db.refresh(submission)

    # Attach dynamic feedback for response serialization
    submission._quality_feedback = combined_feedback
    return submission


def get_submission(db: Session, submission_id: str, user_id: str) -> Submission:
    """Get a submission, ensuring ownership."""
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        from app.core.exceptions import NotFoundException

        raise NotFoundException("Submission")
    if sub.user_id != user_id:
        from app.core.exceptions import ForbiddenException

        raise ForbiddenException()
    return sub


def list_submissions(
    db: Session, user_id: str, page: int = 1, page_size: int = 20
) -> tuple[list[Submission], int]:
    """Return paginated list of adult submissions for a user."""
    query = (
        db.query(Submission)
        .filter(
            Submission.user_id == user_id,
            Submission.type == SubmissionType.adult,
        )
        .order_by(Submission.created_at.desc())
    )
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total
