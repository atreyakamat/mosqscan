# Vectora AI — Release Integrity Audit: Model Consistency & Artifact Lineage

**Document:** `reports/v2-model-consistency.md`  
**Date:** November 11, 2026  
**Auditor:** Senior AI Architect & Security Engineer  
**Status:** AUDIT COMPLETE — RELEASE BLOCKER IDENTIFIED (`BLK-MODEL-01`)

---

## 1. Executive Summary

This audit establishes the exact lineage, mathematical equivalence, and runtime behavior of all deep learning model artifacts across the Vectora AI workspace. 

### Key Findings
1. **Different Model Weights:** The currently deployed models (`efficientnet_b0.onnx`, SHA-256 `03fc58fd...` and `efficientnet_b0_int8.onnx`, SHA-256 `bac40d9a...`) are **NOT re-exports of Exp B**. They are derived from the initial frozen-backbone baseline (`efficientnet_b0_best.pt`), whereas Exp B (`exp_B_unfreeze_stage7_8_best.pt`) has different convolutional weights across stages 7 and 8.
2. **Artifact Discrepancy:** The model registry manifest lists Exp B artifacts (`d644b9cd...` and `6d7e8306...`) as candidate artifacts, but both the backend default configuration and the Android bundled assets run the baseline checkpoint (`03fc58fd...` and `bac40d9a...`).
3. **Threshold Calibration Myth:** All confidence thresholds (`0.40`, `0.50`, `0.65`) are **heuristic boundaries on uncalibrated raw softmax scores**. None are statistically calibrated probabilities.
4. **Extreme Threshold Sensitivity:** On testing ground-truth specimens, top softmax confidences for all models range between **0.35 and 0.50**. At the documented `0.65` threshold, **100% of specimens are rejected as uncertain**.
5. **INT8 Quantization Drift:** Dynamic INT8 quantization causes probability shifts of up to **0.149** (14.9%) and flips the argmax predicted genus on ambiguous specimens.

---

## 2. Artifact Lineage & Checksum Audit

Every `.pt` and `.onnx` file across the workspace was hashed using SHA-256 and mapped to its training provenance:

| Model Artifact File | File Size | SHA-256 Checksum | Training Provenance |
|---|---|---|---|
| `vectora-ai-starter/models/efficientnet_b0_best.pt` | 16,344,133 bytes | `09c7c5702cf1a7840f2c9bda06d4df9215b47e01cef0b133437f60ddb657b2d5` | Baseline training (Epoch 3, val F1: 0.6000, frozen feature extractor) |
| `vectora-ai-starter/models/efficientnet_b0.onnx` | 16,035,557 bytes | `03fc58fd99578b756415ca50a8cc8b702e7e98ad248cfe0215f836e1652b0d19` | Direct FP32 export of `efficientnet_b0_best.pt` |
| `vectora-ai-starter/models/efficientnet_b0_int8.onnx` | 4,360,533 bytes | `bac40d9af5441ddbdb6c6b19348fe04167ca4d8de7466611742022b7f505bd95` | Dynamic INT8 quantization of `efficientnet_b0.onnx` |
| `android/app/src/main/assets/efficientnet_b0_int8.onnx` | 4,360,533 bytes | `bac40d9af5441ddbdb6c6b19348fe04167ca4d8de7466611742022b7f505bd95` | **Identical bit-for-bit copy** of Baseline INT8 |
| `vectora-ai-starter/experiments/exp_B_unfreeze_stage7_8_best.pt` | 16,347,189 bytes | `7b7f122cc275ba9daeb6d13c80156353054dadd22960b60c82a96bee6e00fe5f` | Exp B fine-tuning (Epoch 2, val F1: 0.6190, unfreeze stages 7–8) |
| `models/vectora_candidate_exp_b.onnx` | 16,035,577 bytes | `d644b9cd9c952d461bbfbb44e8b1926cdcf9bbbfb9cd43f85065cbed0d7b1499` | Direct FP32 export of `exp_B_unfreeze_stage7_8_best.pt` |
| `models/vectora_candidate_exp_b_int8.onnx` | 4,362,942 bytes | `6d7e830699f4ca3f3b67c538c2f77a592f88288845dfa00d94c7837ccef68803` | Dynamic INT8 quantization of `vectora_candidate_exp_b.onnx` |

### Checkpoint Mathematical Comparison
Inspection of model state dictionaries confirms different internal weights:
- **`efficientnet_b0_best.pt`:** `classifier.1.weight` L2 norm = `1.032325`, `classifier.1.bias` = `[0.01170, -0.01270, -0.00475]`. Features stages 0–8 are identical to ImageNet default.
- **`exp_B_unfreeze_stage7_8_best.pt`:** `classifier.1.weight` L2 norm = `0.996122`, `classifier.1.bias` = `[0.01087, -0.01206, -0.00449]`. Convolutional filters in blocks `features[7]` and `features[8]` are updated via backpropagation.

Max absolute logit difference between Baseline FP32 and Exp B FP32 on normalized input: **`0.0566`**. They are **mathematically distinct neural networks**.

---

## 3. Platform Deployment Reconciliation

| Platform / Config | Configured Artifact | Deployed SHA-256 Checksum | Lineage Origin |
|---|---|---|---|
| **Backend API (`app/config.py`)** | `efficientnet_b0.onnx` | `03fc58fd99578b756415ca50a8cc8b702e7e98ad248cfe0215f836e1652b0d19` | Baseline FP32 |
| **Android APK (`OnnxAdultClassifier.kt`)** | `efficientnet_b0_int8.onnx` | `bac40d9af5441ddbdb6c6b19348fe04167ca4d8de7466611742022b7f505bd95` | Baseline INT8 |
| **Model Registry (`manifest.json`)** | Primary: `efficientnet_b0.onnx`<br>Candidate: `vectora_candidate_exp_b.onnx` | `03fc58fd...` / `bac40d9a...`<br>`d644b9cd...` / `6d7e8306...` | Documents both |
| **Release Docker Compose (`docker-compose.yml`)** | `efficientnet_b0.onnx` (overridden in compose env) | `03fc58fd...` | Baseline FP32 |

