# Vectora AI — Evaluation Integrity Audit & Metric Reconciliation Report

**Date:** 2026-11-11  
**Auditor:** Senior Software Quality & ML Evaluation Engineer (Antigravity)  
**Target:** Independent Audit of 5 Controlled Fine-Tuning Experiments  
**Dataset:** Mendeley Data v4 (44 physical specimens partitioned into disjoint partitions)  

---

## 1. Specimen Isolation & Partition Integrity Audit

Every physical photograph in `data/splits.csv` is traced to a unique `specimen_id` and assigned to exactly one partition:

* **Train Partition ($N=32$ specimens):**
  * `Aedes` ($11$): `Aedes_aegypti_1`, `10`, `11`, `12`, `13`, `14`, `4`, `5`, `6`, `7`, `9`
  * `Anopheles` ($7$): `Anopheles_stephensi_1`, `2`, `3`, `4`, `5`, `6`, `8`
  * `Culex` ($14$): `Culex_quinquefasciatus_1`, `10`, `12`, `13`, `14`, `15`, `16`, `18`, `2`, `3`, `6`, `7`, `8`, `9`
* **Validation Partition ($N=6$ specimens):**
  * `Aedes` ($2$): `Aedes_aegypti_15`, `Aedes_aegypti_2`
  * `Anopheles` ($1$): `Anopheles_stephensi_9`
  * `Culex` ($3$): `Culex_quinquefasciatus_11`, `Culex_quinquefasciatus_19`, `Culex_quinquefasciatus_20`
* **Held-Out Test Partition ($N=6$ specimens):**
  * `Aedes` ($2$): `Aedes_aegypti_3`, `Aedes_aegypti_8`
  * `Anopheles` ($1$): `Anopheles_stephensi_7`
  * `Culex` ($3$): `Culex_quinquefasciatus_17`, `Culex_quinquefasciatus_4`, `Culex_quinquefasciatus_5`

### Disjointness Verification
* $\text{Train} \cap \text{Validation} = \emptyset$ (0 overlap)
* $\text{Train} \cap \text{Test} = \emptyset$ (0 overlap)
* $\text{Validation} \cap \text{Test} = \emptyset$ (0 overlap)

> [!IMPORTANT]
> **Cardinal Evaluation Rule:**
> Training, validation, and held-out test predictions must **never be pooled into a single combined metric**. Reporting a pooled "All 44" metric obscures overfitting, mixes in-sample training samples with out-of-sample data, and violates evaluation integrity. All subsequent analyses evaluate each partition in complete isolation.

---

## 2. Investigation of Reported Macro-F1 Discrepancies

The user audit flagged two mathematical discrepancies in the previous report:
1. **Baseline Macro-F1:** Reported as `0.611` vs. recalculated from the text confusion matrix as `0.609`.
2. **Weighted Macro-F1:** Reported as `0.698` vs. recalculated from the text confusion matrix as `0.707`.

### Root-Cause Analysis
The discrepancy originated from a transcription divergence between the **actual saved model checkpoint outputs** (which were logged into `experiments/all_experiments_comparison.json`) and the **manually formatted text tables** in Section 4 of the previous report.

#### Discrepancy 1: Baseline Experiment
* **Actual Checkpoint Predictions:**
  $$\text{CM}_{\text{actual}} = \begin{pmatrix} 13 & 1 & 1 \\ 4 & 1 & 4 \\ 1 & 0 & 19 \end{pmatrix}$$
  $$\text{Precision}: \text{Ae}=\frac{13}{18}=0.7222, \quad \text{An}=\frac{1}{2}=0.5000, \quad \text{Cx}=\frac{19}{24}=0.7917$$
  $$\text{Recall}: \text{Ae}=\frac{13}{15}=0.8667, \quad \text{An}=\frac{1}{9}=0.1111, \quad \text{Cx}=\frac{19}{20}=0.9500$$
  $$\text{F1}: \text{Ae}=0.7879, \quad \text{An}=0.1818, \quad \text{Cx}=0.8636$$
  $$\text{Macro-F1} = \frac{0.7879 + 0.1818 + 0.8636}{3} = \mathbf{0.6111} \implies \mathbf{0.611}$$
