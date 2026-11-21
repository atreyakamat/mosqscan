"""Video duration boundary and validation test suite."""
from __future__ import annotations

import io
import os
import tempfile
import pytest

from app.services.larvae_service import validate_video_duration
from tests.conftest import create_test_video


def test_video_boundary_2_99s_rejected():
    """2.99s video must be rejected with VIDEO_TOO_SHORT."""
    video_bytes = create_test_video(frames=299, fps=100)
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(video_bytes)
        tmp_path = tmp.name

    try:
        dur, err = validate_video_duration(tmp_path)
        assert err == "VIDEO_TOO_SHORT"
        assert dur == pytest.approx(2.99, abs=0.01)
    finally:
        os.unlink(tmp_path)


def test_video_boundary_3_00s_accepted():
    """3.00s video must be accepted."""
    video_bytes = create_test_video(frames=300, fps=100)
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(video_bytes)
        tmp_path = tmp.name

    try:
        dur, err = validate_video_duration(tmp_path)
        assert err is None
        assert dur == pytest.approx(3.00, abs=0.01)
    finally:
        os.unlink(tmp_path)


def test_video_boundary_4_00s_accepted():
    """4.00s video must be accepted."""
    video_bytes = create_test_video(frames=400, fps=100)
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(video_bytes)
        tmp_path = tmp.name

    try:
        dur, err = validate_video_duration(tmp_path)
        assert err is None
        assert dur == pytest.approx(4.00, abs=0.01)
    finally:
        os.unlink(tmp_path)


def test_video_boundary_5_00s_accepted():
    """5.00s video must be accepted."""
    video_bytes = create_test_video(frames=500, fps=100)
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(video_bytes)
        tmp_path = tmp.name

    try:
        dur, err = validate_video_duration(tmp_path)
        assert err is None
        assert dur == pytest.approx(5.00, abs=0.01)
    finally:
        os.unlink(tmp_path)


def test_video_boundary_5_01s_rejected():
    """5.01s video must be rejected with VIDEO_TOO_LONG."""
    video_bytes = create_test_video(frames=501, fps=100)
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(video_bytes)
        tmp_path = tmp.name

    try:
        dur, err = validate_video_duration(tmp_path)
        assert err == "VIDEO_TOO_LONG"
        assert dur == pytest.approx(5.01, abs=0.01)
    finally:
        os.unlink(tmp_path)


def test_corrupted_video_rejected():
    """Corrupted / unreadable bytes must be rejected with VIDEO_CORRUPTED."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(b"not a valid video file content at all")
        tmp_path = tmp.name

    try:
        dur, err = validate_video_duration(tmp_path)
        assert err == "VIDEO_CORRUPTED"
    finally:
        os.unlink(tmp_path)


def test_truncated_video_rejected():
    """Truncated MP4 file with incomplete header must be rejected as VIDEO_CORRUPTED."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(b"\x00\x00\x00 ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 50)
        tmp_path = tmp.name

    try:
        dur, err = validate_video_duration(tmp_path)
        assert err == "VIDEO_CORRUPTED"
    finally:
        os.unlink(tmp_path)


def test_variable_frame_rate_video_handled():
    """VFR video with varying frame timestamps must have its actual duration computed accurately."""
    import subprocess
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Generate a 4.0s VFR video with ffmpeg
        cmd = [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=4:size=64x64:rate=30",
            "-vf", "setpts=N*N*0.001+PTS",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", tmp_path
        ]
        res = subprocess.run(cmd, capture_output=True)
        assert res.returncode == 0, "ffmpeg must generate VFR test video"

        dur, err = validate_video_duration(tmp_path)
        assert err is None
        assert 3.0 <= dur <= 5.0
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_api_submit_video_too_short(client, test_user):
    video_bytes = create_test_video(frames=200, fps=100)  # 2.0s
    res = client.post(
        "/api/v1/larvae/submit",
        headers=test_user["headers"],
        files={"file": ("short.mp4", io.BytesIO(video_bytes), "video/mp4")},
    )
    assert res.status_code == 422
    data = res.json()
    assert data["success"] is False
    assert data["error_code"] == "VIDEO_TOO_SHORT"
    assert "at least 3 seconds" in data["message"]


def test_api_submit_video_too_long(client, test_user):
    video_bytes = create_test_video(frames=600, fps=100)  # 6.0s
    res = client.post(
        "/api/v1/larvae/submit",
        headers=test_user["headers"],
        files={"file": ("long.mp4", io.BytesIO(video_bytes), "video/mp4")},
    )
    assert res.status_code == 422
    data = res.json()
    assert data["success"] is False
    assert data["error_code"] == "VIDEO_TOO_LONG"
    assert "not exceed 5 seconds" in data["message"]


