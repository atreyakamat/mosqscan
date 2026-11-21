# Vectora AI — Training and Evaluation Report on 'Mosquito Images Original'

## 1. Executive Summary

This report documents the inspection of the `Mosquito Images Original` dataset and the complete training and validation of the EfficientNet-B0 model architecture on it.
All statements follow ASD-STE100 writing principles.

### Key Results
- **Dataset Inspected:** 44 high-resolution physical photographs across three mosquito genera. Zero corrupted files.
- **Training Strategy:** Two-stage transfer learning with dynamic data augmentation and class-weighted cross-entropy loss.
- **4-Fold Cross-Validation:** Achieved a **Mean Macro-F1 of $0.7799 \pm 0.0775$** and **Mean Balanced Accuracy of $0.7847 \pm 0.0972$** on untouched physical validation photographs.
- **Final Model Fit:** 100.00% classification accuracy (44 of 44 correct) on the unaugmented physical dataset.
- **Exported Artifacts:** Saved PyTorch weights ([`vectora_original_trained.pt`](file:///home/nimr/Projects/mosqscan/models/vectora_original_trained.pt)) and verified self-contained ONNX FP32 model ([`vectora_original_trained_fp32.onnx`](file:///home/nimr/Projects/mosqscan/models/vectora_original_trained_fp32.onnx)) with **20.35 ms** median CPU inference latency.

---

## 2. Dataset Inspection: `Mosquito Images Original`

Antigravity verified all image files located in [`Mosquito Images Original/Original Images Mendeley`](file:///home/nimr/Projects/mosqscan/Mosquito%20Images%20Original/Original%20Images%20Mendeley).

### Table 1: Dataset Composition and Characteristics

| Genus / Species | Image Count | Proportion | File Size Range | Image Resolutions | Color Mode |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Culex quinquefasciatus** | 20 | 45.45% | 1.84 MB - 2.89 MB | $3000 \times 4000$ (20) | RGB |
| **Aedes aegypti** | 15 | 34.09% | 1.86 MB - 2.87 MB | $3000 \times 4000$ (15) | RGB |
| **Anopheles stephensi** | 9 | 20.45% | 1.05 MB - 2.51 MB | $3000 \times 4000$ (7), $1944 \times 2592$ (2) | RGB |
| **Total** | **44** | **100.00%** | **Mean: 2.22 MB** | **42 (12 MP), 2 (5 MP)** | **100% RGB** |

### Optical and Photographic Analysis
- **Background:** High-contrast off-white entomological cork background.
- **Mean Luminance:** $196.22 \pm 16.01$ (well-illuminated, minimal underexposure or clipping).
- **Mounting:** Specimens are pinned using standard insect pins.
- **Integrity:** Zero corrupted headers, zero truncated bitstreams.

---

## 3. Training Methodology and Hyperparameters

Due to the small sample size ($N=44$), standard unaugmented training causes rapid memorization. Antigravity implemented:

```
+-----------------------------------------------------------------------------+
|             Training Pipeline on 'Mosquito Images Original'                 |
+-----------------------------------------------------------------------------+
                                      |
         +----------------------------+----------------------------+
         |                                                         |
         v                                                         v
  Dynamic Training Augmentation                             Class-Weighted Loss
  - 4x to 6x dynamic views per specimen                    - Aedes weight:     0.9778
  - Random Resized Crop (0.8 - 1.0)                        - Anopheles weight: 1.6296
  - Random Rotation (+/- 15 deg)                           - Culex weight:     0.7333
  - Random Flips (H: 0.5, V: 0.2)                          (Penalizes minority class misses)
  - Color Jitter (Brightness/Contrast)
                                      |
         +----------------------------+
         v
  Two-Stage Transfer Learning (EfficientNet-B0)
  - Stage 1: Linear Probe Head (lr=1e-3, AdamW, weight decay=1e-4)
  - Stage 2: Top Backbone Fine-Tuning (lr_feat=2e-5, lr_head=2e-4)
```

---

## 4. Stratified 4-Fold Cross-Validation Evaluation

Each fold used 33 training specimens with dynamic augmentation and 11 clean, untouched physical photographs for validation.

### Table 2: 4-Fold Stratified Cross-Validation Results

| Fold Index | Val Support (Ae / An / Cx) | Macro-F1 | Balanced Accuracy | Overall Accuracy | Aedes Recall | Anopheles Recall | Culex Recall |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Fold 1** | 4 / 2 / 5 | 0.7554 | 0.7500 | 81.82% (9/11) | 75.00% | 50.00% | 100.00% |
| **Fold 2** | 4 / 2 / 5 | 0.7778 | 0.8333 | 81.82% (9/11) | 50.00% | 100.00% | 100.00% |
| **Fold 3** | 4 / 2 / 5 | 0.7009 | 0.6667 | 72.73% (8/11) | 50.00% | 50.00% | 100.00% |
| **Fold 4** | 3 / 3 / 5 | 0.8857 | 0.8889 | 90.91% (10/11) | 100.00% | 66.67% | 100.00% |
| **Mean $\pm$ SD** | - | **$0.7799 \pm 0.0775$** | **$0.7847 \pm 0.0972$** | **$81.82\%$** (36/44) | **68.75%** | **66.67%** | **100.00%** |

### Cumulative Out-of-Fold Confusion Matrix ($N=44$)

```
                  Predicted Aedes    Predicted Anopheles    Predicted Culex    Total True Specimens
True Aedes              10                    3                    2                   15
True Anopheles           1                    6                    2                    9
True Culex               0                    0                   20                   20
Total Predicted         11                    9                   24                   44
```

- **Culex Performance:** 20 of 20 correct (**100.0% recall**).
- **Aedes Performance:** 10 of 15 correct (**66.7% recall**).
- **Anopheles Performance:** 6 of 9 correct (**66.7% recall**).

---

## 5. Final Model Training and Artifact Export

Antigravity trained the final model on all 44 original photographs using the verified two-stage schedule.

### Table 3: Exported Model Artifacts

| Artifact | File Path | File Size | Checksum (SHA-256) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **PyTorch Checkpoint** | [`models/vectora_original_trained.pt`](file:///home/nimr/Projects/mosqscan/models/vectora_original_trained.pt) | 16.34 MB | `3c06adf10077a3e6f9dc22c3a80cb726aefd7bb7db42728635e08087046390c0` | Saved & Verified |
| **ONNX FP32 Model** | [`models/vectora_original_trained_fp32.onnx`](file:///home/nimr/Projects/mosqscan/models/vectora_original_trained_fp32.onnx) | 16.04 MB | `b40b52c06dfe2c84b66b034354ca7f8244ec84807d2b7fba0da9202f4622d04e` | Exported & Verified |
| **JSON Results** | [`reports/original_dataset_training_results.json`](file:///home/nimr/Projects/mosqscan/reports/original_dataset_training_results.json) | 2.45 KB | - | Saved |

### ONNX Runtime Verification
- **Validation Run:** All 44 physical photographs evaluated through ONNX Runtime C++ engine (`CPUExecutionProvider`).
- **Accuracy:** **100.00%** (44/44 specimens classified correctly).
- **Median Inference Latency:** **20.35 ms** on Intel Core i7-2600 CPU.
- **Model Graph:** Self-contained single-file ONNX with static weights and dynamic batch dimension.

---

## 6. Deployment Notes

The new trained weights are preserved as separate research artifacts:
- The active Docker container continues running the established baseline checkpoint ([`vectora_v3_fp32.onnx`](file:///home/nimr/Projects/mosqscan/models/vectora_v3_fp32.onnx)) to maintain runtime stability.
- If you wish to switch the active Docker inference server to [`vectora_original_trained_fp32.onnx`](file:///home/nimr/Projects/mosqscan/models/vectora_original_trained_fp32.onnx), you can update `ADULT_MODEL_ARTIFACT` in `docker-compose.yml`.
