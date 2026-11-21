# Model Registry — Vectora AI

The model registry is the single source of truth for all ML model artifacts used by Vectora AI. It lives at `model-registry/` in the repository root.

---

## Registry Structure

```
model-registry/
├── manifest.json             ← Canonical model metadata and checksums
├── verify_checksums.sh       ← Checksum verification script
└── golden-tests/
    ├── README.md             ← Golden test instructions
    ├── images/               ← Reference test images (committed)
    └── results/              ← Expected output JSONs (committed)
```

The actual ONNX model files live in `vectora-ai-starter/models/` and are referenced by `manifest.json`. They are **not** duplicated inside `model-registry/`.

---

## manifest.json Structure

```json
{
  "product": "Vectora AI",
  "schema_version": "1",
  "model_version": "1.0.0",
  "created_at": "YYYY-MM-DD",
  "adult_classifier": {
    "architecture": "...",
    "num_classes": 3,
    "classes": ["aedes", "anopheles", "culex"],
    "artifacts": {
      "fp32_onnx": { ... },
      "int8_onnx": { ... }
    },
    "evaluation": { ... }
  },
  "larvae_model": { ... }
}
```

### Key Fields

| Field | Description |
|-------|-------------|
| `schema_version` | Registry format version; increment if schema structure changes |
| `model_version` | SemVer of the model; increment on any weight or architecture change |
| `confidence_threshold` | Minimum confidence to report a positive identification (0.65) |
| `artifacts[].sha256` | SHA-256 hex digest of the ONNX file at time of registration |
| `artifacts[].size_bytes` | Expected byte size of the file |
| `evaluation.warning` | Required disclaimer for all pilot-stage models |

---

## Android vs Backend Artifact Selection

| Artifact | Key | Deployment | File | Format |
|----------|-----|-----------|------|--------|
| FP32 ONNX | `fp32_onnx` | Backend (server) | `efficientnet_b0.onnx` | ONNX FP32, opset 17 |
| INT8 ONNX | `int8_onnx` | Android APK | `efficientnet_b0_int8.onnx` | ONNX INT8 (dynamic quantization), opset 17 |

**Rules:**
- The backend **always** uses the FP32 model for maximum accuracy.
- Android **always** uses the INT8 model for on-device efficiency (~4× smaller).
- Never swap these — the INT8 model must not be used on the backend, and the FP32 model must not be bundled in the APK.

---

## Registering a New Model Version

Follow this procedure when updating model weights, architecture, or quantization settings.

### Step 1 — Export ONNX Artifacts

```bash
cd vectora-ai-starter
python export_onnx.py --checkpoint models/efficientnet_b0_best.pt \
    --output-fp32 models/efficientnet_b0.onnx \
    --output-int8 models/efficientnet_b0_int8.onnx \
    --opset 17
```

### Step 2 — Compute Checksums

```bash
sha256sum models/efficientnet_b0.onnx
sha256sum models/efficientnet_b0_int8.onnx
```

### Step 3 — Run Evaluation

```bash
python evaluate.py --model models/efficientnet_b0.onnx \
    --data data/raw --split test
```

Record `accuracy`, `macro_f1`, and `test_samples`.

### Step 4 — Update manifest.json

Update the following fields:
- `model_version` — bump the SemVer (e.g., `1.0.0` → `1.1.0`)
- `created_at` — today's date
- `artifacts.fp32_onnx.sha256` — new FP32 checksum
- `artifacts.int8_onnx.sha256` — new INT8 checksum
- `artifacts.fp32_onnx.size_bytes` — new FP32 file size
- `artifacts.int8_onnx.size_bytes` — new INT8 file size
- `evaluation` — updated metrics

### Step 5 — Run Golden Tests

```bash
bash model-registry/verify_checksums.sh
python scripts/run_all_golden_tests.py \
    --golden-dir model-registry/golden-tests \
    --fp32-model vectora-ai-starter/models/efficientnet_b0.onnx \
    --int8-model vectora-ai-starter/models/efficientnet_b0_int8.onnx
```

All tests must pass before the model may be deployed.

### Step 6 — Update Golden Test Results

If the new model improves predictions on golden test images, update the expected result JSONs:

```bash
python scripts/run_golden_test.py \
    --image model-registry/golden-tests/images/<name>.jpg \
    --fp32-model vectora-ai-starter/models/efficientnet_b0.onnx \
    --int8-model vectora-ai-starter/models/efficientnet_b0_int8.onnx \
    --output model-registry/golden-tests/results/<name>.json \
    --overwrite
```

Commit the updated results with a clear commit message describing the change.

### Step 7 — Commit and Tag

```bash
git add model-registry/manifest.json model-registry/golden-tests/
git commit -m "model: bump to v1.1.0 — improved anopheles recall"
git tag model-v1.1.0
```

---

## Checksum Verification

Run at any time to verify that the ONNX files on disk match the registry:

```bash
bash model-registry/verify_checksums.sh
```

This script checks:
1. That both ONNX files exist at `vectora-ai-starter/models/`
2. That their SHA-256 digests match the values in `manifest.json`

Expected output on success:
```
✅ All checksums verified. Models are intact.
```

Integrate this into CI/CD pipelines to catch accidental model file corruption or replacement.

---

## Never-Use Rules

> [!CAUTION]
> **Violation of these rules could result in incorrect public health guidance.**

1. **Never use the larvae model for production predictions.** Its `status` is `not_validated`. It must remain `prediction: null` until a validated classifier is integrated and independently tested.

2. **Never deploy a model whose checksums do not match the manifest.** A checksum mismatch indicates file corruption or an unauthorised replacement.

3. **Never promote a model to production without passing all golden tests.**

4. **Never use evaluation metrics from the augmented dataset** to represent real-world performance. The 44-image original dataset metrics are the only defensible benchmark.

5. **Never report test accuracy from the full 44-image dataset as "test accuracy."** The 6-sample holdout set is the test split; the 44-sample full-dataset result is for reference only.
