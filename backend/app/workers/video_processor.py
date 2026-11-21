"""Video processing service for mosquito larvae videos using OpenCV."""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.db.models import IdentificationResult, MediaFile, ProcessingJob, Submission, SubmissionStatus
from app.db.session import SessionLocal
from app.inference.registry import get_model_version

logger = logging.getLogger(__name__)

try:
    from celery import Celery
    from app.config import settings

    celery_app = Celery("vectora_workers", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
    celery_app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
    )

    @celery_app.task(name="process_larvae_video_task")
    def celery_process_larvae_video(job_id: str):
        process_larvae_video_job(job_id)

except Exception as _e:
    logger.warning("Celery could not be initialized: %s", _e)
    celery_app = None
    celery_process_larvae_video = None


def analyze_larvae_video(video_path: str) -> dict:
    """
    Decodes video, evaluates frames, detects meniscus and larvae movement.

    Returns:
        dict with frame_count, valid_frames, meniscus_detected,
        motion_detected, avg_orientation_deg, blur_scores.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video: {video_path}")

    frame_count = 0
    valid_frames = 0
    meniscus_detected = False
    motion_detected = False
    orientations: list[float] = []

    prev_gray: np.ndarray | None = None
    blur_scores: list[float] = []

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            frame_count += 1
            h, w = frame.shape[:2]
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Frame quality evaluation
            # 1. Brightness check (avoid completely dark or overexposed frames)
            brightness = float(np.mean(gray))
            # 2. Blur evaluation using Laplacian variance
            lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            blur_scores.append(lap_var)

            # Valid if brightness is reasonable (10 to 245) and not totally blank
            is_valid_frame = 10.0 <= brightness <= 245.0 and lap_var > 5.0
            if is_valid_frame:
                valid_frames += 1

            # Meniscus detection (upper 35% of frame, horizontal edges)
            if not meniscus_detected and h > 50:
                top_region = gray[: int(h * 0.35), :]
                edges = cv2.Canny(top_region, 50, 150)
                lines = cv2.HoughLinesP(
                    edges,
                    rho=1,
                    theta=np.pi / 180,
                    threshold=50,
                    minLineLength=int(w * 0.25),
                    maxLineGap=20,
                )
                if lines is not None and len(lines) > 0:
                    for line in lines:
                        x1, y1, x2, y2 = line[0]
                        # Check if near horizontal (slope angle < 15 degrees)
                        dx = abs(x2 - x1)
                        dy = abs(y2 - y1)
                        if dx > 0 and (dy / dx) < 0.27:
                            meniscus_detected = True
                            break

            # Motion filtering & larvae region detection via frame differencing
            if prev_gray is not None:
                diff = cv2.absdiff(prev_gray, gray)
                _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
                # Morphological noise removal
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
                thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for cnt in contours:
                    area = cv2.contourArea(cnt)
                    # Filter for larvae-sized moving regions (typical 30 - 5000 pixels)
                    if 30 <= area <= 5000:
                        motion_detected = True
                        if len(cnt) >= 5:
                            ellipse = cv2.fitEllipse(cnt)
                            orientations.append(ellipse[2])  # angle in degrees

            prev_gray = gray
    finally:
        cap.release()

    avg_orientation = float(np.mean(orientations)) if orientations else None

    return {
        "frame_count": frame_count,
        "valid_frames": valid_frames,
        "meniscus_detected": meniscus_detected,
        "motion_detected": motion_detected,
        "avg_orientation_deg": avg_orientation,
        "mean_blur_score": float(np.mean(blur_scores)) if blur_scores else 0.0,
    }


def process_larvae_video_job(job_id: str, db: Session | None = None) -> None:
    """
    Process a larvae video job:
    Decodes video, evaluates frames/meniscus/motion, updates job and submission.
    Larvae genus identification remains unvalidated according to spec.
    """
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True

    try:
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if not job:
            logger.error("Processing job %s not found", job_id)
            return

        submission = db.query(Submission).filter(Submission.id == job.submission_id).first()
        if not submission:
            logger.error("Submission %s for job %s not found", job.submission_id, job_id)
            return

        media = (
            db.query(MediaFile)
            .filter(MediaFile.submission_id == submission.id)
            .first()
        )
        if not media or not os.path.exists(media.file_path):
            job.status = "failed"
            job.error_message = "Media file not found on disk"
            submission.status = SubmissionStatus.failed
            db.commit()
            return

        start_time = time.perf_counter()
        job.status = "processing"
        job.started_at = datetime.now(timezone.utc)
        submission.status = SubmissionStatus.processing
        db.commit()

        try:
            analysis = analyze_larvae_video(media.file_path)
        except Exception as exc:
            logger.exception("Video analysis failed for job %s", job_id)
            job.status = "failed"
            job.error_message = str(exc)
            submission.status = SubmissionStatus.failed
            db.commit()
            return

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        job.frame_count = analysis["frame_count"]
        job.valid_frames = analysis["valid_frames"]
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)

        # Build identification result keeping unvalidated status
        model_ver = get_model_version()
        result = IdentificationResult(
            submission_id=submission.id,
            predicted_genus=None,
            confidence=None,
            model_version=model_ver,
            model_artifact="larvae_pipeline_v1",
            processing_time_ms=elapsed_ms,
            is_uncertain=True,
            uncertainty_message=(
                "Larvae identification model is not yet field-validated and "
                "must not be used for production predictions."
            ),
            all_scores={
                "status": "model_not_validated",
                "meniscus_detected": analysis["meniscus_detected"],
                "motion_detected": analysis["motion_detected"],
                "avg_orientation_deg": analysis["avg_orientation_deg"],
                "valid_frames": analysis["valid_frames"],
                "total_frames": analysis["frame_count"],
            },
        )
        db.add(result)
        submission.status = SubmissionStatus.completed
        db.commit()
        logger.info("Processed larvae video job %s successfully", job_id)

    finally:
        if own_session:
            db.close()