def test_api_submit_video_accepted_and_processed(client, test_user):
    video_bytes = create_test_video(frames=350, fps=100)  # 3.5s
    res = client.post(
        "/api/v1/larvae/submit",
        headers=test_user["headers"],
        files={"file": ("larvae.mp4", io.BytesIO(video_bytes), "video/mp4")},
    )
    assert res.status_code == 202
    data = res.json()
    assert "job_id" in data
    assert "submission_id" in data
    assert data["status"] in ["queued", "processing", "completed"]

    job_id = data["job_id"]
    job_res = client.get(f"/api/v1/larvae/jobs/{job_id}", headers=test_user["headers"])
    assert job_res.status_code == 200

    # Submission endpoint returns model_not_validated
    sub_id = data["submission_id"]
    sub_res = client.get(f"/api/v1/larvae/submissions/{sub_id}", headers=test_user["headers"])
    assert sub_res.status_code == 200
    assert sub_res.json()["model_status"] == "model_not_validated"


def test_video_oversized_file_rejected(client, test_user, monkeypatch):
    """Oversized video file must be rejected with 422 and FILE_TOO_LARGE."""
    from app.config import settings
    monkeypatch.setattr(settings, "MAX_VIDEO_SIZE_MB", 1)  # 1MB limit
    oversized_data = b"0" * (1024 * 1024 + 100)
    res = client.post(
        "/api/v1/larvae/submit",
        headers=test_user["headers"],
        files={"file": ("huge.mp4", io.BytesIO(oversized_data), "video/mp4")},
    )
    assert res.status_code == 422
    assert res.json()["error_code"] == "FILE_TOO_LARGE"


def test_background_job_failure_handling(db_session):
    """When media file is missing, background job is marked failed with error message."""
    from app.db.models import MediaFile, ProcessingJob, Submission, SubmissionStatus, SubmissionType
    from app.workers.video_processor import process_larvae_video_job

    submission = Submission(
        user_id="test-user-id",
        type=SubmissionType.larvae,
        status=SubmissionStatus.pending,
    )
    db_session.add(submission)
    db_session.flush()

    media = MediaFile(
        submission_id=submission.id,
        original_filename="missing.mp4",
        stored_filename="missing.mp4",
        file_path="/nonexistent/path/missing.mp4",
        mime_type="video/mp4",
        file_size=1000,
        sha256_checksum="dummy",
    )
    db_session.add(media)
    db_session.flush()

    job = ProcessingJob(
        submission_id=submission.id,
        status="queued",
    )
    db_session.add(job)
    db_session.commit()

    # Process job directly with db_session
    process_larvae_video_job(job.id, db=db_session)

    db_session.refresh(job)
    db_session.refresh(submission)
    assert job.status == "failed"
    assert "Media file not found" in job.error_message
    assert submission.status == SubmissionStatus.failed


def test_invalid_codec_rejected():
    """Video with invalid codec / payload must be rejected with VIDEO_CORRUPTED."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        # Invalid video header / codec bytes
        tmp.write(b"\x00\x00\x00\x18ftypinvalid\x00\x00\x00\x00garbage_codec_bytes_12345")
        tmp_path = tmp.name

    try:
        dur, err = validate_video_duration(tmp_path)
        assert err == "VIDEO_CORRUPTED"
    finally:
        os.unlink(tmp_path)


def test_missing_duration_rejected():
    """Video where duration cannot be determined must be rejected with VIDEO_INVALID_DURATION or VIDEO_CORRUPTED."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        # Empty file
        tmp.write(b"")
        tmp_path = tmp.name

    try:
        dur, err = validate_video_duration(tmp_path)
        assert err in ["VIDEO_INVALID_DURATION", "VIDEO_CORRUPTED"]
    finally:
        os.unlink(tmp_path)


def test_false_client_duration_rejected(client, test_user):
    """Client asserting duration 4.0s but uploading 2.0s video must be rejected based on decoded media."""
    # 2.0s video
    video_bytes = create_test_video(frames=200, fps=100)
    res = client.post(
        "/api/v1/larvae/submit",
        headers=test_user["headers"],
        files={"file": ("fake_4s_video.mp4", io.BytesIO(video_bytes), "video/mp4")},
        data={"client_duration": "4.0"},  # Spoofed client metadata
    )
    assert res.status_code == 422
    assert res.json()["error_code"] == "VIDEO_TOO_SHORT"
