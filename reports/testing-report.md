# Vectora AI — Testing and Baseline Validation Report

**Date:** 2026-11-11  
**Auditor:** Senior Software Quality & ML Test Engineer (Antigravity)  

---

## 1. Test Execution Summary

| Test Domain | Target | Command Executed | Result | Duration |
|---|---|---|---|---|
| **Environment Check** | Python / CPU / PyTorch | `python scripts/check_env.py` | **PASS** | 2.1 s |
| **Split Disjointness** | Specimen Isolation | `python -c "import tests.test_split_groups..."` | **PASS** | 0.4 s |
| **Complete ML Pipeline**| 13-stage ML lifecycle | `python tests/test_ml_pipeline.py` | **PASS** | 7.8 s |
| **OpenCV Vision Test** | Image decode / transform | `python -c "import cv2; ..."` | **PASS** | 0.8 s |
| **ONNX Export Test** | PyTorch to ONNX FP32 | `torch.onnx.export(..., dynamo=False)` | **PASS** | 4.2 s |
| **ONNX Quantization** | Dynamic INT8 conversion | `onnxruntime.quantization.quantize_dynamic` | **PASS** | 1.1 s |
| **ONNX Runtime CPU** | Inference Session | `ort.InferenceSession.run()` | **PASS** | 1.4 s |
| **Original Baseline** | 44 original photographs | `python scripts/test_model_detailed.py` | **PASS** | 14.8 s |
| **Augmented Benchmark**| 2,640 augmented images | `python scripts/test_full_dataset.py` | **PASS** | 154.9 s |
| **Android ADB Device** | Hardware Device Bridge | `adb devices` | **NO DEVICE** | 0.1 s |

---

## 2. End-to-End Machine Learning Pipeline Test (13-Stage Verification)

Executed in [`tests/test_ml_pipeline.py`](file:///home/nimr/Projects/mosqscan/vectora-ai-starter/tests/test_ml_pipeline.py):

```text
[1/13] Dataset loading: PASS
[2/13] Label mapping (CLASS_TO_IDX): PASS
[3/13] Image preprocessing (build_transforms): PASS
[4/13] Batch generation (DataLoader batch_size=2): PASS
[5/13] Model initialization (EfficientNet-B0): PASS
[6/13] Forward propagation (shape [2, 3]): PASS
[7/13] Loss calculation (CrossEntropyLoss=1.1981): PASS
[8/13] Backpropagation (gradients computed): PASS
[9/13] Optimizer execution (AdamW weight update): PASS
[10/13] Checkpoint saving (models/temp.pt, 15.58 MB): PASS
[11/13] Checkpoint loading (state dict restoration): PASS
[12/13] Evaluation execution (evaluate function): PASS
[13/13] Prediction output (softmax probabilities sum to 1.0): PASS
```

---

## 3. Training Smoke-Test Results

Executed baseline training with:
```bash
python -m vectora.train --epochs 8 --batch-size 8 --image-size 224 --threads 3
```
* **Dataset:** 32 train images, 6 validation images.
* **Backbone:** EfficientNet-B0 (pretrained on ImageNet, feature backbone frozen).
* **Optimizer:** AdamW (`lr=1e-3`, `weight_decay=1e-4`).
* **Elapsed Time:** 53.7 seconds on 3 CPU threads.
* **Epoch-by-Epoch Convergence:**

| Epoch | Train Loss | Validation Loss | Validation Accuracy | Validation Macro-F1 | Best Checkpoint |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | 1.1060 | 1.0396 | 50.0% | 0.3333 | Saved |
| 2 | 0.9543 | 1.0125 | 50.0% | 0.4000 | Saved |
| 3 | 0.9276 | 0.9017 | 83.3% | 0.6000 | Saved |
| 4 | 0.8404 | 0.7426 | 83.3% | 0.6000 | Stale (1/3) |
| 5 | 0.7396 | 0.6806 | 83.3% | 0.6000 | Stale (2/3) |
| 6 | 0.7647 | 0.6223 | 83.3% | 0.6000 | Stale (3/3) |
* **Early Stopping Triggered:** Epoch 6 (no F1 improvement for 3 consecutive epochs).

---

## 4. Inference & Evaluation Results

### A. Original Dataset Benchmark (44 Images)
* **Overall Accuracy:** **70.45%** (31 / 44 images correct)
* **Macro-F1 Score:** **0.5823**

```text
Confusion Matrix (44 Original Photographs):
                Pred aedes  Pred anopheles  Pred culex    Recall
True aedes              15               0           0    100.0%
True anopheles           7               1           1     11.1%
True culex               4               1          15     75.0%
Precision            57.7%           50.0%       93.8%
```

### B. Augmented Dataset Benchmark (2,640 Images)
* **Overall Accuracy:** **62.73%** (1,656 / 2,640 images correct)
* **Macro-F1 Score:** **0.5542**

```text
Per-Class Metrics (Augmented 2,640 Images):
Genus           Precision    Recall    F1-Score    Support
Aedes             0.520      0.824      0.637        900
Anopheles         0.357      0.206      0.261        540
Culex             0.891      0.669      0.764       1200
```

---

## 5. Performance & Resource Benchmarks

All benchmarks performed on the `Intel(R) Core(TM) i7-2600 CPU @ 3.40GHz`:

| Metric | Target (PRD) | Measured Value (Desktop i7-2600) | Compliance |
|---|---|---|---|
| **FP32 Model Size** | ≤ 45 MB | **15.29 MB** | **COMPLIANT** |
| **INT8 Quantized Size** | ≤ 45 MB | **4.16 MB** | **COMPLIANT** |
| **FP32 Inference Latency** | ≤ 300–350 ms | **14.21 ms** | **COMPLIANT** |
| **INT8 Inference Latency** | ≤ 300–350 ms | **58.79 ms** | **COMPLIANT** |
| **CPU Training Time (6 epochs)**| N/A | **53.7 s** | Extremely fast on CPU |
| **Peak RAM Consumption** | < 15 GB | **~600 MB** resident | Well within memory limits |
