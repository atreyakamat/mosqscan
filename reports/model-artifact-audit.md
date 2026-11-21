# Vectora AI — Model Artifact Audit & Parameter-Level Comparison

**Audit Date:** November 11, 2026  
**Auditor:** Vectora AI Machine Learning & Computer Vision Engineering  
**Scope:** Checkpoint integrity verification, parameter-level differential audit, probability divergence analysis, and provisional candidate selection.

---

## 1. Executive Summary

This audit validates all five fine-tuning experiment checkpoints produced during the controlled training phase of the Vectora AI adult mosquito classifier. We perform an exhaustive cryptographic, structural, and empirical analysis to:
1. Cryptographically verify and record each checkpoint's binary properties, parameter counts, and evaluation metrics.
2. Mathematically compare **Exp B vs. Exp C** and **Exp B-Weighted vs. Exp C-Weighted** to resolve why both pairs produced identical discrete validation and test metrics.
3. Select a provisional research candidate using **validation metrics only**, adhering strictly to the anti-data-leakage policy.
4. Establish the operational parameters for mobile quantization and product deployment.

---

## 2. Checkpoint Verification Matrix

All checkpoints were loaded and verified using PyTorch 2.5.1 on the Omarchy Linux development platform. SHA-256 digests were computed directly from disk bytes.

| Experiment ID | Checkpoint File | File Size (Bytes) | SHA-256 Checksum | Trainable Params | Trainable % | Loss Weights | Best Val Macro-F1 | Held-out Test Macro-F1 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Exp A** (Frozen Baseline) | `exp_A_frozen_baseline_best.pt` | 16,346,457 | `b7a1022c2c29256cee426d398513234fadb80fe3864b86037fc8abbb6b955140` | 3,843 | 0.10% | None | 0.6000 | 1.0000 |
| **Exp B** (Stage 7–8) | `exp_B_unfreeze_stage7_8_best.pt` | 16,347,189 | `7b7f122cc275ba9daeb6d13c80156353054dadd22960b60c82a96bee6e00fe5f` | 1,133,235 | 28.25% | None | **0.6190** | 0.6000 |
| **Exp C** (Stages 5–8) | `exp_C_unfreeze_stages5_8_best.pt` | 16,347,555 | `9faf5ecdd35322119f1c7cf01ec7ac80694cd43801670515679c51db023bed00` | 3,702,731 | 92.31% | None | **0.6190** | 0.6000 |
| **Exp B-Weighted** | `exp_B_weighted_stage7_8_best.pt` | 16,347,189 | `e2b1bfb4fb82a85c780d339a3012b563a3b4f4088cd6555a7eb39c69f20abb40` | 1,133,235 | 28.25% | Training Only | 0.6000 | 0.8222 |
| **Exp C-Weighted** | `exp_C_weighted_stages5_8_best.pt` | 16,347,555 | `54c00b77efbd34036d47aa5e370ee41b5bb150f52eab924c25e78bc8b326078e` | 3,702,731 | 92.31% | Training Only | 0.6000 | 0.8222 |

*Note: Baseline reference checkpoint `models/efficientnet_b0_best.pt` (SHA-256: `09c7c5702cf1a7840f2c9bda06d4df9215b47e01cef0b133437f60ddb657b2d5`, 16,344,133 bytes) remains preserved and unmodified.*

---

## 3. Deep Model Comparison: Exp B vs Exp C & Weighted Counterparts

In the previous evaluation audit, Exp B and Exp C produced identical discrete metrics on both validation (Macro-F1 = 0.6190) and test (Macro-F1 = 0.6000). Similarly, Exp B-Weighted and Exp C-Weighted yielded identical metrics (Val Macro-F1 = 0.6000, Test Macro-F1 = 0.8222).

To resolve whether this identity stems from model cloning or identical discrete classification from divergent continuous probability spaces, we performed tensor-level and inference-level differential audits.

### 3.1 State Dictionary & Parameter Divergence

Comparing the state dictionaries across all 360 parameter tensors:

