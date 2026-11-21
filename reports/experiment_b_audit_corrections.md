# Vectora AI — Experiment B Metric Discrepancy Correction and Audit Report

**Target:** Audit and Reconciliation of Experiment B Cross-Validation Metrics  
**Dataset:** Mendeley Mosquito Dataset (44 physical specimens + 2,245 verified precomputed augmentations)  
**Partitioning Scheme:** 4-Fold `StratifiedGroupKFold` ($K=4$, Seed 42, grouped strictly by physical parent specimen)  
**Evaluator:** Independent ML Quality & Evaluation Audit  
**Date:** 2026-11-13  
**Status:** Audit Completed · Metrics Reconciled  

---

## 1. Executive Summary

This report delivers the authoritative metric reconciliation for **Experiment B** (combined dataset training: 44 physical original photographs plus 2,245 verified precomputed augmentations, unweighted Cross-Entropy loss, zero online dynamic transforms).

The audit investigated flagged discrepancies regarding:
1. Reported Fold 1 Macro-F1 of **0.5026** and Fold 3 Macro-F1 of **0.6586**.
2. Confusion matrix reconstruction for each of the four folds.
3. Distinction between **mean fold Macro-F1** and **pooled out-of-fold Macro-F1**.

### Key Audit Findings
1. **Mathematical Accuracy of Reported Metrics:** The reported Fold 1 Macro-F1 ($0.5026$) and Fold 3 Macro-F1 ($0.6586$) are **100% mathematically exact** and derived directly from the fold confusion matrices without manipulation.
2. **Root Cause of Apparent Discrepancy:** The apparent discrepancy arose from an alternative hypothesis where the single *Aedes* misclassified as *Culex* was attributed to Fold 1 rather than Fold 3. Attributing that error to Fold 1 yields a Fold 1 Macro-F1 of $0.4952$ (as observed in earlier baseline runs). In Experiment B, that error occurred in Fold 3, which precisely yields $0.5026$ in Fold 1 and $0.6586$ in Fold 3.
3. **Reconciled Overall Performance:**
   - **Mean Across Four Folds Macro-F1:** **$0.7903 \pm 0.2504$** (Sample SD, $ddof=1$) / **$\pm 0.2168$** (Population SD, $ddof=0$).
   - **Pooled Out-of-Fold Macro-F1:** **$0.7899$** ($78.99\%$).
   - **Mean Across Four Folds Balanced Accuracy:** **$0.8167 \pm 0.2321$**.
   - **Pooled Out-of-Fold Balanced Accuracy:** **$0.8130$** ($81.30\%$).
   - **Overall Physical Accuracy:** **$81.82\%$** ($36/44$ specimens correct across out-of-fold evaluations).

---

## 2. Reconstructed Fold Confusion Matrices

Every fold evaluated held-out physical photographs of biological parent specimens that were completely excluded from the training split of that fold.

Class index convention:
- Index 0: `Aedes`
- Index 1: `Anopheles`
- Index 2: `Culex`

Matrix format: Rows represent **True Genus**; columns represent **Predicted Genus**.

### Fold 1 Matrix ($N=11$ Held-Out Physical Specimens)
*Support: Aedes = 4, Anopheles = 2, Culex = 5*

$$\text{CM}_{\text{Fold 1}} = \begin{pmatrix} 1 & 3 & 0 \\ 1 & 1 & 0 \\ 1 & 0 & 4 \end{pmatrix}$$

* **Per-Class Precision:**
  - $\text{Precision}_{\text{Aedes}} = \frac{1}{1 + 1 + 1} = \frac{1}{3} \approx 0.3333$
  - $\text{Precision}_{\text{Anopheles}} = \frac{1}{3 + 1 + 0} = \frac{1}{4} = 0.2500$
  - $\text{Precision}_{\text{Culex}} = \frac{4}{0 + 0 + 4} = \frac{4}{4} = 1.0000$
* **Per-Class Recall:**
  - $\text{Recall}_{\text{Aedes}} = \frac{1}{4} = 0.2500$ ($25.00\%$)
  - $\text{Recall}_{\text{Anopheles}} = \frac{1}{2} = 0.5000$ ($50.00\%$)
  - $\text{Recall}_{\text{Culex}} = \frac{4}{5} = 0.8000$ ($80.00\%$)