* **Transcribed Text Draft:**
  $$\text{CM}_{\text{transcribed}} = \begin{pmatrix} 13 & 0 & 2 \\ 7 & 1 & 1 \\ 1 & 0 & 19 \end{pmatrix}$$
  $$\text{F1}: \text{Ae}=\frac{2 \times 0.6190 \times 0.8667}{0.6190 + 0.8667}=0.7222, \quad \text{An}=0.2000, \quad \text{Cx}=0.9048$$
  $$\text{Macro-F1} = \frac{0.7222 + 0.2000 + 0.9048}{3} = \mathbf{0.6090} \implies \mathbf{0.609}$$
* **Finding:** The table reported `0.611` directly from the code tensor output, but the text table transcribed an earlier draft matrix yielding `0.609`.

#### Discrepancy 2: Weighted Experiment
* **Actual Checkpoint Predictions:**
  $$\text{CM}_{\text{actual}} = \begin{pmatrix} 13 & 1 & 1 \\ 4 & 3 & 2 \\ 1 & 1 & 18 \end{pmatrix}$$
  $$\text{Precision}: \text{Ae}=\frac{13}{18}=0.7222, \quad \text{An}=\frac{3}{5}=0.6000, \quad \text{Cx}=\frac{18}{21}=0.8571$$
  $$\text{Recall}: \text{Ae}=\frac{13}{15}=0.8667, \quad \text{An}=\frac{3}{9}=0.3333, \quad \text{Cx}=\frac{18}{20}=0.9000$$
  $$\text{F1}: \text{Ae}=0.7879, \quad \text{An}=0.4286, \quad \text{Cx}=0.8780$$
  $$\text{Macro-F1} = \frac{0.7879 + 0.4286 + 0.8780}{3} = \mathbf{0.6982} \implies \mathbf{0.698}$$
* **Transcribed Text Draft:**
  $$\text{CM}_{\text{transcribed}} = \begin{pmatrix} 13 & 0 & 2 \\ 5 & 3 & 1 \\ 2 & 0 & 18 \end{pmatrix}$$
  $$\text{F1}: \text{Ae}=0.7429, \quad \text{An}=0.5000, \quad \text{Cx}=0.8780$$
  $$\text{Macro-F1} = \frac{0.7429 + 0.5000 + 0.8780}{3} = \mathbf{0.7070} \implies \mathbf{0.707}$$
* **Finding:** Similarly, the table reported `0.698` from the exact checkpoint, but the text section transcribed a matrix that recalculates to `0.707`.

> [!CAUTION]
> Both metrics suffered from the underlying defect of **pooling training, validation, and test sets**. Neither 0.611 nor 0.698 represents an honest generalization score. Below, all metrics are strictly segregated by partition.

---

## 3. Checkpoint & Configuration Verification

All 5 experiment checkpoints saved in `experiments/` were audited against their configuration and weights:

| Checkpoint Name | Checkpoint File | Trainable Parameters | Mode | Class-Weighted Loss Applied |
|---|---|:---:|:---:|:---:|
| `exp_A_frozen_baseline` | `exp_A_frozen_baseline_best.pt` | 3,843 (0.10%) | `frozen` | **No** (Unweighted) |
| `exp_B_unfreeze_stage7_8`| `exp_B_unfreeze_stage7_8_best.pt` | 1,133,235 (28.25%) | `stage7_8` | **No** (Unweighted) |
| `exp_C_unfreeze_stages5_8`| `exp_C_unfreeze_stages5_8_best.pt`| 3,702,731 (92.31%) | `stages5_8` | **No** (Unweighted) |
| `exp_B_weighted_stage7_8`| `exp_B_weighted_stage7_8_best.pt` | 1,133,235 (28.25%) | `stage7_8` | **Yes** (Training only) |
| `exp_C_weighted_stages5_8`| `exp_C_weighted_stages5_8_best.pt`| 3,702,731 (92.31%) | `stages5_8` | **Yes** (Training only) |

