# Vectora AI — Experiment B Specimen Prediction Reconciliation Report

**Target:** Specimen-Level Prediction Reconciliation for Experiment B  
**Dataset:** 44 Original Biological Photographs + 2,245 Verified Precomputed Augmentations  
**Evaluation Scheme:** 4-Fold StratifiedGroupKFold ($K=4$, Seed 42, Biological Parent Grouping)  
**Standard:** ASD-STE100 Simplified Technical English  
**Date:** 2026-11-13  
**Status:** Reconciled & Formally Approved  

---

## 1. Executive Summary

This report delivers the final specimen-level reconciliation for **Experiment B** (precomputed augmentations with unweighted loss and zero online dynamic transforms).
The audit compares:
1. The initial combined training records in `reports/v3_combined_training_comparison.md` and `reports/v3_combined_experiments.json`.
2. The mathematical metric audit in `reports/experiment_b_audit_corrections.md`.
3. The reconstructed per-fold confusion matrices and specimen assignments.

### Key Audit Conclusions:
1. **Zero Prediction Manipulation:** No raw predictions were altered. No specimen labels were modified.
2. **Deterministic Mathematical Reconciliation:**
   - The reported metrics in `v3_combined_experiments.json` (Fold 1 Macro-F1 = $0.5026$, Fold 3 Macro-F1 = $0.6586$) are mathematically exact.
   - The single *Aedes* specimen misclassified as *Culex* occurred in **Fold 3**, not Fold 1.
   - Attributing this misclassification to Fold 1 yields a Macro-F1 of $0.4952$ (as seen in preliminary baseline iterations). In Experiment B, that error occurred in Fold 3, producing exactly $0.5026$ in Fold 1 and $0.6586$ in Fold 3.
3. **Specimen Isolation:**
   - All 44 specimens evaluated across the four folds were strictly held-out out-of-fold physical specimens.
   - All precomputed derivatives of validation parent specimens were strictly excluded from the training split.

---

## 2. Partition Specimen Rosters and Classification Outcomes

Table 1 details the biological specimen assignments across all four cross-validation folds.

### Table 1: Specimen Allocation and Out-of-Fold Prediction Outcomes

| Fold | True Genus | Specimen File Identifier | Predicted Genus | Prediction Status | Error Classification |
| :---: | :--- | :--- | :--- | :---: | :--- |
| **1** | Aedes | `Aedes_aegypti_6.jpg` | Aedes | **Correct** | - |
| **1** | Aedes | `Aedes_aegypti_7.jpg` | Anopheles | **Error** | Aedes $\to$ Anopheles |
| **1** | Aedes | `Aedes_aegypti_11.jpg` | Anopheles | **Error** | Aedes $\to$ Anopheles |
| **1** | Aedes | `Aedes_aegypti_12.jpg` | Anopheles | **Error** | Aedes $\to$ Anopheles |
| **1** | Anopheles | `Anopheles_stephensi_2.jpg` | Anopheles | **Correct** | - |
| **1** | Anopheles | `Anopheles_stephensi_3.jpg` | Aedes | **Error** | Anopheles $\to$ Aedes |
| **1** | Culex | `Culex_quinquefasciatus_5.jpg` | Culex | **Correct** | - |
| **1** | Culex | `Culex_quinquefasciatus_8.jpg` | Culex | **Correct** | - |
| **1** | Culex | `Culex_quinquefasciatus_9.jpg` | Culex | **Correct** | - |
| **1** | Culex | `Culex_quinquefasciatus_15.jpg` | Culex | **Correct** | - |
| **1** | Culex | `Culex_quinquefasciatus_20.jpg` | Aedes | **Error** | Culex $\to$ Aedes |
| **2** | Aedes | `Aedes_aegypti_3.jpg` | Aedes | **Correct** | - |
| **2** | Aedes | `Aedes_aegypti_9.jpg` | Aedes | **Correct** | - |
| **2** | Aedes | `Aedes_aegypti_10.jpg` | Aedes | **Correct** | - |
| **2** | Aedes | `Aedes_aegypti_15.jpg` | Aedes | **Correct** | - |
| **2** | Anopheles | `Anopheles_stephensi_1.jpg` | Anopheles | **Correct** | - |
| **2** | Anopheles | `Anopheles_stephensi_4.jpg` | Anopheles | **Correct** | - |
| **2** | Anopheles | `Anopheles_stephensi_8.jpg` | Anopheles | **Correct** | - |
| **2** | Culex | `Culex_quinquefasciatus_1.jpg` | Culex | **Correct** | - |
| **2** | Culex | `Culex_quinquefasciatus_2.jpg` | Culex | **Correct** | - |
| **2** | Culex | `Culex_quinquefasciatus_7.jpg` | Culex | **Correct** | - |
| **2** | Culex | `Culex_quinquefasciatus_11.jpg` | Culex | **Correct** | - |
| **2** | Culex | `Culex_quinquefasciatus_14.jpg` | Culex | **Correct** | - |
| **3** | Aedes | `Aedes_aegypti_1.jpg` | Anopheles | **Error** | Aedes $\to$ Anopheles |
| **3** | Aedes | `Aedes_aegypti_2.jpg` | Anopheles | **Error** | Aedes $\to$ Anopheles |
| **3** | Aedes | `Aedes_aegypti_13.jpg` | Culex | **Error** | Aedes $\to$ Culex |
| **3** | Aedes | `Aedes_aegypti_14.jpg` | Aedes | **Correct** | - |
| **3** | Anopheles | `Anopheles_stephensi_6.jpg` | Anopheles | **Correct** | - |
| **3** | Anopheles | `Anopheles_stephensi_7.jpg` | Anopheles | **Correct** | - |
| **3** | Culex | `Culex_quinquefasciatus_3.jpg` | Culex | **Correct** | - |
| **3** | Culex | `Culex_quinquefasciatus_4.jpg` | Culex | **Correct** | - |
| **3** | Culex | `Culex_quinquefasciatus_10.jpg` | Culex | **Correct** | - |
| **3** | Culex | `Culex_quinquefasciatus_12.jpg` | Culex | **Correct** | - |
| **3** | Culex | `Culex_quinquefasciatus_19.jpg` | Culex | **Correct** | - |
| **4** | Aedes | `Aedes_aegypti_4.jpg` | Aedes | **Correct** | - |
| **4** | Aedes | `Aedes_aegypti_5.jpg` | Aedes | **Correct** | - |
| **4** | Aedes | `Aedes_aegypti_8.jpg` | Aedes | **Correct** | - |
| **4** | Anopheles | `Anopheles_stephensi_5.jpg` | Anopheles | **Correct** | - |
| **4** | Anopheles | `Anopheles_stephensi_9.jpg` | Anopheles | **Correct** | - |
| **4** | Culex | `Culex_quinquefasciatus_6.jpg` | Culex | **Correct** | - |
| **4** | Culex | `Culex_quinquefasciatus_13.jpg` | Culex | **Correct** | - |
| **4** | Culex | `Culex_quinquefasciatus_16.jpg` | Culex | **Correct** | - |
| **4** | Culex | `Culex_quinquefasciatus_17.jpg` | Culex | **Correct** | - |
| **4** | Culex | `Culex_quinquefasciatus_18.jpg` | Culex | **Correct** | - |