* **Per-Class F1-Score:**
  - $\text{F1}_{\text{Aedes}} = \frac{2 \times \frac{1}{3} \times \frac{1}{4}}{\frac{1}{3} + \frac{1}{4}} = \frac{2/12}{7/12} = \frac{2}{7} \approx 0.285714$
  - $\text{F1}_{\text{Anopheles}} = \frac{2 \times \frac{1}{4} \times \frac{1}{2}}{\frac{1}{4} + \frac{1}{2}} = \frac{1/4}{3/4} = \frac{1}{3} \approx 0.333333$
  - $\text{F1}_{\text{Culex}} = \frac{2 \times 1.0 \times \frac{4}{5}}{1.0 + \frac{4}{5}} = \frac{8/5}{9/5} = \frac{8}{9} \approx 0.888889$
* **Fold 1 Summary Metrics:**
  - $\text{Macro-F1} = \frac{\frac{2}{7} + \frac{1}{3} + \frac{8}{9}}{3} = \frac{\frac{18 + 21 + 56}{63}}{3} = \frac{95}{189} \approx \mathbf{0.502646} \implies \mathbf{0.5026}$
  - $\text{Balanced Accuracy} = \frac{0.25 + 0.50 + 0.80}{3} = \frac{1.55}{3} \approx \mathbf{0.516667} \implies \mathbf{0.5167}$
  - $\text{Accuracy} = \frac{1 + 1 + 4}{11} = \frac{6}{11} \approx \mathbf{0.545455} \implies \mathbf{0.5455}$ ($54.55\%$)

---

### Fold 2 Matrix ($N=12$ Held-Out Physical Specimens)
*Support: Aedes = 4, Anopheles = 3, Culex = 5*

$$\text{CM}_{\text{Fold 2}} = \begin{pmatrix} 4 & 0 & 0 \\ 0 & 3 & 0 \\ 0 & 0 & 5 \end{pmatrix}$$

* **Per-Class Metrics:**
  - Precision: Aedes = $1.0000$, Anopheles = $1.0000$, Culex = $1.0000$
  - Recall: Aedes = $1.0000$, Anopheles = $1.0000$, Culex = $1.0000$
  - F1-Score: Aedes = $1.0000$, Anopheles = $1.0000$, Culex = $1.0000$
* **Fold 2 Summary Metrics:**
  - $\text{Macro-F1} = \mathbf{1.0000}$
  - $\text{Balanced Accuracy} = \mathbf{1.0000}$
  - $\text{Accuracy} = \frac{12}{12} = \mathbf{1.0000}$ ($100.00\%$)

---

### Fold 3 Matrix ($N=11$ Held-Out Physical Specimens)
*Support: Aedes = 4, Anopheles = 2, Culex = 5*

$$\text{CM}_{\text{Fold 3}} = \begin{pmatrix} 1 & 2 & 1 \\ 0 & 2 & 0 \\ 0 & 0 & 5 \end{pmatrix}$$

* **Per-Class Precision:**
  - $\text{Precision}_{\text{Aedes}} = \frac{1}{1 + 0 + 0} = 1.0000$
  - $\text{Precision}_{\text{Anopheles}} = \frac{2}{2 + 2 + 0} = \frac{2}{4} = 0.5000$
  - $\text{Precision}_{\text{Culex}} = \frac{5}{1 + 0 + 5} = \frac{5}{6} \approx 0.833333$
* **Per-Class Recall:**
  - $\text{Recall}_{\text{Aedes}} = \frac{1}{4} = 0.2500$ ($25.00\%$)
  - $\text{Recall}_{\text{Anopheles}} = \frac{2}{2} = 1.0000$ ($100.00\%$)
  - $\text{Recall}_{\text{Culex}} = \frac{5}{5} = 1.0000$ ($100.00\%$)
* **Per-Class F1-Score:**
  - $\text{F1}_{\text{Aedes}} = \frac{2 \times 1.0 \times 0.25}{1.0 + 0.25} = \frac{0.50}{1.25} = \frac{2}{5} = 0.400000$
  - $\text{F1}_{\text{Anopheles}} = \frac{2 \times 0.50 \times 1.0}{0.50 + 1.0} = \frac{1.0}{1.5} = \frac{2}{3} \approx 0.666667$
  - $\text{F1}_{\text{Culex}} = \frac{2 \times \frac{5}{6} \times 1.0}{\frac{5}{6} + 1.0} = \frac{5/3}{11/6} = \frac{10}{11} \approx 0.909091$