* **Verification:** Class weights ($w_{aedes}=0.9697, w_{anopheles}=1.5238, w_{culex}=0.7619$) were computed **strictly from the training partition** and applied solely to the loss function during gradient descent. Evaluation of validation and test splits used standard unweighted CrossEntropy and standard unweighted macro averaging.

---

## 4. Partition-Separated Evaluation Audit (Fixed Class Ordering: Aedes, Anopheles, Culex)

### Confusion Matrix Layout
All matrices adhere to the exact class order:
$$\begin{pmatrix} 
\text{True Aedes} \to \text{Pred Ae} & \text{True Aedes} \to \text{Pred An} & \text{True Aedes} \to \text{Pred Cx} \\
\text{True Anopheles} \to \text{Pred Ae} & \text{True Anopheles} \to \text{Pred An} & \text{True Anopheles} \to \text{Pred Cx} \\
\text{True Culex} \to \text{Pred Ae} & \text{True Culex} \to \text{Pred An} & \text{True Culex} \to \text{Pred Cx}
\end{pmatrix}$$

---

### A. Training Partition Evaluation ($N=32$)
*Support: Aedes = 11, Anopheles = 7, Culex = 14*

| Experiment | Accuracy | Macro-F1 | Aedes (P / R / F1) | Anopheles (P / R / F1) | Culex (P / R / F1) | Confusion Matrix |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Exp A (Frozen)** | 68.8% | 0.5208 | 0.69 / 0.82 / 0.75 | 0.00 / 0.00 / 0.00 | 0.72 / 0.93 / 0.81 | `[[9, 1, 1], [3, 0, 4], [1, 0, 13]]` |
| **Exp B (Unfreeze 7–8)** | 62.5% | 0.5355 | 0.59 / 0.91 / 0.71 | 0.33 / 0.14 / 0.20 | 0.75 / 0.64 / 0.69 | `[[10, 1, 0], [3, 1, 3], [4, 1, 9]]` |
| **Exp C (Unfreeze 5–8)** | 62.5% | 0.5355 | 0.59 / 0.91 / 0.71 | 0.33 / 0.14 / 0.20 | 0.75 / 0.64 / 0.69 | `[[10, 1, 0], [3, 1, 3], [4, 1, 9]]` |
| **Exp B-Weighted** | **75.0%** | **0.6722** | 0.69 / 0.82 / 0.75 | **0.67 / 0.29 / 0.40** | 0.81 / 0.93 / 0.87 | `[[9, 1, 1], [3, 2, 2], [1, 0, 13]]` |
| **Exp C-Weighted** | **75.0%** | **0.6722** | 0.69 / 0.82 / 0.75 | **0.67 / 0.29 / 0.40** | 0.81 / 0.93 / 0.87 | `[[9, 1, 1], [3, 2, 2], [1, 0, 13]]` |

---

### B. Validation Partition Evaluation ($N=6$)
*Support: Aedes = 2, Anopheles = 1, Culex = 3*

| Experiment | Accuracy | Macro-F1 | Aedes (P / R / F1) | Anopheles (P / R / F1) | Culex (P / R / F1) | Confusion Matrix |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Exp A (Frozen)** | 83.3% | 0.6000 | 0.67 / 1.00 / 0.80 | 0.00 / 0.00 / 0.00 | 1.00 / 1.00 / 1.00 | `[[2, 0, 0], [1, 0, 0], [0, 0, 3]]` |
| **Exp B (Unfreeze 7–8)** | 83.3% | **0.6190** | 1.00 / 1.00 / 1.00 | 0.00 / 0.00 / 0.00 | 0.75 / 1.00 / 0.86 | `[[2, 0, 0], [0, 0, 1], [0, 0, 3]]` |
| **Exp C (Unfreeze 5–8)** | 83.3% | **0.6190** | 1.00 / 1.00 / 1.00 | 0.00 / 0.00 / 0.00 | 0.75 / 1.00 / 0.86 | `[[2, 0, 0], [0, 0, 1], [0, 0, 3]]` |
| **Exp B-Weighted** | 83.3% | 0.6000 | 0.67 / 1.00 / 0.80 | 0.00 / 0.00 / 0.00 | 1.00 / 1.00 / 1.00 | `[[2, 0, 0], [1, 0, 0], [0, 0, 3]]` |
| **Exp C-Weighted** | 83.3% | 0.6000 | 0.67 / 1.00 / 0.80 | 0.00 / 0.00 / 0.00 | 1.00 / 1.00 / 1.00 | `[[2, 0, 0], [1, 0, 0], [0, 0, 3]]` |

