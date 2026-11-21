# Vectora AI — Extended Model Metric Recalculation and Evaluation Integrity Audit

**Deliverable:** Extended Model Audit Deliverable 3 of 5  
**Target:** Metric Recalculation, Confusion Matrix Reconstruction, and Evaluation Classification  
**Target Artifacts:** [`reports/v3_extended_training_results.json`](file:///home/nimr/Projects/mosqscan/reports/v3_extended_training_results.json), [`reports/v3_extended_training_report.md`](file:///home/nimr/Projects/mosqscan/reports/v3_extended_training_report.md)  
**Evaluator:** Independent ML Quality & Evaluation Audit  
**Date:** 2026-11-13  
**Status:** Audit Completed · Formal Status Established  

---

## 1. Executive Summary

This deliverable provides the independent metric audit and confusion matrix reconstruction for the extended 8-epoch model.

### Key Audit Conclusions:
1. **Reconstruction of All Epoch Confusion Matrices:** Every reported validation metric in `v3_extended_training_results.json` (Epochs 1 through 8) has been analytically reconstructed down to the exact fraction from the 9 held-out physical validation specimens.
2. **Definitive Finding on the 44/44 Result:** The reported "100.00% accuracy (44 of 44)" and "1.0000 Macro-F1" is **unequivocally a training-set / in-sample resubstitution evaluation**, not an out-of-fold evaluation.
   - **35 of the 44 evaluated physical specimens ($79.55\%$) were directly in the training set**.
   - Only 9 specimens ($20.45\%$) were held-out validation specimens.
3. **Out-of-Fold Coverage Deficit:** Because Folds 2 through 5 were never executed, out-of-fold generalization was tested on only 9 of the 44 specimens. The model lacks out-of-fold evaluation on the remaining 35 specimens ($79.5\%$).

---

## 2. Epoch-by-Epoch Confusion Matrix Reconstruction ($N=9$ Held-Out Physical Specimens)

Support on the 9 held-out physical validation specimens in Fold 1:
- *Aedes aegypti*: 3 specimens (`Aedes_aegypti_4.jpg`, `9`, `13`)
- *Anopheles stephensi*: 2 specimens (`Anopheles_stephensi_5.jpg`, `7`)
- *Culex quinquefasciatus*: 4 specimens (`Culex_quinquefasciatus_11.jpg`, `13`, `15`, `18`)

Matrix format: Rows represent **True Genus** (Ae, An, Cx); columns represent **Predicted Genus** (Ae, An, Cx).

### Table 1: Per-Epoch Progression and Reconstructed Confusion Matrices

| Epoch | Phase | Reconstructed Confusion Matrix ($3 \times 3$) | Accuracy | Macro-F1 | Balanced Acc | Ae Recall | An Recall | Cx Recall | Val Loss |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Ep 1** | Head | `[[1, 2, 0], [0, 2, 0], [0, 1, 3]]` | $66.67\%$ (6/9) | 0.6429 | 0.6944 | $33.33\%$ (1/3) | $100.00\%$ (2/2) | $75.00\%$ (3/4) | 0.5609 |
| **Ep 2** | Head | `[[1, 2, 0], [0, 2, 0], [0, 0, 4]]` | $77.78\%$ (7/9) | 0.7222 | 0.7778 | $33.33\%$ (1/3) | $100.00\%$ (2/2) | $100.00\%$ (4/4) | 0.3824 |
| **Ep 3** | Head | `[[2, 1, 0], [0, 2, 0], [0, 0, 4]]` | $88.89\%$ (8/9) | 0.8667 | 0.8889 | $66.67\%$ (2/3) | $100.00\%$ (2/2) | $100.00\%$ (4/4) | 0.4393 |
| **Ep 4** | Fine | `[[2, 1, 0], [0, 2, 0], [0, 0, 4]]` | $88.89\%$ (8/9) | 0.8667 | 0.8889 | $66.67\%$ (2/3) | $100.00\%$ (2/2) | $100.00\%$ (4/4) | 0.2139 |
| **Ep 5** | Fine | `[[3, 0, 0], [0, 2, 0], [0, 1, 3]]` | $88.89\%$ (8/9) | 0.8857 | 0.9167 | $100.00\%$ (3/3) | $100.00\%$ (2/2) | $75.00\%$ (3/4) | 0.2305 |
| **Ep 6** | Fine | `[[3, 0, 0], [0, 2, 0], [0, 0, 4]]` | $100.00\%$ (9/9)| 1.0000 | 1.0000 | $100.00\%$ (3/3) | $100.00\%$ (2/2) | $100.00\%$ (4/4) | 0.0938 |
| **Ep 7** | Fine | `[[3, 0, 0], [0, 2, 0], [0, 0, 4]]` | $100.00\%$ (9/9)| 1.0000 | 1.0000 | $100.00\%$ (3/3) | $100.00\%$ (2/2) | $100.00\%$ (4/4) | 0.0738 |
| **Ep 8** | Fine | `[[3, 0, 0], [0, 2, 0], [0, 0, 4]]` | $100.00\%$ (9/9)| 1.0000 | 1.0000 | $100.00\%$ (3/3) | $100.00\%$ (2/2) | $100.00\%$ (4/4) | 0.0306 |

---

## 3. Mathematical Recalculation of Each Epoch's Metrics

### Epoch 1 Recalculation
- Confusion Matrix: `[[1, 2, 0], [0, 2, 0], [0, 1, 3]]`
- Precision: $\text{Ae} = \frac{1}{1} = 1.0$, $\text{An} = \frac{2}{5} = 0.40$, $\text{Cx} = \frac{3}{3} = 1.0$.
- Recall: $\text{Ae} = \frac{1}{3} \approx 0.3333$, $\text{An} = \frac{2}{2} = 1.0$, $\text{Cx} = \frac{3}{4} = 0.75$.
- F1-Score: $\text{Ae} = 0.5000$, $\text{An} = \frac{4}{7} \approx 0.5714$, $\text{Cx} = \frac{6}{7} \approx 0.8571$.
- $\text{Macro-F1} = \frac{1/2 + 4/7 + 6/7}{3} = \frac{9}{14} \approx \mathbf{0.642857} \implies \mathbf{0.6429}$ (Exact match).
- $\text{Balanced Accuracy} = \frac{1/3 + 1.0 + 3/4}{3} = \frac{25/12}{3} = \frac{25}{36} \approx \mathbf{0.694444} \implies \mathbf{0.6944}$ (Exact match).

### Epoch 2 Recalculation
- Confusion Matrix: `[[1, 2, 0], [0, 2, 0], [0, 0, 4]]`
- Precision: $\text{Ae} = 1.0$, $\text{An} = \frac{2}{4} = 0.50$, $\text{Cx} = 1.0$.
- Recall: $\text{Ae} = \frac{1}{3} \approx 0.3333$, $\text{An} = 1.0$, $\text{Cx} = 1.0$.
- F1-Score: $\text{Ae} = 0.5000$, $\text{An} = \frac{2}{3} \approx 0.6667$, $\text{Cx} = 1.0$.
- $\text{Macro-F1} = \frac{1/2 + 2/3 + 1.0}{3} = \frac{13}{18} \approx \mathbf{0.722222} \implies \mathbf{0.7222}$ (Exact match).
- $\text{Balanced Accuracy} = \frac{1/3 + 1.0 + 1.0}{3} = \frac{7}{9} \approx \mathbf{0.777778} \implies \mathbf{0.7778}$ (Exact match).

### Epochs 3 & 4 Recalculation
- Confusion Matrix: `[[2, 1, 0], [0, 2, 0], [0, 0, 4]]`
- Precision: $\text{Ae} = 1.0$, $\text{An} = \frac{2}{3} \approx 0.6667$, $\text{Cx} = 1.0$.
- Recall: $\text{Ae} = \frac{2}{3} \approx 0.6667$, $\text{An} = 1.0$, $\text{Cx} = 1.0$.
- F1-Score: $\text{Ae} = 0.8000$, $\text{An} = 0.8000$, $\text{Cx} = 1.0$.
- $\text{Macro-F1} = \frac{0.8 + 0.8 + 1.0}{3} = \frac{13}{15} \approx \mathbf{0.866667} \implies \mathbf{0.8667}$ (Exact match).
- $\text{Balanced Accuracy} = \frac{2/3 + 1.0 + 1.0}{3} = \frac{8}{9} \approx \mathbf{0.888889} \implies \mathbf{0.8889}$ (Exact match).

### Epoch 5 Recalculation
- Confusion Matrix: `[[3, 0, 0], [0, 2, 0], [0, 1, 3]]`
- Precision: $\text{Ae} = 1.0$, $\text{An} = \frac{2}{3} \approx 0.6667$, $\text{Cx} = 1.0$.
- Recall: $\text{Ae} = 1.0$, $\text{An} = 1.0$, $\text{Cx} = \frac{3}{4} = 0.75$.
- F1-Score: $\text{Ae} = 1.0$, $\text{An} = 0.8000$, $\text{Cx} = \frac{6}{7} \approx 0.8571$.
- $\text{Macro-F1} = \frac{1.0 + 0.8 + 6/7}{3} = \frac{31}{35} \approx \mathbf{0.885714} \implies \mathbf{0.8857}$ (Exact match).
- $\text{Balanced Accuracy} = \frac{1.0 + 1.0 + 0.75}{3} = \frac{2.75}{3} = \frac{11}{12} \approx \mathbf{0.916667} \implies \mathbf{0.9167}$ (Exact match).

### Epochs 6, 7 & 8 Recalculation
- Confusion Matrix: `[[3, 0, 0], [0, 2, 0], [0, 0, 4]]`
- All metrics: Precision = 1.0, Recall = 1.0, F1 = 1.0 across all classes.
- $\text{Macro-F1} = \mathbf{1.0000}$, $\text{Balanced Accuracy} = \mathbf{1.0000}$, $\text{Accuracy} = \mathbf{1.0000}$ (Exact match).

---

## 4. Evaluation Nature of the 44/44 Result

In `scripts/train_extended_combined.py` (lines 413–436) and `reports/v3_extended_training_report.md` (Table 2):
```
Global Physical Specimen Evaluation (N=44):
Overall Global Fit: 44/44 (100.00%)
Confusion Matrix:
[[15,  0,  0],
 [ 0,  9,  0],
 [ 0,  0, 20]]
```

### Critical Audit Determination:
The 44/44 evaluation is **NOT an out-of-fold evaluation**. It is a **Training-Set Resubstitution Evaluation**:

```
+-------------------------------------------------------------------------------------------------+
|                                    ALL 44 PHYSICAL SPECIMENS                                    |
+-------------------------------------------------------------------------------------------------+
| 35 Training Parents (80%)                         | 9 Validation Parents (20%)                  |
| IN-SAMPLE RESUBSTITUTION                          | HELD-OUT OUT-OF-SAMPLE                      |
| (Trained for 8 epochs on these 35 specimens       | (Held-out during Fold 1 training,           |
|  and their 1,762 precomputed augmentations)       |  evaluated at end of each epoch)            |
+-------------------------------------------------------------------------------------------------+
```

### Why Resubstitution Inflates Metrics
1. **Model Capacity:** An EfficientNet-B0 backbone (5.3M parameters) has sufficient capacity to memorize 35 training parent specimen geometries when fine-tuned across 8 epochs with gradient descent.
2. **Violation of Scientific Evaluation Standards:** Presenting a 44/44 result on all original photographs without clarifying that $79.55\%$ of those photographs were used during optimization creates the false impression that the model achieved perfect generalizability across the entire biological population.
3. **True Out-of-Sample Performance:** The only true out-of-sample data in this run were the 9 validation specimens in Fold 1. While the checkpoint achieved $9/9$ ($100\%$) on those 9 specimens in Epoch 8, this represents only a small slice ($20.5\%$) of the dataset. The remaining 35 specimens were never validated out-of-fold.

---

## 5. Comparative Evaluation Summary

Table 2 contrasts the extended model's reported metrics against the clean biological cross-validation baseline from `reports/v3_1_cv_clean_results.json`.

### Table 2: Benchmark Comparison: Extended Model vs. Biological CV Baseline

| Metric | Extended Model Fold 1 Val (9 Specimens) | Extended Model Headline Resubstitution (44 Specimens) | True Biological CV Baseline (v3_1 Clean CV, 44 Specimens) | PRD Requirement Target |
| :--- | :---: | :---: | :---: | :---: |
| **Evaluation Type** | Held-Out Split ($N=9$) | In-Sample Resubstitution ($N=44$) | Out-of-Fold Cross-Validation ($N=44$) | Autonomous Field Target |
| **Macro-F1** | **$1.0000$** | **$1.0000$** (Biased) | **$0.5023 \pm 0.1209$** | $\ge 0.9200$ ($92.0\%$) |
| **Balanced Accuracy** | **$1.0000$** | **$1.0000$** (Biased) | **$0.5632 \pm 0.1105$** | $\ge 0.9000$ ($90.0\%$) |
| **Overall Accuracy** | **$100.00\%$** (9/9) | **$100.00\%$** (44/44) | **$62.50\%$** (27.5/44) | $\ge 90.00\%$ |
| **Anopheles Recall** | **$100.00\%$** (2/2) | **$100.00\%$** (9/9) | **$39.58\%$** | $\ge 90.00\%$ |
| **Validation Coverage**| $20.45\%$ (9/44) | $0\%$ out-of-fold (Resubstitution) | **$100.00\%$** (44/44 out-of-fold) | $100\%$ |
| **Evaluation Validity**| Valid single-split val | **Biased Training-Set Metric** | **Gold Standard Out-of-Fold** | Gold Standard |

### Audit Finding:
The headline 44/44 result reflects **in-sample memorization / resubstitution**, not true out-of-fold generalizability.
