# Vectora AI — Model Parity Specification

## 1. Principle: One Model Version, One Inference Contract, Two User Interfaces

Vectora AI enforces strict parity between the native Android mobile application and the web platform backend. Both environments share:
- Model Architecture: `EfficientNet-B0` (Torchvision)
- Model Version: `1.0.0`
- Target Classes: `["aedes", "anopheles", "culex"]` (fixed index order `0, 1, 2`)
- Input Size: `224 × 224` pixels
- Normalization: ImageNet constants (`mean = [0.485, 0.456, 0.406]`, `std = [0.229, 0.224, 0.225]`)
- Color Format: `RGB` (CHW layout)
- Decision Threshold: `0.65` (scores below 0.65 are flagged as uncertain; scores below 0.40 are flagged as non-target).

---

## 2. Artifact Parity & Checksum Verification

| Target | Deployment | Artifact File | Format | SHA-256 Checksum |
| :--- | :--- | :--- | :--- | :--- |
| **Backend API** | Server CPU / Container | `efficientnet_b0.onnx` | ONNX FP32 | `03fc58fd99578b756415ca50a8cc8b702e7e98ad248cfe0215f836e1652b0d19` |
| **Android Native** | Mobile / Offline | `efficientnet_b0_int8.onnx` | ONNX INT8 | `bac40d9af5441ddbdb6c6b19348fe04167ca4d8de7466611742022b7f505bd95` |

The Android APK bundles the exact `efficientnet_b0_int8.onnx` artifact inside `assets/`. Integrity tests confirm the asset sha256 matches the central model registry byte-for-byte.

---

## 3. Preprocessing Parity

### Python (Backend)
```python
image = image.convert("RGB").resize((224, 224), Image.BILINEAR)
arr = np.array(image, dtype=np.float32) / 255.0
arr = (arr - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
arr = arr.transpose(2, 0, 1)[np.newaxis, ...]
```

### Kotlin (Android)
```kotlin
val resized = Bitmap.createScaledBitmap(bitmap, 224, 224, true)
val floats = FloatArray(3 * 224 * 224)
// R channel
for (y in 0 until 224) { for (x in 0 until 224) { floats[idx++] = (Color.red(pixel)/255f - 0.485f) / 0.229f } }
// G channel
for (y in 0 until 224) { for (x in 0 until 224) { floats[idx++] = (Color.green(pixel)/255f - 0.456f) / 0.224f } }
// B channel
for (y in 0 until 224) { for (x in 0 until 224) { floats[idx++] = (Color.blue(pixel)/255f - 0.406f) / 0.225f } }
```

---

## 4. Golden Test Parity Verification

Golden tests in `backend/tests/test_model_parity.py` and `model-registry/golden-tests` run reference specimen images simultaneously through both FP32 and INT8 models to monitor numerical drift caused by dynamic quantization.

Key acceptance criteria:
1. **Predicted Top Genus Parity**: Matching predicted class when confidence exceeds threshold.
2. **Uncertainty Decision Parity**: Any image scoring below 0.65 in either model is unanimously flagged as uncertain with `"Uncertain identification. Manual inspection is advised."`.
3. **Probability Delta Bound**: Maximum absolute deviation between FP32 and INT8 probabilities across any class must remain `< 0.20`.