* **Fold 3 Summary Metrics:**
  - $\text{Macro-F1} = \frac{\frac{2}{5} + \frac{2}{3} + \frac{10}{11}}{3} = \frac{\frac{66 + 110 + 150}{165}}{3} = \frac{326}{495} \approx \mathbf{0.658586} \implies \mathbf{0.6586}$
  - $\text{Balanced Accuracy} = \frac{0.25 + 1.00 + 1.00}{3} = \frac{2.25}{3} = \mathbf{0.7500}$
  - $\text{Accuracy} = \frac{1 + 2 + 5}{11} = \frac{8}{11} \approx \mathbf{0.727273} \implies \mathbf{0.7273}$ ($72.73\%$)

---

### Fold 4 Matrix ($N=10$ Held-Out Physical Specimens)
*Support: Aedes = 3, Anopheles = 2, Culex = 5*

$$\text{CM}_{\text{Fold 4}} = \begin{pmatrix} 3 & 0 & 0 \\ 0 & 2 & 0 \\ 0 & 0 & 5 \end{pmatrix}$$

* **Per-Class Metrics:**
  - Precision: Aedes = $1.0000$, Anopheles = $1.0000$, Culex = $1.0000$
  - Recall: Aedes = $1.0000$, Anopheles = $1.0000$, Culex = $1.0000$
  - F1-Score: Aedes = $1.0000$, Anopheles = $1.0000$, Culex = $1.0000$
* **Fold 4 Summary Metrics:**
  - $\text{Macro-F1} = \mathbf{1.0000}$
  - $\text{Balanced Accuracy} = \mathbf{1.0000}$
  - $\text{Accuracy} = \frac{10}{10} = \mathbf{1.0000}$ ($100.00\%$)

---

## 3. Cumulative Confusion Matrix Verification

Summing the reconstructed confusion matrices across all four folds yields:

$$\text{CM}_{\text{cumulative}} = \text{CM}_{\text{Fold 1}} + \text{CM}_{\text{Fold 2}} + \text{CM}_{\text{Fold 3}} + \text{CM}_{\text{Fold 4}}$$

$$\text{CM}_{\text{cumulative}} = \begin{pmatrix} 1 & 3 & 0 \\ 1 & 1 & 0 \\ 1 & 0 & 4 \end{pmatrix} + \begin{pmatrix} 4 & 0 & 0 \\ 0 & 3 & 0 \\ 0 & 0 & 5 \end{pmatrix} + \begin{pmatrix} 1 & 2 & 1 \\ 0 & 2 & 0 \\ 0 & 0 & 5 \end{pmatrix} + \begin{pmatrix} 3 & 0 & 0 \\ 0 & 2 & 0 \\ 0 & 0 & 5 \end{pmatrix} = \begin{pmatrix} 9 & 5 & 1 \\ 1 & 8 & 0 \\ 1 & 0 & 19 \end{pmatrix}$$

This matches the cumulative confusion matrix stored in `reports/v3_combined_experiments.json` (line 137) and transcribed in `reports/v3_combined_training_comparison.md` (line 121) identically.

---

## 4. Recalculation and Comparison: Mean Fold vs. Pooled Out-of-Fold

In multi-fold evaluation, two distinct averaging methodologies exist. Both are reported here to prevent ambiguity:

### Method 1: Mean Across Folds (Macro-Averaged Across Folds)
In this method, metric values are computed independently for each fold and averaged:
- **Mean Fold Macro-F1:**
  $$\overline{\text{Macro-F1}} = \frac{0.502646 + 1.000000 + 0.658586 + 1.000000}{4} = \frac{3.161231}{4} = \mathbf{0.790308} \implies \mathbf{0.7903}$$
  - Sample Standard Deviation ($s$, $ddof=1$): $\mathbf{0.2504}$
  - Population Standard Deviation ($\sigma$, $ddof=0$): $\mathbf{0.2168}$
- **Mean Fold Balanced Accuracy:**
  $$\overline{\text{BalAcc}} = \frac{0.516667 + 1.000000 + 0.750000 + 1.000000}{4} = \frac{3.266667}{4} = \mathbf{0.816667} \implies \mathbf{0.8167}$$
  - Sample Standard Deviation ($s$, $ddof=1$): $\mathbf{0.2321}$
- **Mean Fold Accuracy:**
  $$\overline{\text{Acc}} = \frac{0.545455 + 1.000000 + 0.727273 + 1.000000}{4} = \frac{3.272727}{4} = \mathbf{0.818182} \implies \mathbf{0.8182}$$

