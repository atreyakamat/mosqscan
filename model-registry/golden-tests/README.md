# Golden Tests — Vectora AI Model Parity

Golden tests verify that the **Android INT8** model and the **backend FP32** model produce consistent predictions on the same reference images. This ensures that a user photographing a mosquito with the mobile app will receive the same genus identification as the backend inference pipeline.

---

## Purpose

| Goal | Detail |
|------|--------|
| **Catch quantization regressions** | INT8 dynamic quantization reduces model size by ~4× but can shift confidence scores. Golden tests flag regressions early. |
| **Validate deployment parity** | Confirms that the ONNX export is correct for both runtime targets. |
| **Gate model releases** | A new model version must pass all golden tests before it may be shipped to Android or promoted to backend production. |
| **Provide reproducible baselines** | Each test image is a fixed, committed artifact with known ground truth. |

---

## Directory Structure

```
golden-tests/
├── README.md               ← this file
├── images/                 ← reference test images (committed to repo)
│   ├── aedes_01.jpg
│   ├── anopheles_01.jpg
│   └── culex_01.jpg
└── results/                ← expected output records (JSON)
    ├── aedes_01.json
    ├── anopheles_01.json
    └── culex_01.json
```

> **Important:** Images in `images/` must be **representative, field-realistic specimens**. Do not use training set images.

---

## How to Add a Test Image

1. Place the image in `golden-tests/images/` with a descriptive filename:
   ```
   <genus>_<sequence>.jpg
   ```
   e.g., `aedes_02.jpg`, `culex_03.jpg`

2. Run the parity script against both models:
   ```bash
   python scripts/run_golden_test.py \
       --image golden-tests/images/aedes_02.jpg \
       --fp32-model ../vectora-ai-starter/models/efficientnet_b0.onnx \
       --int8-model ../vectora-ai-starter/models/efficientnet_b0_int8.onnx \
       --output golden-tests/results/aedes_02.json
   ```

3. Review the generated result file and confirm the predictions are correct (matching the true genus label).

4. Commit both the image and the result JSON to the repository.

---

## Expected Result File Format

Each result file is a JSON document with the following structure:

```json
{
  "image": "aedes_01.jpg",
  "true_label": "aedes",
  "created_at": "2026-11-11",
  "model_version": "1.0.0",
  "fp32": {
    "predicted_class": "aedes",
    "confidence": 0.812,
    "probabilities": {
      "aedes": 0.812,
      "anopheles": 0.103,
      "culex": 0.085
    },
    "above_threshold": true
  },
  "int8": {
    "predicted_class": "aedes",
    "confidence": 0.798,
    "probabilities": {
      "aedes": 0.798,
      "anopheles": 0.112,
      "culex": 0.090
    },
    "above_threshold": true
  },
  "parity": {
    "class_match": true,
    "confidence_delta": 0.014,
    "within_tolerance": true,
    "tolerance": 0.05
  }
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `image` | string | Filename of the reference image |
| `true_label` | string | Ground-truth genus (`aedes`, `anopheles`, or `culex`) |
| `model_version` | string | Model registry version this result was generated against |
| `fp32.predicted_class` | string | Top-1 prediction from the FP32 backend model |
| `fp32.confidence` | float | Softmax score for the top-1 class (0–1) |
| `fp32.above_threshold` | bool | Whether confidence ≥ 0.65 (the production threshold) |
| `int8.predicted_class` | string | Top-1 prediction from the INT8 Android model |
| `int8.confidence` | float | Softmax score for the top-1 class (0–1) |
| `parity.class_match` | bool | True if both models predict the same class |
| `parity.confidence_delta` | float | Absolute difference in top-1 confidence |
| `parity.within_tolerance` | bool | True if `confidence_delta` ≤ 0.05 |

---

## Acceptable Numerical Tolerance

**Confidence values may differ by ±0.05** between the INT8 and FP32 models.

This tolerance accounts for the precision loss introduced by INT8 dynamic quantization. The key requirement is that **both models agree on the predicted class** (top-1). A confidence delta larger than 0.05 is a **test failure** that requires investigation before release.

| Criterion | Pass | Fail |
|-----------|------|------|
| Predicted class (top-1) | Match | Mismatch |
| Confidence delta | ≤ 0.05 | > 0.05 |
| Both above threshold | Optional | — |

---

## Running All Golden Tests

```bash
# From the repository root
bash model-registry/verify_checksums.sh
python scripts/run_all_golden_tests.py \
    --golden-dir model-registry/golden-tests \
    --fp32-model vectora-ai-starter/models/efficientnet_b0.onnx \
    --int8-model vectora-ai-starter/models/efficientnet_b0_int8.onnx
```

Expected output:
```
✓ aedes_01:    FP32=aedes(0.812) INT8=aedes(0.798)  Δ=0.014  PASS
✓ anopheles_01: FP32=anopheles(0.701) INT8=anopheles(0.688)  Δ=0.013  PASS
✓ culex_01:    FP32=culex(0.934) INT8=culex(0.921)  Δ=0.013  PASS

3/3 tests passed. Max confidence delta: 0.014
```

---

## Failure Procedure

If a golden test fails after a model update:

1. **Do not ship** the new model to Android or backend production.
2. Investigate whether the quantization settings need adjustment (e.g., switch to static quantization with calibration data).
3. Re-run all golden tests after the fix.
4. Update result JSONs only when the new model is intentionally replacing the old one — record this in the model registry changelog.
