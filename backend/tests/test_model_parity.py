"""Model parity tests comparing FP32 backend model and INT8 mobile model."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np
import onnxruntime as ort
import pytest
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MANIFEST_PATH = REPO_ROOT / "model-registry" / "manifest.json"
FP32_PATH = REPO_ROOT / "vectora-ai-starter" / "models" / "efficientnet_b0.onnx"
INT8_PATH = REPO_ROOT / "vectora-ai-starter" / "models" / "efficientnet_b0_int8.onnx"
ANDROID_INT8_PATH = REPO_ROOT / "android" / "app" / "src" / "main" / "assets" / "efficientnet_b0_int8.onnx"
GOLDEN_IMAGES_DIR = REPO_ROOT / "model-registry" / "golden-tests" / "images"

CLASSES = ["aedes", "anopheles", "culex"]
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def _sha256(path: Path) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _preprocess(img: Image.Image) -> np.ndarray:
    img = img.convert("RGB").resize((224, 224), Image.BILINEAR)
    arr = np.array(img, dtype=np.float32) / 255.0
    arr = (arr - MEAN) / STD
    arr = arr.transpose(2, 0, 1)[np.newaxis, ...]
    return arr


def _run_model(session: ort.InferenceSession, arr: np.ndarray) -> np.ndarray:
    input_name = session.get_inputs()[0].name
    outputs = session.run(None, {input_name: arr})
    logits = outputs[0][0]
    exp = np.exp(logits - np.max(logits))
    return exp / exp.sum()


def test_manifest_checksums_match_files():
    """Verify on-disk models match SHA-256 in manifest."""
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)

    fp32_expected = manifest["adult_classifier"]["artifacts"]["fp32_onnx"]["sha256"]
    int8_expected = manifest["adult_classifier"]["artifacts"]["int8_onnx"]["sha256"]

    assert _sha256(FP32_PATH) == fp32_expected
    assert _sha256(INT8_PATH) == int8_expected


def test_android_bundled_model_matches_registry():
    """Verify the Android packaged model is identical to the registry INT8 artifact."""
    assert ANDROID_INT8_PATH.exists(), f"Android asset missing at {ANDROID_INT8_PATH}"
    assert _sha256(ANDROID_INT8_PATH) == _sha256(INT8_PATH)


def test_fp32_and_int8_prediction_parity():
    """Verify FP32 and INT8 produce matching top classes on reference images."""
    fp32_session = ort.InferenceSession(str(FP32_PATH), providers=["CPUExecutionProvider"])
    int8_session = ort.InferenceSession(str(INT8_PATH), providers=["CPUExecutionProvider"])

    image_files = list(GOLDEN_IMAGES_DIR.glob("*.jpg"))
    assert len(image_files) > 0, "Golden test images should be present"

    results = []
    for img_path in sorted(image_files):
        img = Image.open(img_path)
        arr = _preprocess(img)

        fp32_probs = _run_model(fp32_session, arr)
        int8_probs = _run_model(int8_session, arr)

        fp32_top = int(np.argmax(fp32_probs))
        int8_top = int(np.argmax(int8_probs))

        # Check top class prediction parity
        assert fp32_top == int8_top, (
            f"Class prediction mismatch on {img_path.name}: "
            f"FP32 predicted {CLASSES[fp32_top]} ({fp32_probs[fp32_top]:.3f}) vs "
            f"INT8 predicted {CLASSES[int8_top]} ({int8_probs[int8_top]:.3f})"
        )

        # Max probability difference across all classes must be within quantization tolerance
        max_diff = float(np.max(np.abs(fp32_probs - int8_probs)))
        assert max_diff < 0.20, f"Quantization delta {max_diff:.3f} exceeded tolerance on {img_path.name}"

        results.append({
            "image": img_path.name,
            "predicted_genus": CLASSES[fp32_top],
            "fp32_confidence": float(fp32_probs[fp32_top]),
            "int8_confidence": float(int8_probs[int8_top]),
            "max_abs_delta": max_diff,
        })

    # Save golden test results
    results_dir = REPO_ROOT / "model-registry" / "golden-tests" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    with open(results_dir / "parity_report.json", "w") as f:
        json.dump(results, f, indent=2)
