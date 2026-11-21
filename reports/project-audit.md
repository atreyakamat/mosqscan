# Vectora AI — Project Audit Report

**Date:** 2026-11-11  
**Auditor:** Senior ML / Computer Vision / Android Engineer (Antigravity)  
**Workspace:** `/home/nimr/Projects/mosqscan/vectora-ai-starter`  

---

## 1. Project Structure

The project currently resides at `/home/nimr/Projects/mosqscan/vectora-ai-starter`:

```text
vectora-ai-starter/
├── configs/
│   └── baseline.yaml                     # Training configuration (classes, epochs, batch_size, lr)
├── data/
│   ├── metadata.csv                      # Manifest of indexed raw images with provenance
│   ├── metadata_template.csv             # Template defining required manifest schema
│   ├── splits.csv                        # Group-disjoint train/val/test splits
│   └── raw/
│       ├── aedes/                        # 15 original Aedes aegypti photographs
│       ├── anopheles/                    # 9 original Anopheles stephensi photographs
│       ├── culex/                        # 20 original Culex quinquefasciatus photographs
│       └── non_mosquito/                 # Negative class directory (currently empty)
├── models/
│   ├── efficientnet_b0_best.pt           # PyTorch checkpoint (trained baseline weights)
│   ├── efficientnet_b0.onnx              # Exported ONNX FP32 model (15.29 MB)
│   └── efficientnet_b0_int8.onnx         # Dynamically quantized INT8 model (4.16 MB)
├── reports/                              # Audit and testing documentation
├── results/
│   ├── comprehensive_test_results.json   # Per-image testing results on 44 original + 60 sample augmented
│   ├── confusion_matrix.csv              # Test split confusion matrix
│   ├── full_test_report.json             # Exhaustive test results across all 44 original + 2,640 augmented
│   ├── test_metrics.json                 # Classification report JSON on test split
│   └── training_history.csv              # Epoch-by-epoch loss, val accuracy and macro-F1
├── scripts/
│   ├── check_env.py                      # CPU environment and PyTorch smoke checker
│   ├── make_manifest.py                  # Ingests raw images into metadata.csv
│   ├── split_dataset.py                  # Specimen-level disjoint splitting
│   ├── test_model_detailed.py            # Detailed evaluation script
│   └── test_full_dataset.py              # Full 2,640-image evaluation pipeline
├── src/
│   └── vectora/
│       ├── __init__.py
│       ├── data.py                       # PyTorch Dataset and transforms definition
│       ├── evaluate.py                   # Checkpoint evaluation script
│       ├── model.py                      # EfficientNet-B0 transfer learning definition
│       ├── predict.py                    # Single-image inference CLI
│       └── train.py                      # CPU training loop with early stopping
├── tests/
│   ├── test_split_groups.py              # Group disjointness split unit test
│   └── test_ml_pipeline.py               # 13-step complete ML pipeline test
├── pyproject.toml                        # Package build definition (pip install -e .)
├── README.md                             # Research baseline documentation
└── requirements.txt                      # Python dependencies
```

---

## 2. Architecture & Component Status Matrix

| Component | Existing Implementation | Status | Issues & Limitations |
|---|---|---|---|
| **Dataset Pipeline** | `scripts/make_manifest.py`, `scripts/split_dataset.py`, `vectora.data.MosquitoDataset` | **Working** | Currently handles 44 original photographs; augmented dataset requires strict specimen ID tracking before ingestion. |
| **Image Preprocessing** | `torchvision.transforms` (Resize 224x224, Normalization, Data Augmentations) | **Working** | Basic image resize & augmentations working. Morphological specimen isolation and crop not yet implemented. |
| **Adult Detection** | None (PRD proposes YOLOv11n) | **Missing** | Current pipeline assumes image is pre-cropped or macro centered on the mosquito specimen. |
| **Adult Classification** | EfficientNet-B0 with customized 3-class linear head | **Working** | Working baseline (70.5% accuracy on originals). Feature backbone was frozen; fine-tuning needed for Anopheles. |
| **Larvae Pipeline** | None (PRD proposes video meniscus extraction & tracking) | **Missing** | No video frame extractor or larvae kinematic analysis implemented yet. |
| **Model Training** | `vectora.train` with AdamW, early stopping, CrossEntropy | **Working** | CPU-optimized training runs cleanly in 53s on i7-2600. |
| **Model Evaluation** | `vectora.evaluate`, `test_full_dataset.py` | **Working** | Confusion matrix, Macro-F1, Precision/Recall, and calibration confidence evaluation functional. |
| **ONNX Conversion** | Exported via `torch.onnx.export` + dynamic INT8 quantization | **Working** | FP32 (15.29 MB) and INT8 (4.16 MB) successfully exported and verified with `onnxruntime`. |
| **Android Application** | None in current repo | **Missing** | Android app scaffold (Kotlin / Jetpack Compose / CameraX) has not yet been initialized. |
| **CameraX Integration** | None in current repo | **Missing** | Pending Android application initialization. |
| **Offline Inference** | ONNX Runtime CPU execution provider verified locally | **Ready for App** | Validated on desktop CPU (14.2 ms FP32 / 58.8 ms INT8). Ready for ONNX Runtime Mobile integration. |

---

## 3. Existing vs Missing Functionality

### Working Functionality
1. **Proven CPU Training & Verification Pipeline:** Fully automated data ingestion, group-aware splitting, training, checkpointing, and evaluation.
2. **Proven ONNX Export & INT8 Quantization:** PyTorch models convert smoothly to ONNX and run with ONNX Runtime CPU. Both FP32 and INT8 models meet the PRD footprint constraint (< 45 MB).
3. **Reproducible Test Coverage:** Unit test for specimen grouping (`tests/test_split_groups.py`) and 13-stage end-to-end ML test (`tests/test_ml_pipeline.py`).
4. **Dataset Validation:** 44 high-resolution original photographs and 2,640 augmented images fully evaluated with detailed failure analysis.

### Missing Functionality
1. **Adult Mosquito Detector (YOLOv11n):** No bounding box detection or specimen localization model exists yet.
2. **Out-of-Distribution / Rejection Head:** No rejection class or calibrated uncertainty threshold for non-mosquito insects or invalid images.
3. **Larvae Video Pipeline:** Frame extraction, water-meniscus detection, kinematic posture estimation, and multi-object tracking are not yet built.
4. **Android Client Application:** No Android project repository with Jetpack Compose or CameraX exists in this workspace.

---

## 4. Critical Problems Identified

1. **Class Imbalance & Underrepresentation of *Anopheles* (Severity: P1):**
   * Only 9 original *Anopheles* photographs exist in the Mendeley dataset (compared to 15 Aedes and 20 Culex).
   * In training, only 7 *Anopheles* specimens were available, leading to an 11.1% recall on original images.
2. **Lack of Calibrated Confidence (Severity: P2):**
   * The average softmax probability for correct predictions was 43.7%, while for incorrect predictions it was 39.8%. A naive threshold cannot reliably distinguish correct from incorrect identifications.
3. **Synthetic Duplicate Leakage in External Datasets (Severity: P2):**
   * An audit of the auxiliary `mosquito-dataset-for-classification-cnn.zip` revealed that 1,919 out of 3,000 images (64%) are exact bit-for-bit duplicate copies (Culex has only 40 unique images repeated 960 times). It must not be mixed into the pipeline without deduplication.
4. **Missing Android Scaffold (Severity: P3):**
   * While the Android SDK is installed on the host machine (`/home/nimr/Android/Sdk`), no Android Gradle codebase has been initialized for Vectora AI yet.
