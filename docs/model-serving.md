# Vectora AI 2.2 — Model Serving Specification

## 1. Candidate Model Identity

Vectora AI 2.2 deploys the candidate experimental adult mosquito classifier **Exp B**:
- **Artifact Path**: `models/vectora_candidate_exp_b.onnx`
- **Model Type**: Deep Convolutional Neural Network (EfficientNet-B0 backbone)
- **Precision**: 32-bit Floating Point (FP32)
- **Canonical SHA-256 Checksum**:
  ```
  d644b9cd9c952d461bbfbb44e8b1926cdcf9bbbfb9cd43f85065cbed0d7b1499
  ```
- **Target Classes**:
  - Index `0`: `aedes`
  - Index `1`: `anopheles`
  - Index `2`: `culex`

---

## 2. Model Input and Preprocessing Contract

The model requires a four-dimensional tensor:
- **Shape**: `[1, 3, 224, 224]`
- **Color Format**: RGB (Red, Green, Blue) normalized to range `[0.0, 1.0]`
- **Normalization Parameters**:
  - Mean vector: `[0.485, 0.456, 0.406]`
  - Standard deviation vector: `[0.229, 0.224, 0.225]`
- **Data Type**: `float32`

### Preprocessing Operations:
1. Decode image into RGB PIL Image.
2. Apply EXIF transposition (`ImageOps.exif_transpose`).
3. Extract crop region if bounding box coordinates are provided.
4. Resize crop to `(224, 224)` using bilinear interpolation (`Image.Resampling.BILINEAR`).
5. Convert PIL Image to NumPy array `(224, 224, 3)`.
6. Transpose dimensions to Channel-First format: `(3, 224, 224)`.
7. Subtract mean, divide by standard deviation, and expand dimensions to `(1, 3, 224, 224)`.

---

## 3. Manifest and Model Metadata Endpoints

Model information is registered in `model-registry/manifest.json` and exposed by the backend:

### Endpoint: `GET /api/v1/models/info` (or `/api/v1/models/manifest`)
```json
{
  "adult_model": {
    "model_name": "vectora_candidate_exp_b.onnx",
    "architecture": "EfficientNet-B0",
    "precision": "FP32",
    "sha256": "d644b9cd9c952d461bbfbb44e8b1926cdcf9bbbfb9cd43f85065cbed0d7b1499",
    "verified": true,
    "input_shape": [1, 3, 224, 224],
    "output_shape": [1, 3],
    "classes": ["aedes", "anopheles", "culex"],
    "status": "EXPERIMENTAL_NOT_FIELD_VALIDATED"
  },
  "larvae_model": {
    "status": "NOT_DEPLOYED"
  }
}
```

---

## 4. Probabilities and Threshold Guidance

The model output layer yields unnormalized logits.
The server transforms logits into softmax probabilities:
$$P(c) = \frac{e^{z_c}}{\sum_{j=1}^{3} e^{z_j}}$$

### 4.1 Uncalibrated Score Notice
The Exp B model has not undergone isotonic calibration or Platt scaling on multi-site field data.
Softmax scores reflect raw neural network outputs and must not be interpreted as absolute statistical probabilities.

### 4.2 Minimum Confidence Threshold (0.65)
- **High Confidence ($\ge 0.65$)**: Top genus is presented with uncalibrated confidence score.
- **Low Confidence ($< 0.65$)**: Result is classified as `Uncertain`. The UI advises manual inspection and entomologist review.
