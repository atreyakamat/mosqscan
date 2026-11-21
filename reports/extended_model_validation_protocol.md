# Vectora AI — Extended Model Validation Protocol and Scientific Evaluation Standard

**Document Target:** Formal Validation Terminology, Checkpoint-Selection Bias Mitigation, and Evaluation Protocol  
**Compliance Standard:** ASD-STE100 Simplified Technical English  
**Governing Architecture:** EfficientNet-B0 ($224 \times 224$), ONNX Runtime FP32  
**Date:** 2026-11-13  
**Status:** Approved Technical Protocol  

---

## 1. Executive Summary

This protocol defines the scientific validation rules for all mosquito classification models in Vectora AI.
Antigravity investigated the extended 8-epoch model evaluation in `scripts/train_extended_combined.py` and identified two critical evaluation defects:
1. **Single-Split Execution:** The pipeline initiated a 5-fold StratifiedGroupKFold split but stopped after the first iteration. It trained and evaluated only Fold 1 (35 training specimens, 9 validation specimens). Folds 2, 3, 4, and 5 were never executed.
2. **In-Sample Resubstitution Evaluation:** The headline $44/44$ ($100\%$) accuracy was produced by evaluating the Fold 1 checkpoint across all 44 specimens simultaneously. Thirty-five of the 44 specimens ($79.55\%$) were directly in the training set.

This protocol establishes mandatory terminology corrections, eliminates checkpoint-selection bias, and specifies an outer evaluation procedure for all future model assessments.

---

## 2. Mandatory Validation Terminology Corrections

All internal reports, engineering records, and public communications must follow the terminology definitions in Table 1.

### Table 1: Standardized Metric Terminology

| Evaluation Term | Definition | Permitted Usage | Prohibited Usage |
| :--- | :--- | :--- | :--- |
| **Training Resubstitution** | Evaluating a trained model on specimens included in its own training set. | Diagnostic measure of model capacity and memorization. | Must **NEVER** be described as generalization accuracy or test performance. |
| **Single-Split Validation** | Evaluating a model on specimens held out from a single train/validation split. | Preliminary indicator of convergence on one fold ($N=9$). | Must **NEVER** be described as complete 4-fold or 5-fold cross-validation. |
| **Out-of-Fold Cross-Validation** | Aggregating predictions across all $K$ folds where every specimen was held out in exactly one fold. | Official internal validation benchmark across all 44 physical specimens. | Must not be claimed if any fold was skipped or if derivatives leaked across splits. |
| **External Test Evaluation** | Evaluating a locked model on newly collected, independently collected specimens. | Final gate for field deployment release. | Cannot be claimed using any subset of the 44 development specimens. |

### Retraction of 100% Accuracy Claim:
The claim that the extended 8-epoch model achieved "$100\%$ accuracy on the 44 original photographs" is formally retracted from research evaluation. That metric was an artifact of training-set resubstitution ($35$ specimens) combined with checkpoint-selection bias ($9$ specimens).

---

## 3. Analysis of Checkpoint-Selection Bias

The extended model pipeline evaluated validation loss and Macro-F1 across 8 epochs on the 9 held-out specimens of Fold 1:

```
Epoch 1 (Warmup): Val Loss = 0.5821, Val Macro-F1 = 0.8889
Epoch 2 (Warmup): Val Loss = 0.4912, Val Macro-F1 = 0.8889
Epoch 3 (Warmup): Val Loss = 0.4105, Val Macro-F1 = 1.0000
Epoch 4 (Fine):   Val Loss = 0.3842, Val Macro-F1 = 1.0000
Epoch 5 (Fine):   Val Loss = 0.3510, Val Macro-F1 = 1.0000
Epoch 6 (Fine):   Val Loss = 0.3204, Val Macro-F1 = 1.0000
Epoch 7 (Fine):   Val Loss = 0.2988, Val Macro-F1 = 1.0000
Epoch 8 (Fine):   Val Loss = 0.2815, Val Macro-F1 = 1.0000  <-- Checkpoint Saved
```

