"""Tests for Vectora AI 2.2 Server-hosted inference, crop processing, and model integrity."""
from __future__ import annotations

import io
import json
import pytest
from PIL import Image
from tests.conftest import create_test_image


def test_submit_with_valid_normalized_crop(client, test_user):
    """Test adult submission with explicit crop coordinates."""
    img_bytes = create_test_image(width=500, height=500, fmt="JPEG")
    res = client.post(
        "/api/v1/adult/submit",
        headers=test_user["headers"],
        files={"file": ("mosquito_field.jpg", io.BytesIO(img_bytes), "image/jpeg")},
        data={
            "crop_x": 0.1,
            "crop_y": 0.1,
            "crop_w": 0.6,
            "crop_h": 0.6,
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "completed"
    result = data["result"]
    assert result["model_status"] == "EXPERIMENTAL_NOT_FIELD_VALIDATED"
    assert "raw_score" in result
    assert "quality_feedback" in result
    qf = result["quality_feedback"]
    assert qf["crop_applied"] is True
    assert qf["crop_mode"] == "manual_specimen_crop"
    assert "crop_box_normalized" in qf


def test_submit_with_crop_box_json(client, test_user):
    """Test adult submission with crop_box JSON parameter."""
    img_bytes = create_test_image(width=400, height=400, fmt="JPEG")
    crop_json = json.dumps({"x": 0.05, "y": 0.05, "w": 0.5, "h": 0.5})
    res = client.post(
        "/api/v1/adult/submit",
        headers=test_user["headers"],
        files={"file": ("mosquito_json.jpg", io.BytesIO(img_bytes), "image/jpeg")},
        data={"crop_box": crop_json},
    )
    assert res.status_code == 201
    data = res.json()
    result = data["result"]
    assert result["quality_feedback"]["crop_applied"] is True


def test_submit_with_out_of_bounds_crop(client, test_user):
    """Out of bounds crop coordinates must be rejected."""
    img_bytes = create_test_image(width=300, height=300, fmt="JPEG")
    res = client.post(
        "/api/v1/adult/submit",
        headers=test_user["headers"],
        files={"file": ("oob.jpg", io.BytesIO(img_bytes), "image/jpeg")},
        data={
            "crop_x": 0.8,
            "crop_y": 0.8,
            "crop_w": 0.5,  # 0.8 + 0.5 = 1.3 > 1.05
            "crop_h": 0.5,
        },
    )
    assert res.status_code == 422
    assert res.json()["error_code"] == "INVALID_CROP_COORDINATES"


def test_submit_with_crop_too_small(client, test_user):
    """Crop region smaller than 20x20 pixels must be rejected."""
    img_bytes = create_test_image(width=200, height=200, fmt="JPEG")
    res = client.post(
        "/api/v1/adult/submit",
        headers=test_user["headers"],
        files={"file": ("tiny.jpg", io.BytesIO(img_bytes), "image/jpeg")},
        data={
            "crop_x": 0.1,
            "crop_y": 0.1,
            "crop_w": 0.01,  # 0.01 * 200 = 2 pixels
            "crop_h": 0.01,
        },
    )
    assert res.status_code == 422
    assert res.json()["error_code"] == "CROP_TOO_SMALL"


def test_submit_full_image_fallback(client, test_user):
    """Submission without crop must fallback to full image with documented note."""
    img_bytes = create_test_image(width=300, height=300, fmt="JPEG")
    res = client.post(
        "/api/v1/adult/submit",
        headers=test_user["headers"],
        files={"file": ("nocrop.jpg", io.BytesIO(img_bytes), "image/jpeg")},
    )
    assert res.status_code == 201
    data = res.json()
    result = data["result"]
    assert result["quality_feedback"]["crop_applied"] is False
    assert result["quality_feedback"]["crop_mode"] == "full_image_fallback"


def test_model_checksum_verification_failure(monkeypatch):
    """Checksum mismatch must halt model activation with RuntimeError."""
    from app.inference.adult_classifier import _verify_model_file
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".onnx") as f:
        f.write(b"tampered model data")
        f.flush()
        with pytest.raises(RuntimeError, match="Model SHA-256 checksum mismatch"):
            _verify_model_file(f.name, expected_sha256="d644b9cd9c952d461bbfbb44e8b1926cdcf9bbbfb9cd43f85065cbed0d7b1499")


def test_manifest_unregistered_model_refusal(monkeypatch):
    """Unregistered model artifact in manifest must raise RuntimeError and halt activation."""
    import app.inference.adult_classifier as ac
    monkeypatch.setattr(ac.settings, "ADULT_MODEL_ARTIFACT", "unregistered_fake_model.onnx")
    ac._cached_session = None

    with pytest.raises(Exception):
        ac._load_session()
    # Reset cached session
    ac._cached_session = None


def test_manifest_class_order_verification():
    """Verify manifest class order perfectly matches AdultClassifier.CLASSES."""
    from app.inference.adult_classifier import AdultClassifier
    from app.inference.registry import load_manifest

    manifest = load_manifest()
    manifest_classes = manifest.get("adult_classifier", {}).get("classes", [])
    assert manifest_classes == AdultClassifier.CLASSES
    assert manifest_classes == ["aedes", "anopheles", "culex"]