| Comparison Metric | Exp B vs Exp C | Exp B-Weighted vs Exp C-Weighted |
| :--- | :--- | :--- |
| **Total Model Tensors** | 360 | 360 |
| **Identical Tensors** | 201 (Stages 0–4 + Conv Head) | 201 (Stages 0–4 + Conv Head) |
| **Differing Tensors** | **159** | **159** |
| **L2 Norm Parameter Distance ($\|\theta_1 - \theta_2\|_2$)** | **3.1971** | **6.4608** |
| **Maximum Parameter Absolute Difference** | **0.3124** | **0.6050** |
| **Divergent Architecture Blocks** | `features.5`, `features.6`, `features.7`, `features.8`, `classifier.1` | `features.5`, `features.6`, `features.7`, `features.8`, `classifier.1` |

**Verification Confirmation:**  
The checkpoints are **not clones**. The 159 differing tensors correspond exactly to the layers unfrozen in Exp C (`features.5`, `features.6`) which remained frozen in Exp B, plus the cascading gradient updates transmitted into `features.7`, `features.8`, and `classifier.1`.

---

### 3.2 Continuous Probability Divergence & Discrete Label Agreement

We performed full inference passes across all 44 specimens in the Mendeley Data v4 dataset using both models and evaluated continuous Softmax probability divergences and discrete label agreement.

#### Exp B vs Exp C (Unweighted)
- **Training Set (N=32):**
  - Label Agreement: **100.0%** (32 / 32)
  - Mean Softmax Absolute Difference: **0.001555** (0.16%)
  - Max Softmax Absolute Difference: **0.006197** (0.62%)
- **Validation Set (N=6):**
  - Label Agreement: **100.0%** (6 / 6)
  - Mean Softmax Absolute Difference: **0.001826** (0.18%)
  - Max Softmax Absolute Difference: **0.004984** (0.50%)
- **Held-Out Test Set (N=6):**
  - Label Agreement: **100.0%** (6 / 6)
  - Mean Softmax Absolute Difference: **0.001490** (0.15%)
  - Max Softmax Absolute Difference: **0.004018** (0.40%)
- **All Combined (N=44):**
  - Label Agreement: **100.0%** (44 / 44)
  - Mean Softmax Absolute Difference: **0.001583**
  - Max Softmax Absolute Difference: **0.006197**

#### Exp B-Weighted vs Exp C-Weighted
- **Training Set (N=32):**
  - Label Agreement: **100.0%** (32 / 32)
  - Mean Softmax Absolute Difference: **0.005577** (0.56%)
  - Max Softmax Absolute Difference: **0.024448** (2.44%)
- **Validation Set (N=6):**
  - Label Agreement: **100.0%** (6 / 6)
  - Mean Softmax Absolute Difference: **0.004977** (0.50%)
  - Max Softmax Absolute Difference: **0.014920** (1.49%)
- **Held-Out Test Set (N=6):**
  - Label Agreement: **100.0%** (6 / 6)
  - Mean Softmax Absolute Difference: **0.003934** (0.39%)
  - Max Softmax Absolute Difference: **0.013893** (1.39%)
- **All Combined (N=44):**
  - Label Agreement: **100.0%** (44 / 44)
  - Mean Softmax Absolute Difference: **0.005271**
  - Max Softmax Absolute Difference: **0.024448**

---

### 3.3 Root-Cause Analysis: Why Reported Metrics Were Identical

The mathematical root cause for identical metrics across Exp B and Exp C is twofold:
1. **Conservative Backbone Learning Rate ($10^{-5}$):**  
   The backbone learning rate was chosen conservatively to prevent catastrophic forgetting. Over the course of 2 training epochs before early stopping, the gradient updates to stages 5 and 6 shifted logits by small deltas ($\Delta \text{logit} < 0.08$).
2. **Margin Separation Exceeded Probability Shifts:**  
   For every specimen $i \in \{1, \dots, 44\}$, the top-1 predicted logit was separated from the runner-up logit by a margin $\delta_i > 0.15$. Because the maximum probability shift induced by unfreezing stages 5–6 was at most $0.0062$ (Exp B vs C) and $0.0244$ (Weighted pair), no sample came close enough to a decision threshold to alter its argmax label.