### Audit Finding
The backend and Android applications **are currently in perfect parity with each other** because both execute the Baseline model lineage (`03fc58fd...` on backend, `bac40d9a...` on Android). However, neither executes the proposed Exp B model weights (`d644b9cd...` / `6d7e8306...`). 

> [!IMPORTANT]
> Do NOT replace the deployed baseline artifacts with Exp B without a formal promotion procedure. Promoting Exp B requires simultaneously replacing both the backend FP32 ONNX file and the Android APK asset file, followed by re-running model parity integration tests.

---

## 4. Empirical Prediction Comparisons

To evaluate the operational differences, 6 reference images across all three target genera were processed through all 4 model variants using standard preprocessing:

```
Input: 224x224 RGB, Bilinear interpolation
Normalization: Mean [0.485, 0.456, 0.406], Std [0.229, 0.224, 0.225]
Softmax Order: [0: aedes, 1: anopheles, 2: culex]
```

### Empirical Results Table

| Specimen Image | Ground Truth | Baseline FP32 (`03fc...`) | Baseline INT8 (`bac4...`) | Candidate Exp B FP32 (`d644...`) | Candidate Exp B INT8 (`6d7e...`) |
|---|---|---|---|---|---|
| `Aedes_aegypti_1.jpg` | *Aedes* | **Aedes (50.1%)** | **Aedes (40.0%)** | **Aedes (44.2%)** | **Aedes (38.6%)** |
| `Anopheles_stephensi_1.jpg` | *Anopheles* | Culex (45.8%) ❌ | **Anopheles (36.8%)** ✅ | Culex (50.5%) ❌ | **Anopheles (40.4%)** ✅ |
| `Culex_quinquefasciatus_1.jpg` | *Culex* | Aedes (40.8%) ❌ | **Culex (40.0%)** ✅ | Aedes (38.4%) ❌ | Aedes (35.7%) ❌ |
| `Aedes_aegypti_10.jpg` | *Aedes* | **Aedes (41.7%)** | **Aedes (36.0%)** | **Aedes (41.2%)** | Anopheles (38.9%) ❌ |
| `Anopheles_stephensi_5.jpg` | *Anopheles* | Aedes (40.5%) ❌ | **Anopheles (36.2%)** ✅ | Culex (38.9%) ❌ | **Anopheles (39.7%)** ✅ |
| `Culex_quinquefasciatus_10.jpg` | *Culex* | **Culex (44.1%)** | Aedes (36.2%) ❌ | **Culex (41.7%)** | Anopheles (36.7%) ❌ |

### Critical Observations
1. **Low Baseline Probabilities:** On freshly collected museum-grade adult specimens, the highest single class probability across all specimens was **50.5%**. Because the model was trained on only 44 images with frozen initial layers, the logit dynamic range is narrow ($[-0.4, +0.4]$).
2. **Quantization Argmax Flipping:**
   - On `Anopheles_stephensi_1.jpg`, FP32 predicts *Culex* (45.8%), but INT8 quantization shifts logits sufficiently to predict *Anopheles* (36.8%).
   - On `Culex_quinquefasciatus_10.jpg`, FP32 correctly predicts *Culex* (44.1%), but INT8 predicts *Aedes* (36.2%).
3. **The 0.65 Threshold Fallback:**
   - At a 0.65 threshold, **all 6 predictions above are flagged as `is_uncertain: true`**.
   - This prevents false identifications from being displayed to users, but also means zero valid field identifications will be displayed without retraining.

---

## 5. Confidence Threshold Reconciliation

The repository contained multiple conflicting threshold values across different files:
- **`0.65`:** In `backend/app/inference/adult_classifier.py`, `android/app/.../OnnxAdultClassifier.kt`, `web/src/app/adult/page.tsx`, and `docs/architecture.md`.
- **`0.50`:** In `model-registry/manifest.json` and `backend/.env.example`.
- **`0.40`:** In `reports/backend-implementation-report.md` (average correct confidence).

### Reconciliation Decision
1. **Authoritative Standard Threshold:** **`0.65`** is the established safety threshold for production-grade identification. Any prediction with confidence $< 0.65$ MUST return `"Uncertain identification. Manual inspection is advised."`
2. **Do Not Claim Calibration:** The text in `web/src/app/page.tsx` claiming *"calibrated confidence thresholds"* is false and must be amended to *"experimental uncertainty threshold"*. The scores are raw softmax probabilities and have not undergone temperature scaling or isotonic regression.
3. **Manifest Alignment:** `model-registry/manifest.json` must be updated from `0.50` to `0.65` to prevent drift across services.

---

## 6. Model Integration Gate Verdict

| Condition | Status | Detail |
|---|---|---|
| Artifact Lineage Established | **PASS** | `03fc58fd` = Baseline FP32; `bac40d9a` = Baseline INT8; `d644b9cd` = Exp B FP32; `6d7e8306` = Exp B INT8 |
| Backend & Mobile Pair Parity | **PASS** | Both platforms deploy the Baseline artifact pair with identical class mapping and normalization |
| Candidate Promotion Ready | **BLOCKED** | Exp B cannot be deployed until simultaneous dual-platform artifact update and test validation occur |
| Safety & Uncertainty Gating | **PASS** | 0.65 threshold safely marks low-confidence inferences as uncertain |
