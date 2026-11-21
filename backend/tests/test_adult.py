"""Adult mosquito specimen submission and inference test suite."""
from __future__ import annotations

import io
import pytest
from tests.conftest import create_test_image


def test_submit_valid_jpeg(client, test_user):
    img_bytes = create_test_image(width=224, height=224, fmt="JPEG")
    res = client.post(
        "/api/v1/adult/submit",
        headers=test_user["headers"],
        files={"file": ("mosquito.jpg", io.BytesIO(img_bytes), "image/jpeg")},
    )
    assert res.status_code == 201
    data = res.json()
    assert "id" in data
    assert data["type"] == "adult"
    assert data["status"] == "completed"
    assert "result" in data
    result = data["result"]
    assert result is not None
    assert "confidence" in result
    assert "model_version" in result
    assert "processing_time_ms" in result
    assert "all_scores" in result
    assert set(result["all_scores"].keys()) == {"aedes", "anopheles", "culex"}


def test_submit_valid_png(client, test_user):
    img_bytes = create_test_image(width=224, height=224, fmt="PNG")
    res = client.post(
        "/api/v1/adult/submit",
        headers=test_user["headers"],
        files={"file": ("mosquito.png", io.BytesIO(img_bytes), "image/png")},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "completed"


def test_submit_invalid_file_signature(client, test_user):
    """File extension is .jpg but magic bytes are plain text."""
    fake_data = b"This is not a jpeg image at all."
    res = client.post(
        "/api/v1/adult/submit",
        headers=test_user["headers"],
        files={"file": ("fake.jpg", io.BytesIO(fake_data), "image/jpeg")},
    )
    assert res.status_code == 422
    assert res.json()["error_code"] == "INVALID_FILE_TYPE"


def test_submit_corrupted_image(client, test_user):
    """Valid JPEG header followed by junk bytes."""
    corrupted_data = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 200
    res = client.post(
        "/api/v1/adult/submit",
        headers=test_user["headers"],
        files={"file": ("corrupt.jpg", io.BytesIO(corrupted_data), "image/jpeg")},
    )
    assert res.status_code == 422
    assert res.json()["error_code"] == "CORRUPTED_IMAGE"


def test_submit_too_small_image(client, test_user):
    """Dimensions under 100x100 should be rejected."""
    small_bytes = create_test_image(width=64, height=64, fmt="JPEG")
    res = client.post(
        "/api/v1/adult/submit",
        headers=test_user["headers"],
        files={"file": ("small.jpg", io.BytesIO(small_bytes), "image/jpeg")},
    )
    assert res.status_code == 422
    assert res.json()["error_code"] == "IMAGE_TOO_SMALL"


def test_get_submission_and_image(client, test_user):
    img_bytes = create_test_image(width=224, height=224, fmt="JPEG")
    sub_res = client.post(
        "/api/v1/adult/submit",
        headers=test_user["headers"],
        files={"file": ("mosquito.jpg", io.BytesIO(img_bytes), "image/jpeg")},
    )
    sub_id = sub_res.json()["id"]

    # Get submission detail
    res = client.get(f"/api/v1/adult/submissions/{sub_id}", headers=test_user["headers"])
    assert res.status_code == 200
    assert res.json()["id"] == sub_id

    # Get uploaded image
    img_get_res = client.get(f"/api/v1/adult/submissions/{sub_id}/image", headers=test_user["headers"])
    assert img_get_res.status_code == 200
    assert img_get_res.headers["content-type"] in ["image/jpeg", "image/png"]


def test_list_submissions_paginated(client, test_user):
    # Submit 2 images
    for _ in range(2):
        img_bytes = create_test_image()
        client.post(
            "/api/v1/adult/submit",
            headers=test_user["headers"],
            files={"file": ("mosquito.jpg", io.BytesIO(img_bytes), "image/jpeg")},
        )

    res = client.get("/api/v1/adult/submissions?page=1&page_size=10", headers=test_user["headers"])
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 2
    assert len(data["items"]) >= 2


def test_submit_oversized_image(client, test_user, monkeypatch):
    """Oversized files must be rejected with 422 and FILE_TOO_LARGE."""
    from app.config import settings
    monkeypatch.setattr(settings, "MAX_IMAGE_SIZE_MB", 1)  # 1MB limit
    oversized_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * (1024 * 1024 + 50)
    res = client.post(
        "/api/v1/adult/submit",
        headers=test_user["headers"],
        files={"file": ("huge.jpg", io.BytesIO(oversized_bytes), "image/jpeg")},
    )
    assert res.status_code == 422
    assert res.json()["error_code"] == "FILE_TOO_LARGE"


def test_submit_exceeded_dimensions_image(client, test_user):
    """Images exceeding 8192x8192 must be rejected with IMAGE_DIMENSIONS_EXCEEDED."""
    from PIL import Image
    huge_img = Image.new("RGB", (8200, 150), color=(128, 128, 128))
    buf = io.BytesIO()
    huge_img.save(buf, format="PNG")
    res = client.post(
        "/api/v1/adult/submit",
        headers=test_user["headers"],
        files={"file": ("wide.png", io.BytesIO(buf.getvalue()), "image/png")},
    )
    assert res.status_code == 422
    assert res.json()["error_code"] == "IMAGE_DIMENSIONS_EXCEEDED"


def test_submit_decompression_bomb(client, test_user, monkeypatch):
    """Images triggering decompression bomb check must be rejected with DECOMPRESSION_BOMB."""
    from PIL import Image
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1000)
    img = Image.new("RGB", (200, 200), color=(128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    res = client.post(
        "/api/v1/adult/submit",
        headers=test_user["headers"],
        files={"file": ("bomb.png", io.BytesIO(buf.getvalue()), "image/png")},
    )
    assert res.status_code == 422
    assert res.json()["error_code"] == "DECOMPRESSION_BOMB"


def test_actual_inference_with_candidate_exp_b(client, test_user):
    """Run real inference using candidate Exp B ONNX artifact and verify output contract."""
    from pathlib import Path
    from PIL import Image

    # Test with a real specimen from raw data if present
    repo_root = Path(__file__).resolve().parent.parent.parent
    sample_img = repo_root / "vectora-ai-starter" / "data" / "raw" / "aedes" / "Aedes_aegypti_1.jpg"
    assert sample_img.exists(), "Sample specimen must be present for actual inference test"

    with open(sample_img, "rb") as f:
        img_bytes = f.read()

    res = client.post(
        "/api/v1/adult/submit",
        headers=test_user["headers"],
        files={"file": ("Aedes_aegypti_1.jpg", io.BytesIO(img_bytes), "image/jpeg")},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "completed"
    assert "result" in data
    result = data["result"]
    assert result["confidence"] is not None
    assert set(result["all_scores"].keys()) == {"aedes", "anopheles", "culex"}
    assert result["processing_time_ms"] > 0