### Method 2: Pooled Out-of-Fold Evaluation (Micro-Aggregated Predictions)
In this method, all 44 held-out specimen predictions are pooled into the cumulative confusion matrix before computing precision, recall, and F1:
* **Pooled Precision:**
  - $\text{P}_{\text{Ae}} = \frac{9}{9 + 1 + 1} = \frac{9}{11} \approx 0.818182$ ($81.82\%$)
  - $\text{P}_{\text{An}} = \frac{8}{5 + 8 + 0} = \frac{8}{13} \approx 0.615385$ ($61.54\%$)
  - $\text{P}_{\text{Cx}} = \frac{19}{1 + 0 + 19} = \frac{19}{20} = 0.950000$ ($95.00\%$)
* **Pooled Recall:**
  - $\text{R}_{\text{Ae}} = \frac{9}{15} = 0.600000$ ($60.00\%$)
  - $\text{R}_{\text{An}} = \frac{8}{9} \approx 0.888889$ ($88.89\%$)
  - $\text{R}_{\text{Cx}} = \frac{19}{20} = 0.950000$ ($95.00\%$)
* **Pooled F1-Score:**
  - $\text{F1}_{\text{Ae}} = \frac{2 \times \frac{9}{11} \times \frac{3}{5}}{\frac{9}{11} + \frac{3}{5}} = \frac{54/55}{78/55} = \frac{9}{13} \approx 0.692308$ ($69.23\%$)
  - $\text{F1}_{\text{An}} = \frac{2 \times \frac{8}{13} \times \frac{8}{9}}{\frac{8}{13} + \frac{8}{9}} = \frac{128/117}{176/117} = \frac{8}{11} \approx 0.727273$ ($72.73\%$)
  - $\text{F1}_{\text{Cx}} = \frac{2 \times 0.95 \times 0.95}{0.95 + 0.95} = \frac{19}{20} = 0.950000$ ($95.00\%$)
* **Pooled Summary Metrics:**
  - **Pooled Macro-F1:**
    $$\text{Macro-F1}_{\text{pooled}} = \frac{\frac{9}{13} + \frac{8}{11} + \frac{19}{20}}{3} = \frac{0.692308 + 0.727273 + 0.950000}{3} = \frac{2.369580}{3} \approx \mathbf{0.789860} \implies \mathbf{0.7899}$$
  - **Pooled Balanced Accuracy:**
    $$\text{BalAcc}_{\text{pooled}} = \frac{0.600000 + 0.888889 + 0.950000}{3} = \frac{2.438889}{3} \approx \mathbf{0.812963} \implies \mathbf{0.8130}$$
  - **Overall Physical Accuracy:**
    $$\text{Acc}_{\text{pooled}} = \frac{9 + 8 + 19}{44} = \frac{36}{44} \approx \mathbf{0.818182} \implies \mathbf{0.8182} \quad (81.82\%)$$

### Summary Comparison Table

| Metric | Mean Across Folds | Pooled Out-of-Fold | Variance / Delta |
| :--- | :---: | :---: | :---: |
| **Macro-F1** | **$0.7903 \pm 0.2504$** | **$0.7899$** | $-0.0004$ ($-0.04$ pp) |
| **Balanced Accuracy** | **$0.8167 \pm 0.2321$** | **$0.8130$** | $-0.0037$ ($-0.37$ pp) |
| **Overall Accuracy** | **$81.82\%$** | **$81.82\%$** | $0.00$ pp (Exact match) |
| **Aedes Recall** | $62.50\%$ | $60.00\%$ | $-2.50$ pp |
| **Anopheles Recall** | $87.50\%$ | $88.89\%$ | $+1.39$ pp |
| **Culex Recall** | $95.00\%$ | $95.00\%$ | $0.00$ pp (Exact match) |

---

## 5. Investigation and Audit Conclusions

1. **Prediction Integrity:** The raw specimen predictions were not modified. The reconstructed per-fold matrices account for all 44 held-out specimens across the four folds without discrepancy.
2. **Mathematical Precision:** The reported numbers in `reports/v3_combined_experiments.json` ($0.5026$ and $0.6586$) are accurate roundings of $95/189$ and $326/495$.
3. **Recommendation for Scientific Reporting:** Both the mean fold Macro-F1 ($0.7903$) and pooled out-of-fold Macro-F1 ($0.7899$) must be documented side-by-side in all public and internal research records.