### Identification of Methodological Flaws:
1. **Stopping Criterion Contamination:** Epoch 8 was saved because it minimized validation loss on the 9 held-out specimens. This means the 9 validation specimens influenced model selection.
2. **Absence of an Outer Test Set:** Because no separate test set existed, the 9 validation specimens were used both to select the best checkpoint and to evaluate performance.
3. **Resubstitution Contamination:** The saved checkpoint was then re-evaluated across all 44 specimens, contaminating 35 specimens with training exposure and 9 specimens with selection exposure. Zero specimens were truly unexposed.

---

## 4. Formal Protocol for Complete Grouped Evaluation

Future research evaluations must adhere to the following 5-point protocol:

```
                            NESTED VALIDATION ARCHITECTURE
                            
   +---------------------------------------------------------------------------------+
   |                           All 44 Biological Specimens                           |
   +---------------------------------------------------------------------------------+
                                           |
                   StratifiedGroupKFold (K=4 or K=5, Seed=42)
                                           |
         +-----------------+---------------+-----------------+---------------+
         | Fold 1          | Fold 2        | Fold 3          | Fold 4        |
         v                 v               v                 v               v
   +---------------+---------------+---------------+---------------+---------------+
   | Val: 11 Specs | Val: 11 Specs | Val: 11 Specs | Val: 11 Specs | (Untouched    |
   | Train: 33 Par | Train: 33 Par | Train: 33 Par | Train: 33 Par |  Physical     |
   | + Verified Aug| + Verified Aug| + Verified Aug| + Verified Aug|  Photos ONLY) |
   +---------------+---------------+---------------+---------------+---------------+
         |                 |               |                 |
         v                 v               v                 v
   [Model Fold 1]    [Model Fold 2]  [Model Fold 3]    [Model Fold 4]
   (Sha-256 Hash)    (Sha-256 Hash)  (Sha-256 Hash)    (Sha-256 Hash)
         |                 |               |                 |
         +-----------------+---------------+-----------------+
                                           |
                                           v
                       Accumulate Out-of-Fold Predictions
                       (N = 44 Pure Held-Out Physical Specimens)
                                           |
                                           v
                       Compute Pooled Confusion Matrix & F1
```

### Requirement 1: Complete Fold Execution
Every fold ($1 \le k \le K$) must be independently trained and evaluated. Single-split execution is prohibited for cross-validation reporting.

### Requirement 2: Strict Biological Grouping
Group exclusively by verified physical specimen ID. Every precomputed and online augmentation derived from a physical parent must remain in the training fold of that parent. Zero derivative images may enter the validation split.

### Requirement 3: Untouched Physical Validation Photographs
Validation splits must strictly contain original physical photographs. Augmented images are prohibited in validation sets.

### Requirement 4: Checkpoint Traceability
Every fold must produce a distinct checkpoint saved to `models/research/`. The SHA-256 hash of each checkpoint must be recorded in the evaluation JSON.

### Requirement 5: Raw Prediction Accumulation
Individual specimen predictions (filename, true label, predicted label, class softmax probabilities) must be saved for all evaluated specimens. Metrics must be computed directly from raw prediction tables.

---

## 5. Deployment Protection Rules

1. The active production server model must remain [`models/vectora_v3_fp32.onnx`](file:///home/nimr/Projects/mosqscan/models/vectora_v3_fp32.onnx) (SHA-256: `c3a3656f746a1bb2e7ac428e44670d89cf51f0d0f923ad3aa15420e8a4592cfa`).
2. No research checkpoint may be promoted to production without independent test set validation on physical hardware.
3. The model registry manifest [`model-registry/manifest.json`](file:///home/nimr/Projects/mosqscan/model-registry/manifest.json) must remain locked.
