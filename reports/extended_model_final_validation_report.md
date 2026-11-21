# Vectora AI — Extended Model Final Validation and Reconciliation Report

**Document Target:** Final Audit Decision, Out-of-Fold Evaluation, and Release Governance  
**Model Architecture:** EfficientNet-B0 ($224 \times 224$), ONNX Runtime FP32  
**Dataset:** 44 Original Biological Photographs + 2,245 Verified Precomputed Augmentations  
**Host Platform:** Intel Core i7-2600 @ 3.40GHz (Sandy Bridge, AVX, 16 GB DDR3 RAM, Omarchy Linux)  
**Standard:** ASD-STE100 Simplified Technical English  
**Date:** 2026-11-13  
**Status:** Validation Completed · Release Promotion Prohibited · Production Model Locked  

---

## 1. Executive Summary and Final Release Decision

This report delivers the authoritative scientific evaluation of the Vectora AI extended dataset training pipeline.
Antigravity investigated prior evaluation claims, resolved all metric discrepancies, executed full multi-fold cross-validation on held-out physical specimens, and verified production container health.

### Official Audit Determinations:
1. **Retraction of 100% Accuracy Claim:**
   The previously reported $44/44$ ($100\%$) accuracy was produced by **training-set resubstitution**. The script trained only Fold 1 (35 specimens) and evaluated all 44 specimens simultaneously using the Epoch 8 checkpoint. That result did not evaluate generalization performance.
2. **Reconciliation of Experiment B:**
   All specimen assignments in Experiment B are reconciled without modifying raw predictions. The single *Aedes* $\to$ *Culex* error occurred in Fold 3. Experiment B achieved a mean fold Macro-F1 of **$0.7903 \pm 0.2504$** ($ddof=1$) and a pooled out-of-fold Macro-F1 of **$0.7899$**, with **$88.89\%$** ($8/9$) Anopheles recall and **$81.82\%$** ($36/44$) accuracy.
3. **Genuine Out-of-Fold Hybrid Model Performance:**
   Executing complete 4-fold `StratifiedGroupKFold` cross-validation on held-out physical photographs demonstrates realistic generalization:
   - **Primary Unweighted:** Pooled Macro-F1 = **$0.7611$**, Accuracy = **$79.55\%$** ($35/44$), Anopheles Recall = **$77.78\%$** ($7/9$).
   - **Ablation Class-Weighted:** Pooled Macro-F1 = **$0.7432$**, Accuracy = **$77.27\%$** ($34/44$), Anopheles Recall = **$88.89\%$** ($8/9$).