**Conclusion:** Identical discrete metrics result from distinct underlying continuous probability models that produce 100% identical argmax classifications across the 44 specimens.

---

## 4. Provisional Research Candidate Selection

### 4.1 Selection Methodology (Validation Only)
Under strict machine learning engineering standards:
- Selection must be driven **solely by the validation partition**.
- Held-out test performance must never be used to choose hyperparameters or candidates.

### 4.2 Candidate Comparison: Exp B vs. Exp C vs. Baseline

| Evaluation Criteria | Exp A (Baseline) | Exp B (Stage 7–8) | Exp C (Stage 5–8) | Weighted Variants |
| :--- | :--- | :--- | :--- | :--- |
| **Validation Macro-F1** | 0.6000 | **0.6190** | **0.6190** | 0.6000 |
| **Validation Aedes F1** | 0.8000 | **1.0000** | **1.0000** | 0.8000 |
| **Validation Culex F1** | 1.0000 | 0.8571 | 0.8571 | 1.0000 |
| **Validation Anopheles F1** | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **Trainable Parameter Count** | 3,843 | **1,133,235** (28.25%) | 3,702,731 (92.31%) | 1.13M / 3.70M |
| **Overfitting Risk** | Minimal | **Low** | High | Low / High |
| **Occam's Razor Compliance** | N/A | **Superior** | Inferior | Inferior |

### 4.3 Selection Decision: Exp B
**Selected Model:** `experiments/exp_B_unfreeze_stage7_8_best.pt`  
**Provisional Research Identifier:** `vectora-efficientnet-b0-exp-b`

**Justification:**
1. Exp B ties Exp C for the highest validation macro-F1 (0.6190 vs 0.6000 baseline) and achieves 100% precision and recall on Aedes in validation.
2. Exp B requires training only **1.13M parameters** compared to **3.70M parameters** for Exp C. By Occam's razor, the model with lower complexity that achieves identical generalization performance is strongly favored, especially on small sample regimes where overparameterization risks latent over-fitting.
3. Exp B-Weighted and Exp C-Weighted both underperformed on validation macro-F1 (0.6000), confirming that class weighting without synthetic oversampling penalized majority class boundary margins on this validation split.

---

## 5. Artifact Production & Export Status

To enable cross-platform execution on Android CameraX and Web backends, Exp B was converted to standard Open Neural Network Exchange (ONNX) formats:

1. **Full-Precision ONNX (FP32):**
   - Path: `models/vectora_candidate_exp_b.onnx`
   - Size: 16,035,577 bytes (~16.0 MB)
   - SHA-256: `d644b9cd9c952d461bbfbb44e8b1926cdcf9bbbfb9cd43f85065cbed0d7b1499`
   - Opset: ONNX 18
   - Target: Cloud inference, Web / Node.js runtime, desktop CPU.

2. **Quantized ONNX (INT8):**
   - Path: `models/vectora_candidate_exp_b_int8.onnx`
   - Size: 4,362,942 bytes (~4.16 MB)
   - SHA-256: `6d7e830699f4ca3f3b67c538c2f77a592f88288845dfa00d94c7837ccef68803`
   - Quantization Method: Symmetric dynamic integer quantization (`QDQ` / ONNX Quantizer)
   - Target: Android ONNX Runtime Mobile, edge embedded devices.
   - Compliance: Meets PRD specification ($\le 45\text{ MB}$, actual: 4.16 MB).

---

## 6. Regulatory & Field Validation Disclaimer

> [!CAUTION]
> **EXPERIMENTAL ARTIFACT — NOT VALIDATED FOR FIELD DEPLOYMENT**  
> Candidate `vectora-efficientnet-b0-exp-b` is an intermediate research checkpoint trained on 44 original mosquito specimens. Neither Exp B nor any current checkpoint satisfies the PRD's 92% macro-F1 acceptance criterion under multi-source evaluation. This artifact is strictly intended for software integration testing, mobile CameraX harness validation, and UI pipeline development. It must not be deployed for autonomous epidemiological field surveillance without training on a multi-site dataset with entomological confirmation.
