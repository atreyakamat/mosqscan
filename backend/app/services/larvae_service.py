"""Larvae submission service."""
from __future__ import annotations

import logging
import os
import tempfile
import threading

import cv2

from app.config import settings
from app.core.exceptions import VideoException
from app.db.models import MediaFile, ProcessingJob, Submission, SubmissionStatus, SubmissionType
from app.services.storage_service import save_media_file
from app.workers.video_processor import process_larvae_video_job

logger = logging.getLogger(__name__)


def validate_video_duration(file_path: str) -> tuple[float, str | None]:
    """
    Validate video duration by decoding actual media timestamps.
    Handles both constant-frame-rate (CFR) and variable-frame-rate (VFR) videos.
    Never trust client-provided duration.

    Returns:
        (duration_seconds, error_code_or_None)

    Error codes:
        - "VIDEO_CORRUPTED": file is unreadable or not a valid video
        - "VIDEO_INVALID_DURATION": duration cannot be determined
        - "VIDEO_TOO_SHORT": duration < 3.0s
        - "VIDEO_TOO_LONG": duration > 5.0s
        - None: duration is 3.0 ≤ d ≤ 5.0 (valid)
    """
    # 1. Verify OpenCV can open and decode frames (catches corrupted/truncated media)
    try:
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return 0.0, "VIDEO_CORRUPTED"

        ret, frame = cap.read()
        if not ret or frame is None:
            cap.release()
            return 0.0, "VIDEO_CORRUPTED"

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        cap.release()
    except Exception:
        logger.exception("Error reading video file %s", file_path)
        return 0.0, "VIDEO_CORRUPTED"

    # 2. Extract presentation timestamp duration (handles VFR videos correctly)
    duration = None
    try:
        import subprocess
        res = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path,
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode == 0 and res.stdout.strip():
            parsed_dur = float(res.stdout.strip())
            if parsed_dur > 0:
                duration = parsed_dur
    except Exception:
        pass

    # Fallback to OpenCV frame_count / fps if ffprobe is unavailable
    if duration is None:
        if fps <= 0 or frame_count <= 0:
            return 0.0, "VIDEO_INVALID_DURATION"
        duration = frame_count / fps

    rounded_duration = round(duration, 2)
    if rounded_duration < 3.0:
        return duration, "VIDEO_TOO_SHORT"
    if rounded_duration > 5.0:
        return duration, "VIDEO_TOO_LONG"
    return duration, None


async def process_larvae_submission(
    db,
    user_id: str,
    file_data: bytes,
    original_filename: str,
    run_async_worker: bool = True,
) -> tuple[Submission, ProcessingJob]:
    """
    Validate video, save, create ProcessingJob. Returns (submission, job).
    Video duration is validated by decoding with OpenCV (not client metadata).
    """
    # Write to temp file for duration validation
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp.write(file_data)
        tmp_path = tmp.name

    try:
        duration, error_code = validate_video_duration(tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    if error_code == "VIDEO_CORRUPTED":
        raise VideoException("VIDEO_CORRUPTED", "Video file is corrupted or unreadable")
    if error_code == "VIDEO_INVALID_DURATION":
        raise VideoException("VIDEO_INVALID_DURATION", "Cannot determine video duration")
    if error_code == "VIDEO_TOO_SHORT":
        raise VideoException(
            "VIDEO_TOO_SHORT",
            "The video must be at least 3 seconds.",
        )
    if error_code == "VIDEO_TOO_LONG":
        raise VideoException(
            "VIDEO_TOO_LONG",
            "The video must not exceed 5 seconds.",
        )

    # Create submission
    submission = Submission(
        user_id=user_id,
        type=SubmissionType.larvae,
        status=SubmissionStatus.pending,
    )
    db.add(submission)
    db.flush()

    # Save file
    meta = await save_media_file(file_data, original_filename, sub_folder="videos")
    media = MediaFile(
        submission_id=submission.id,
        mime_type="video/mp4",
        **meta,
    )
    db.add(media)
    db.flush()

    # Create processing job
    job = ProcessingJob(
        submission_id=submission.id,
        status="queued",
    )
    db.add(job)
    db.commit()
    db.refresh(submission)
    db.refresh(job)

    # Trigger async video processing
    if run_async_worker:
        dispatched_celery = False
        if settings.ENVIRONMENT == "production":
            try:
                from app.workers.video_processor import celery_process_larvae_video
                if celery_process_larvae_video:
                    celery_process_larvae_video.delay(job.id)
                    dispatched_celery = True
            except Exception as err:
                logger.warning("Celery dispatch failed, falling back to thread: %s", err)
        if not dispatched_celery:
            worker_thread = threading.Thread(
                target=process_larvae_video_job,
                args=(job.id,),
                daemon=True,
            )
            worker_thread.start()

    return submission, job


def get_job(db, job_id: str, user_id: str) -> ProcessingJob:
    """Get a processing job ensuring ownership via submission."""
    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    if not job:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("Job")
    sub = db.query(Submission).filter(Submission.id == job.submission_id).first()
    if not sub or sub.user_id != user_id:
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException()
    return job


def get_larvae_submission(db, submission_id: str, user_id: str) -> Submission:
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("Submission")
    if sub.user_id != user_id:
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException()
    return sub


def list_larvae_submissions(db, user_id: str, page: int = 1, page_size: int = 20):
    query = (
        db.query(Submission)
        .filter(Submission.user_id == user_id, Submission.type == SubmissionType.larvae)
        .order_by(Submission.created_at.desc())
    )
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total