4. **Final Deployment Governance Decision:**
   - **PROMOTION PROHIBITED:** Do not promote any candidate checkpoint to production.
   - **ACTIVE PRODUCTION MODEL PRESERVED:** The active production model remains [`models/vectora_v3_fp32.onnx`](file:///home/nimr/Projects/mosqscan/models/vectora_v3_fp32.onnx) (SHA-256: `c3a3656f746a1bb2e7ac428e44670d89cf51f0d0f923ad3aa15420e8a4592cfa`).
   - **STABILITY CONFIRMED:** The Android release, model registry manifest, and production containers remain locked and fully operational.

---

## 2. Analysis of Previous Methodological Defects

Table 1 summarizes the defects identified in the previous extended model evaluation (`scripts/train_extended_combined.py`).

### Table 1: Extended Model Audit and Defect Summary

| Defect Item | Previous Claim | Audit Finding | Methodological Correction |
| :--- | :--- | :--- | :--- |
| **Cross-Validation Scope** | "5-Fold Grouped Cross-Validation" | Only Fold 1 was executed. Folds 2, 3, 4, and 5 were never trained. | Classified as a **single-split validation run** ($N=9$). |
| **Validation Independence** | "Validation specimens evaluate generalization" | Epoch 8 was saved because it reached `val_f1 = 1.0000` on those 9 specimens. | Identified as **checkpoint-selection bias**. |
| **Headline Accuracy** | "44/44 (100%) Physical Specimen Accuracy" | The Fold 1 model was evaluated on all 44 specimens; 35 were in its training set. | Classified as **in-sample resubstitution error**. |
| **Specimen Generalization** | Model described as "perfectly solved" | Held-out physical accuracy across complete folds is $\approx 77\% - 82\%$. | Established baseline Macro-F1 of $0.76 - 0.79$. |

---

## 3. Reconciled Experiment B Specimen Performance

Table 2 presents the reconciled per-fold confusion matrices for Experiment B (unweighted precomputed augmentations, zero online transforms).

### Table 2: Experiment B Reconciled Fold Matrix

| Fold | Support (Ae / An / Cx) | Reconstructed Confusion Matrix | Macro-F1 | Bal. Acc. | Accuracy | Anopheles Recall |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Fold 1** | $4 / 2 / 5$ ($N=11$) | $\begin{pmatrix} 1 & 3 & 0 \\ 1 & 1 & 0 \\ 1 & 0 & 4 \end{pmatrix}$ | **0.5026** | **0.5167** | $54.55\%$ ($6/11$) | $50.00\%$ ($1/2$) |
| **Fold 2** | $4 / 3 / 5$ ($N=12$) | $\begin{pmatrix} 4 & 0 & 0 \\ 0 & 3 & 0 \\ 0 & 0 & 5 \end{pmatrix}$ | **1.0000** | **1.0000** | $100.00\%$ ($12/12$) | $100.00\%$ ($3/3$) |
| **Fold 3** | $4 / 2 / 5$ ($N=11$) | $\begin{pmatrix} 1 & 2 & 1 \\ 0 & 2 & 0 \\ 0 & 0 & 5 \end{pmatrix}$ | **0.6586** | **0.7500** | $72.73\%$ ($8/11$) | $100.00\%$ ($2/2$) |
| **Fold 4** | $3 / 2 / 5$ ($N=10$) | $\begin{pmatrix} 3 & 0 & 0 \\ 0 & 2 & 0 \\ 0 & 0 & 5 \end{pmatrix}$ | **1.0000** | **1.0000** | $100.00\%$ ($10/10$) | $100.00\%$ ($2/2$) |
| **Cumulative** | $15 / 9 / 20$ ($N=44$) | $\begin{pmatrix} 9 & 5 & 1 \\ 1 & 8 & 0 \\ 1 & 0 & 19 \end{pmatrix}$ | **0.7899** | **0.8130** | **81.82%** (36/44) | **88.89%** (8/9) |

*Mean Across Folds:* Macro-F1 = **$0.7903 \pm 0.2504$** ($ddof=1$) | Balanced Accuracy = **$0.8167 \pm 0.2321$**.

---

## 4. Multi-Fold Grouped Hybrid Model Evaluation

Antigravity executed complete 4-fold cross-validation on development hardware (`scripts/train_hybrid_classifier.py`).
Every fold was trained with controlled CPU threading (3 threads, batch size 4).
Held-out validation sets contained **untouched physical photographs only**.

### Table 3: Hybrid Classifier Out-of-Fold Performance Comparison

| Metric | Previous Resubstitution | Experiment B (Reconciled) | Primary Hybrid (Unweighted) | Ablation (Class-Weighted) |
| :--- | :---: | :---: | :---: | :---: |
| **Evaluation Type** | In-Sample Resubstitution | 4-Fold Grouped CV | 4-Fold Grouped CV | 4-Fold Grouped CV |
| **Validation Photographs** | All 44 simultaneously | 44 Held-Out Physical | 44 Held-Out Physical | 44 Held-Out Physical |
| **Online Transforms** | Yes | No | Yes (Training Only) | Yes (Training Only) |
| **Mean Fold Macro-F1** | $1.0000^*$ (1 fold) | $0.7903 \pm 0.2504$ | **$0.7380 \pm 0.1038$** | **$0.7362 \pm 0.1181$** |
| **Pooled Out-of-Fold Macro-F1** | $1.0000^*$ (Flawed) | $0.7899$ | **$0.7611$** | **$0.7432$** |
| **Pooled Balanced Accuracy** | $1.0000^*$ (Flawed) | $0.8130$ | **$0.7759$** | **$0.7741$** |
| **Overall Accuracy** | $100.00\%$ ($44/44$) | $81.82\%$ ($36/44$) | **$79.55\%$ ($35/44$)** | **$77.27\%$ ($34/44$)** |
| **Anopheles Recall** | $100.00\%$ ($9/9$) | $88.89\%$ ($8/9$) | **$77.78\%$ ($7/9$)** | **$88.89\%$ ($8/9$)** |
| **Aedes Recall** | $100.00\%$ ($15/15$) | $60.00\%$ ($9/15$) | **$60.00\%$ ($9/15$)** | **$53.33\%$ ($8/15$)** |
| **Culex Recall** | $100.00\%$ ($20/20$) | $95.00\%$ ($19/20$) | **$95.00\%$ ($19/20$)** | **$90.00\%$ ($18/20$)** |

`*` Denotes flawed resubstitution metric.

### Table 4: Primary Hybrid Out-of-Fold Confusion Matrix ($N=44$)
$$\text{CM}_{\text{Primary}} = \begin{pmatrix} 9 & 5 & 1 \\ 2 & 7 & 0 \\ 1 & 0 & 19 \end{pmatrix}$$

### Table 5: Class-Weighted Ablation Out-of-Fold Confusion Matrix ($N=44$)
$$\text{CM}_{\text{Ablation}} = \begin{pmatrix} 8 & 6 & 1 \\ 1 & 8 & 0 \\ 1 & 1 & 18 \end{pmatrix}$$

### Scientific Analysis:
1. **Class-Weighting Trade-Off:** Applying class weights increases *Anopheles* recall from **$77.78\%$** ($7/9$) to **$88.89\%$** ($8/9$), matching Experiment B. However, it increases false positives against *Aedes*, reducing overall accuracy from **$79.55\%$** to **$77.27\%$**.
2. **Realistic Generalization Ceiling:** Across both runs, generalization on held-out physical specimens consistently lands in the **$76\% - 80\%$** Macro-F1 range. This confirms that claims of $100\%$ accuracy were entirely invalid.

---

## 5. Checkpoint Provenance and File Integrity

Table 6 records the SHA-256 hashes of all generated research artifacts.

### Table 6: Generated Research Artifact Checksums

| Artifact Path | SHA-256 Checksum | Purpose / Description |
| :--- | :--- | :--- |
| [`models/research/hybrid_unweighted_fold1.pt`](file:///home/nimr/Projects/mosqscan/models/research/hybrid_unweighted_fold1.pt) | `9559bb29c0a6b73ebf0367eb7826359bebe3ba03cb117ea7ea79815c48b26c2e` | Primary Fold 1 Checkpoint |
| [`models/research/hybrid_unweighted_fold2.pt`](file:///home/nimr/Projects/mosqscan/models/research/hybrid_unweighted_fold2.pt) | `0e9cb20387b32810fb5cfc66c30f40df8374d6c41b8c0d1e1fa63bc64b971c26` | Primary Fold 2 Checkpoint |
| [`models/research/hybrid_unweighted_fold3.pt`](file:///home/nimr/Projects/mosqscan/models/research/hybrid_unweighted_fold3.pt) | `b9f5647565985ae08ef61cb56bb76d75508b534d0263f350cbe43b4685ff8614` | Primary Fold 3 Checkpoint |
| [`models/research/hybrid_unweighted_fold4.pt`](file:///home/nimr/Projects/mosqscan/models/research/hybrid_unweighted_fold4.pt) | `d0fbc705a61fc08c7908b8b082ae0d65a88c3a1e2850901e687e14dbe10ec7ce` | Primary Fold 4 Checkpoint |
| [`models/research/hybrid_weighted_fold1.pt`](file:///home/nimr/Projects/mosqscan/models/research/hybrid_weighted_fold1.pt) | `532e013a778c13b28b7470f5e1a3bcda4ecf90117fc040715aa31fe829672eb1` | Ablation Fold 1 Checkpoint |
| [`models/research/hybrid_weighted_fold2.pt`](file:///home/nimr/Projects/mosqscan/models/research/hybrid_weighted_fold2.pt) | `99d9b626f228b3234d7fb37caeb591a134a6ca024b4249a4f6d482cf187ea131` | Ablation Fold 2 Checkpoint |
| [`models/research/hybrid_weighted_fold3.pt`](file:///home/nimr/Projects/mosqscan/models/research/hybrid_weighted_fold3.pt) | `e24391ea114feebfd67c9c0b1ef380b263e7c85aa882c42b5839257e8aa6878b` | Ablation Fold 3 Checkpoint |
| [`models/research/hybrid_weighted_fold4.pt`](file:///home/nimr/Projects/mosqscan/models/research/hybrid_weighted_fold4.pt) | `d95856755490ff4908920199e69315dff722fe1fa8a7c29759e0a0ee449bc2b8` | Ablation Fold 4 Checkpoint |
| [`reports/extended_model_grouped_evaluation_results.json`](file:///home/nimr/Projects/mosqscan/reports/extended_model_grouped_evaluation_results.json) | `45050f4625b0cb5030ddf4ffea4a485fa6b785e68ce0e3c54c34a2e83163098d` | Machine-readable metrics & predictions |
| **Active Production Model** | `c3a3656f746a1bb2e7ac428e44670d89cf51f0d0f923ad3aa15420e8a4592cfa` | **UNMODIFIED** (`models/vectora_v3_fp32.onnx`) |

---

## 6. Hardware Utilization and Production Server Coexistence

The training controller script [`scripts/run_hybrid_training.sh`](file:///home/nimr/Projects/mosqscan/scripts/run_hybrid_training.sh) enforced continuous production safety on the Intel Core i7-2600 host:

1. **Host Server Availability:**
   - Total health check requests during training: **336 requests**.
   - Failed requests: **0 failures** ($100\%$ uptime).
   - Baseline API latency before training: **65.93 ms** (median), **104.34 ms** (P95).
   - Concurrent API latency during training: **89.00 ms** (median), **114.00 ms** (P95), **222.00 ms** (maximum spike).
   - Post-training API latency: **63.19 ms** (median), **85.09 ms** (P95).
2. **CPU & Memory Profiling:**
   - PyTorch threads strictly capped at **3 execution threads**.
   - Peak process memory: **3,130.4 MB** ($19.7\%$ of host RAM).
   - Zero swap thrashing occurred.
3. **Storage and Integrity:**
   - Active production model [`models/vectora_v3_fp32.onnx`](file:///home/nimr/Projects/mosqscan/models/vectora_v3_fp32.onnx) was verified via SHA-256 before and after training. The checksum remained identical: `c3a3656f746a1bb2e7ac428e44670d89cf51f0d0f923ad3aa15420e8a4592cfa`.

---

## 7. Release Governance Action Items

1. **Model Promotion Status:**
   - **PROHIBITED:** Neither the 8-epoch Fold 1 checkpoint nor any hybrid fold checkpoint will be promoted to production.
   - The production server will continue serving [`models/vectora_v3_fp32.onnx`](file:///home/nimr/Projects/mosqscan/models/vectora_v3_fp32.onnx).
2. **Android Field Release:**
   - The compiled Android field release application remains configured to query `http://<server-ip>:8000`.
   - Android application code, APK assets, and client models remain locked.
3. **Larvae Classification:**
   - The larvae model remains unvalidated and excluded from production serving.
4. **Independent Test Requirement:**
   - No architectural change will be accepted for production release without evaluation on a locked external test dataset of newly collected, independently verified specimens.