*Note on Validation Anopheles:* In all 5 experiments, the single validation *Anopheles* specimen (`Anopheles_stephensi_9`) was misclassified (either as Aedes or Culex). Because support = 1, validation Anopheles recall is 0.00 across the board.

---

### C. Held-Out Test Partition Evaluation ($N=6$)
*Support: Aedes = 2, Anopheles = 1, Culex = 3*  
*(Strictly held-out; never accessed during hyperparameter selection, early stopping, or weight tuning)*

| Experiment | Accuracy | Macro-F1 | Aedes (P / R / F1) | Anopheles (P / R / F1) | Culex (P / R / F1) | Confusion Matrix |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Exp A (Frozen)** | **100.0%** | **1.0000** | 1.00 / 1.00 / 1.00 | **1.00 / 1.00 / 1.00** | 1.00 / 1.00 / 1.00 | `[[2, 0, 0], [0, 1, 0], [0, 0, 3]]` |
| **Exp B (Unfreeze 7–8)** | 83.3% | 0.6000 | 0.67 / 1.00 / 0.80 | 0.00 / 0.00 / 0.00 | 1.00 / 1.00 / 1.00 | `[[2, 0, 0], [1, 0, 0], [0, 0, 3]]` |
| **Exp C (Unfreeze 5–8)** | 83.3% | 0.6000 | 0.67 / 1.00 / 0.80 | 0.00 / 0.00 / 0.00 | 1.00 / 1.00 / 1.00 | `[[2, 0, 0], [1, 0, 0], [0, 0, 3]]` |
| **Exp B-Weighted** | 83.3% | **0.8222** | 1.00 / 1.00 / 1.00 | **0.50 / 1.00 / 0.67** | 1.00 / 0.67 / 0.80 | `[[2, 0, 0], [0, 1, 0], [0, 1, 2]]` |
| **Exp C-Weighted** | 83.3% | **0.8222** | 1.00 / 1.00 / 1.00 | **0.50 / 1.00 / 0.67** | 1.00 / 0.67 / 0.80 | `[[2, 0, 0], [0, 1, 0], [0, 1, 2]]` |

---

## 5. Statistical Validity & PRD Acceptance Audit

### Why Exp A's "1.0000 Test Macro-F1" is an Illusion of Small Sample Size
In Experiment A, the test macro-F1 is mathematically recorded as **1.0000** (all 6 specimens correctly classified: 2 Aedes, 1 Anopheles, 3 Culex).  
However:
1. On the **Training partition** ($N=32$), Exp A achieved an Anopheles recall of **0.00%** (0 out of 7 specimens identified!).
2. On the **Validation partition** ($N=6$), Exp A achieved an Anopheles recall of **0.00%** (0 out of 1 specimen identified).
3. The single test *Anopheles* specimen (`Anopheles_stephensi_7`) happened to land on the correct side of the linear classification hyperplane by chance.
4. When evaluated across the 2,640 augmented images from this dataset, Exp A achieved an Anopheles recall of only **20.6%**.
5. Claiming that Exp A has "100% accuracy" or has "exceeded the PRD target" would be fraudulent and scientifically invalid.

### Conclusion on the PRD 92% Macro-F1 Target
* **PRD Requirement:** Adult identification macro-F1 $\ge 92\%$.
* **Audit Finding:** **NO experiment can honestly claim to have achieved the PRD target.**
* **Scientific Reality:** With only 1 Anopheles specimen in the test partition, a 95% confidence interval for Anopheles recall spans $[5\%, 100\%]$. True validation requires an independent test benchmark of at least **150–200 physical specimens per genus** collected under real-world conditions.
