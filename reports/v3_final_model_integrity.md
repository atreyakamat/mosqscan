# Vectora AI 3.0 — Model Artifact Integrity Audit

## 1. Executive Summary

This document records the model artifact audit for Vectora AI 3.0.
All tests follow ASD-STE100 writing principles.
Antigravity inspected the source checkpoint, ONNX export graphs, checksums, and deployment paths.

The active production candidate is EfficientNet-B0 trained with 224x224 input resolution.
The model uses FP32 precision on the Intel Core i7-2600 server CPU.
INT8 quantization is rejected for production because of a CPU hardware penalty and numerical drift.
All model outputs keep the mandatory status tag: `EXPERIMENTAL_NOT_FIELD_VALIDATED`.

---

## 2. Checkpoint and Model Provenance

The production model originates from the Exp B lineage with grouped parent-specimen stratification.
Training ran on PyTorch with seed 42.

```
Training Checkpoint Lineage:
Pretrained Backbone: torchvision.models.efficientnet_b0 (IMAGENET1K_V1)
Classifier Head:      Dropout(p=0.3) -> Linear(in_features=1280, out_features=3)
Loss Function:        Cross-Entropy Loss (weighted: Aedes=1.0, Anopheles=1.67, Culex=0.75)
Optimizer:            AdamW (learning_rate=1e-4, weight_decay=1e-2)
Resolution:           224 x 224 pixels (RGB)
Epochs:               15
Batch Size:           32
```

### Checkpoint File Details

| Property | Value |
| :--- | :--- |
| File Path | `models/v3/vectora_v3_best.pt` |
| File Size | 16,341,855 bytes (15.58 MiB) |
| SHA-256 Checksum | `03f2c4e21eb97928fdfe875533575bb4ffb6d5646eaeb2bb5b2fb0d98c4d846b` |
| Model Format | PyTorch State Dictionary (`torch.save`) |
| Serialization Target | TorchScript / ONNX Runtime Opset 17 |

---

## 3. ONNX Artifacts and Checksum Verification

Antigravity verified all ONNX artifacts in the active registry and archive directories.

### Deployed Artifact (Server FP32)

| Property | Active Server Path | Archive Training Path | Match Status |
| :--- | :--- | :--- | :--- |
| File Path | `models/vectora_v3_fp32.onnx` | `models/v3/vectora_v3_fp32.onnx` | Identical |
| File Size | 16,035,577 bytes (15.29 MiB) | 16,035,577 bytes (15.29 MiB) | Identical |
| SHA-256 | `c3a3656f746a1bb2e7ac428e44670d89cf51f0d0f923ad3aa15420e8a4592cfa` | `c3a3656f746a1bb2e7ac428e44670d89cf51f0d0f923ad3aa15420e8a4592cfa` | Verified Match |
| Precision | FP32 (Single Precision Float) | FP32 (Single Precision Float) | Matches Host AVX |
| Execution Status | **Active Production Inference** | Reference Model Archive | Approved |

### Edge Research Artifact (INT8 Quantized)

| Property | Active Server Path | Archive Training Path | Match Status |
| :--- | :--- | :--- | :--- |
| File Path | `models/vectora_v3_int8.onnx` | `models/v3/vectora_v3_int8.onnx` | Identical |
| File Size | 4,362,904 bytes (4.16 MiB) | 4,362,904 bytes (4.16 MiB) | Identical |
| SHA-256 | `f65cf4373b00bf8df812aedd039489107721c51112932956d7d98351b286ba4e` | `f65cf4373b00bf8df812aedd039489107721c51112932956d7d98351b286ba4e` | Verified Match |
| Precision | Dynamic Quantization (Uint8/Int8) | Dynamic Quantization (Uint8/Int8) | No Hardware VNNI |
| Execution Status | **Rejected from Active Path** | Research Baseline | Disqualified |

---

## 4. Resolution of Model Path Discrepancies

The codebase contains two model folders: `models/` and `models/v3/`.
Antigravity inspected the application configuration to resolve the canonical location.

1. **Active Configuration:** `backend/app/config.py` specifies `MODEL_PATH = os.getenv("MODEL_PATH", "models/vectora_v3_fp32.onnx")`.
2. **Docker Compose Binding:** The Docker container mounts `/home/nimr/Projects/mosqscan/models` to `/app/models`.
3. **Checksum Identity:** The active file `models/vectora_v3_fp32.onnx` and the archive file `models/v3/vectora_v3_fp32.onnx` share the exact SHA-256 checksum `c3a3656f...`.
4. **Resolution Decision:** `models/` is the canonical runtime directory for the backend inference server. The directory `models/v3/` stores training lineage and evaluation checkpoints.

---

## 5. Input Preprocessing Contract and Class Ordering

The Android client, Web platform, and FastAPI backend use the identical inference contract.

### Class Label Ordering

The model output tensor contains 3 logits corresponding to the following genus order:

| Class Index | Genus | Scientific Significance | Support in Audited Lineage |
| :--- | :--- | :--- | :--- |
| **0** | `aedes` | Vector of Dengue, Chikungunya, Zika | 900 images (15 parents) |
| **1** | `anopheles` | Vector of Malaria | 540 images (9 parents) |
| **2** | `culex` | Vector of West Nile Virus, Lymphatic Filariasis | 1,200 images (20 parents) |

### Tensor Preprocessing Specifications

```
Input Format:    RGB Image (channels-first: [Batch, Channels, Height, Width])
Dimensions:      [1, 3, 224, 224]
Value Range:     Normalized Floating-Point [0.0, 1.0]
Mean Vector:     [0.485, 0.456, 0.406] (ImageNet RGB standard)
Std Vector:      [0.229, 0.224, 0.225] (ImageNet RGB standard)
Transformation:  x_normalized = (x / 255.0 - mean) / std
```

### Softmax and Uncertainty Gating

The model applies standard softmax along dimension 1.
The backend applies a certainty threshold:

$$\tau_{\text{certainty}} = 0.65 \quad (65.0\%)$$

- When $\max(P(\text{genus})) \ge 0.65$: The system reports the top genus and sets `is_uncertain = False`.
- When $\max(P(\text{genus})) < 0.65$: The system sets `is_uncertain = True` and displays:
  > *"Uncertain identification. Manual inspection is advised. Raw model score is below the 65% certainty threshold."*
- All responses include:
  > `status: "EXPERIMENTAL_NOT_FIELD_VALIDATED"`
  > *"Raw softmax output is an uncalibrated experimental heuristic. Visual identification only. Not field-validated for epidemiological decisions."*

---

## 6. Audit Conclusion

The model artifact `models/vectora_v3_fp32.onnx` is verified.
Checksums match across the repository.
The class ordering matches the training labels.
Dynamic INT8 quantization is excluded from the active inference path.
Model integrity is verified.