---

## 3. Reconciled Confusion Matrices by Fold

The rows represent the ground-truth biological genus; columns represent predicted genus:
`[0: Aedes, 1: Anopheles, 2: Culex]`

### Fold 1 Matrix (11 Specimens)
$$\text{CM}_1 = \begin{pmatrix} 1 & 3 & 0 \\ 1 & 1 & 0 \\ 1 & 0 & 4 \end{pmatrix}$$
- Correct: 6 / 11 ($54.55\%$)
- Class F1-Scores: Aedes = $0.2857$, Anopheles = $0.3333$, Culex = $0.8889$
- **Macro-F1:** $\frac{0.2857 + 0.3333 + 0.8889}{3} = \mathbf{0.5026}$

### Fold 2 Matrix (12 Specimens)
$$\text{CM}_2 = \begin{pmatrix} 4 & 0 & 0 \\ 0 & 3 & 0 \\ 0 & 0 & 5 \end{pmatrix}$$
- Correct: 12 / 12 ($100.00\%$)
- Class F1-Scores: Aedes = $1.0000$, Anopheles = $1.0000$, Culex = $1.0000$
- **Macro-F1:** $\mathbf{1.0000}$

### Fold 3 Matrix (11 Specimens)
$$\text{CM}_3 = \begin{pmatrix} 1 & 2 & 1 \\ 0 & 2 & 0 \\ 0 & 0 & 5 \end{pmatrix}$$
- Correct: 8 / 11 ($72.73\%$)
- Class F1-Scores: Aedes = $0.4000$, Anopheles = $0.6667$, Culex = $0.9091$
- **Macro-F1:** $\frac{0.4000 + 0.6667 + 0.9091}{3} = \mathbf{0.6586}$

### Fold 4 Matrix (10 Specimens)
$$\text{CM}_4 = \begin{pmatrix} 3 & 0 & 0 \\ 0 & 2 & 0 \\ 0 & 0 & 5 \end{pmatrix}$$
- Correct: 10 / 10 ($100.00\%$)
- Class F1-Scores: Aedes = $1.0000$, Anopheles = $1.0000$, Culex = $1.0000$
- **Macro-F1:** $\mathbf{1.0000}$

---

## 4. Cumulative Summation & Discrepancy Resolution

Summing all four fold confusion matrices gives the cumulative out-of-fold confusion matrix:

$$\text{CM}_{\text{cumulative}} = \text{CM}_1 + \text{CM}_2 + \text{CM}_3 + \text{CM}_4 = \begin{pmatrix} 9 & 5 & 1 \\ 1 & 8 & 0 \\ 1 & 0 & 19 \end{pmatrix}$$

### Verification Checklist:
- Total evaluated specimens: $9 + 5 + 1 + 1 + 8 + 0 + 1 + 0 + 19 = 44$.
- Total correct predictions: $9 + 8 + 19 = 36$ ($81.82\%$).
- Total misclassifications: $8$ ($18.18\%$).
- Anopheles recall: $\frac{8}{8 + 1} = \frac{8}{9} = \mathbf{88.89\%}$.
- Aedes recall: $\frac{9}{9 + 5 + 1} = \frac{9}{15} = \mathbf{60.00\%}$.
- Culex recall: $\frac{19}{19 + 1} = \frac{19}{20} = \mathbf{95.00\%}$.
- Mean Fold Macro-F1: $\frac{0.5026 + 1.0000 + 0.6586 + 1.0000}{4} = \mathbf{0.7903} \pm \mathbf{0.2504}$ ($s$, $ddof=1$).
- Pooled Out-of-Fold Macro-F1: $\mathbf{0.7899}$.

### Resolution Statement:
All individual specimen assignments, fold metrics, and cumulative matrix cells are completely reconciled. No contradictions exist between the raw data, the audit calculations, and the summary reports.
