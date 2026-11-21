# Vectora AI — Confidence-Gating Terminology Correction and Extended Model Release Decision

**Deliverable:** Extended Model Audit Deliverable 5 of 5  
**Target:** Confidence-Gating Terminology Correction and Final Release Governance Decision  
**Evaluator:** Independent ML Quality & Evaluation Audit  
**Date:** 2026-11-13  
**Final Extended Model Status:** `VALIDATION_INCOMPLETE`  
**Operational Action:** DO NOT PROMOTE TO PRODUCTION · MAINTAIN ACTIVE PRODUCTION V3 FP32 MODEL  

---

## 1. Executive Summary

This deliverable provides two essential governance decisions for Vectora AI:
1. **Correction of Confidence-Gating Terminology:** A rigorous mathematical and conceptual correction distinguishing Maximum Softmax Probability from Predictive Entropy, refuting claims that fixed thresholds eliminate confidently incorrect predictions.
2. **Formal Audit Determination for the Extended Eight-Epoch Model:** A definitive release gate determination based on the findings from Deliverables 1 through 4.

The final audit status for [`models/vectora_extended_best.pt`](file:///home/nimr/Projects/mosqscan/models/vectora_extended_best.pt) / [`models/vectora_extended_fp32.onnx`](file:///home/nimr/Projects/mosqscan/models/vectora_extended_fp32.onnx) is formally designated as:

$$\mathbf{VALIDATION\_INCOMPLETE}$$

The model is withheld from production. The existing active production model ([`models/vectora_v3_fp32.onnx`](file:///home/nimr/Projects/mosqscan/models/vectora_v3_fp32.onnx), SHA-256 `c3a3656f...`) remains untouched and continues serving production traffic.

---

## 2. Confidence-Gating Terminology Correction

Section D of the audit mandate requires establishing precise mathematical terminology for confidence estimation and model gating.

### A. Mathematical Formulation: Maximum Softmax Probability (MSP)
Given a model output logit vector $z = [z_1, z_2, \dots, z_K]^T \in \mathbb{R}^K$, the softmax transformation produces a categorical probability distribution $p = \sigma(z) \in \Delta^{K-1}$:

$$p_k = \frac{e^{z_k}}{\sum_{j=1}^K e^{z_j}}, \quad k \in \{1, \dots, K\}$$

The Maximum Softmax Probability (MSP) is defined as:

$$\text{MSP}(x) = \max_{k \in \{1, \dots, K\}} p_k(x)$$

MSP represents the point estimate of the peak of the normalized distribution. It measures only the single highest probability relative to the normalization sum.

---

### B. Mathematical Formulation: Predictive Shannon Entropy
Predictive entropy measures the information-theoretic dispersion or uncertainty across the **entire categorical distribution** across all $K$ classes:

$$H(p) = - \sum_{k=1}^K p_k \ln(p_k)$$

For $K=3$ classes:
- **Minimum Entropy ($H_{\min} = 0\text{ nats}$):** Occurs when the distribution is degenerate ($p = [1.0, 0.0, 0.0]$), indicating complete determinism.
- **Maximum Entropy ($H_{\max} = \ln(3) \approx 1.0986\text{ nats}$ or $\log_2(3) \approx 1.5850\text{ bits}$):** Occurs when the distribution is uniform ($p = [1/3, 1/3, 1/3]$), indicating complete ambiguity.

---

### C. Why Describing a 0.70 Probability Threshold as "Entropy-Based" is a Category Error
A fixed threshold applied to maximum softmax probability (e.g., $\text{MSP} \ge 0.70$) is **fundamentally not entropy-based**:

1. **Information Loss:** MSP considers only the top class probability, discarding information about how the remaining $30\%$ of probability mass is distributed.
2. **Entropy Dissociation in Multiclass Domains ($K \ge 3$):**
   Consider two distinct 3-class prediction outputs with identical $\text{MSP} = 0.70$:
   - **Distribution A:** $p_A = [0.70, 0.30, 0.00]$ (Clear two-class competition)
     $$H(p_A) = - (0.70 \ln 0.70 + 0.30 \ln 0.30 + 0) = - (-0.2497 - 0.3612) \approx \mathbf{0.6109\text{ nats}}$$
   - **Distribution B:** $p_B = [0.70, 0.15, 0.15]$ (Uniform uncertainty among alternatives)
     $$H(p_B) = - (0.70 \ln 0.70 + 2 \times 0.15 \ln 0.15) = - (-0.2497 - 0.5691) \approx \mathbf{0.8188\text{ nats}}$$
   - Both outputs have the exact same MSP ($0.70$). However, Distribution B exhibits **$34\%$ higher predictive entropy** than Distribution A.
3. **Scientific Inaccuracy:** Labeling a scalar filter on $\max(p)$ as an "entropy threshold" misrepresents the underlying mathematical operation and obscures whether full-distribution uncertainty was computed.

---

### D. Why a Fixed Threshold Does NOT Eliminate Confidently Incorrect Predictions
It is a dangerous and scientifically false assumption to claim that requiring $\text{MSP} \ge 0.70$ (or any fixed threshold) prevents confident misclassifications:

1. **Neural Network Overconfidence (Logit Miscalibration):**
   As demonstrated by Guo et al. (2017) (*On Calibration of Modern Neural Networks*), modern deep convolutional architectures (such as EfficientNet and ResNet) trained with Cross-Entropy and AdamW are notoriously uncalibrated. The softmax function amplifies small differences in logit magnitude, pushing probabilities toward $0.95–0.99$ even on ambiguous or erroneous inputs.
2. **Out-of-Distribution (OOD) Blind Spots:**
   When presented with non-mosquito images, damaged wings, or background cork textures, uncalibrated networks regularly output $\text{MSP} > 0.90$ for an incorrect genus.
3. **Empirical Evidence in Vectora AI:**
   In controlled experiments, multiple specimens misclassified into incorrect genera had softmax probabilities exceeding $0.75$. A threshold of $0.70$ allows these errors to pass directly into user reports.
4. **Correction Guidance:**
   - Term the mechanism: **Maximum Softmax Probability (MSP) Gating**, not entropy gating.
   - Acknowledge that thresholding only removes **low-margin / equivocal predictions**, but **cannot eliminate confidently incorrect predictions**.
   - True risk reduction requires post-hoc temperature scaling calibration, Out-of-Distribution (OOD) rejection heads, and ensemble variance estimators.

---

## 3. Independent Audit of the Extended Eight-Epoch Model

### Formal Status Selection
In accordance with the audit mandate, the final status for the extended eight-epoch model must be exactly one of:
- `VERIFIED_CROSS_VALIDATED`
- `TRAINING_SET_METRICS_ONLY`
- `VALIDATION_INCOMPLETE`
- `INTEGRITY_FAILURE`

### Formal Evaluation:

#### 1. Why `VERIFIED_CROSS_VALIDATED` is REJECTED
- Cross-validation requires partitioning the entire dataset into $K$ disjoint subsets, training $K$ separate models, and obtaining out-of-fold predictions for $100\%$ of biological specimens.
- In `scripts/train_extended_combined.py`, `next(sgkf.split(...))` was called once.
- Folds 2, 3, 4, and 5 were never trained or evaluated.
- Only 9 of 44 physical specimens ($20.45\%$) have true out-of-fold validation predictions.
- Therefore, the model is **NOT cross-validated**.

#### 2. Why `INTEGRITY_FAILURE` is NOT the Primary Designation
- Set intersection checks in Deliverable 2 confirmed that within Fold 1, the training split and validation split were strictly disjoint ($Train \cap Val = \emptyset$).
- Zero derivatives of the 9 validation parent specimens leaked into the training split.
- The pipeline execution was technically cleanly partitioned for Fold 1.
- Although reporting the 44/44 metric without emphasizing resubstitution violates best practices, it does not stem from corrupt code or data leakage.

#### 3. Why `TRAINING_SET_METRICS_ONLY` Accurately Describes the 44/44 Result, but `VALIDATION_INCOMPLETE` Governs the Model
- The headline metric of 44/44 ($100.00\%$) across all original photographs is a **training-set resubstitution metric** ($35/44$ specimens were in the training set).
- However, the training run did maintain an honest 9-specimen validation split across Epochs 1–8.
- The fundamental defect of the release candidate is that **the cross-validation pipeline was stopped prematurely after a single fold, leaving 4 of 5 folds unvalidated**.

### Final Status Determination:

$$\mathbf{Status: VALIDATION\_INCOMPLETE}$$

*(with formal finding that all full-dataset 44/44 claims represent `TRAINING_SET_METRICS_ONLY`).*

---

## 4. Production Release Decision and Governance Policy

### Decision: PRODUCTION PROMOTION DENIED
1. **The Experimental Model Must Not Be Promoted:**
   [`models/vectora_extended_fp32.onnx`](file:///home/nimr/Projects/mosqscan/models/vectora_extended_fp32.onnx) must not be deployed to the production inference container or designated as an active model.
2. **Active Production Model Preserved:**
   [`models/vectora_v3_fp32.onnx`](file:///home/nimr/Projects/mosqscan/models/vectora_v3_fp32.onnx) (SHA-256 `c3a3656f746a1bb2e7ac428e44670d89cf51f0d0f923ad3aa15420e8a4592cfa`) remains the authoritative active model in Docker container `mosqscan-backend-1`.
3. **PRD Acceptance Gap Remains Unresolved:**
   As established in `reports/v3_1_release_status.md`, the true out-of-fold biological performance of adult mosquito classification on physical specimens is **$50.23\% \pm 12.09\%$ Macro-F1**, which fails the PRD release gate of $\ge 92.00\%$.
   The extended model's apparent $100\%$ score is an artifact of incomplete validation and resubstitution evaluation on training specimens.

---

## 5. Master Audit Traceability Matrix

Table 1 summarizes the findings across all five audit deliverables.

### Table 1: Master Audit Deliverables Summary

| Deliverable | Document Name | Key Technical Finding | Governance Status |
| :--- | :--- | :--- | :--- |
| **Deliverable 1** | [`extended_model_lineage_audit.md`](file:///home/nimr/Projects/mosqscan/reports/extended_model_lineage_audit.md) | All 2,245 parents mapped; 180 ambiguous and 215 unconfirmed preserved | **VERIFIED** |
| **Structured Lineage** | [`extended_model_augmented_lineage_mapping.json`](file:///home/nimr/Projects/mosqscan/reports/extended_model_augmented_lineage_mapping.json) | Complete JSON mapping for all 2,245 verified augmented images | **SAVED** |
| **Deliverable 2** | [`extended_model_partition_audit.md`](file:///home/nimr/Projects/mosqscan/reports/extended_model_partition_audit.md) | Fold 1 cleanly isolated, but Folds 2–5 never executed (1-fold run) | **DEFECT CONFIRMED** |
| **Deliverable 3** | [`extended_model_metric_audit.md`](file:///home/nimr/Projects/mosqscan/reports/extended_model_metric_audit.md) | All epoch metrics recalculated; 44/44 proved to be training resubstitution | **DEFECT CONFIRMED** |
| **Deliverable 4** | [`extended_model_parity_and_latency.md`](file:///home/nimr/Projects/mosqscan/reports/extended_model_parity_and_latency.md) | PyTorch vs ONNX logit diff $3.57 \times 10^{-5}$; median latency 17.11 ms reproduced | **PARITY CONFIRMED** |
| **Deliverable 5** | [`extended_model_verification_decision.md`](file:///home/nimr/Projects/mosqscan/reports/extended_model_verification_decision.md) | Softmax vs Entropy distinguished; Final Status: `VALIDATION_INCOMPLETE` | **WITHHELD FROM PROD** |
| **Exp B Report** | [`experiment_b_audit_corrections.md`](file:///home/nimr/Projects/mosqscan/reports/experiment_b_audit_corrections.md) | Reconstructed matrices; Fold 1 (0.5026) & Fold 3 (0.6586) proved exact | **RECONCILED** |
