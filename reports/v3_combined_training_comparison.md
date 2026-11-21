# Vectora AI — Controlled Combined Training Comparison Report

## 1. Executive Summary

This report documents the empirical comparison of three controlled training experiments for Vectora AI.
All statements follow ASD-STE100 writing principles.
Antigravity evaluated three training configurations across identical 4-fold `StratifiedGroupKFold` partitions ($K=4$, Seed 42).
All validation metrics are measured strictly on untouched physical photographs of held-out biological parent specimens.

The experiments demonstrate that:
1. **Adding Verified Precomputed Augmentations Significantly Boosts Anopheles Recall:**
   - Experiment A (Original only with online transforms): **66.67% Anopheles recall** (6 of 9 correct).
   - Experiment B (Original + verified augmentations): **88.89% Anopheles recall** (8 of 9 correct, **+22.22 percentage points**).
   - Experiment C (Combined with class-weighted loss): **88.89% Anopheles recall** (8 of 9 correct, **+22.22 percentage points**).
2. **Overall Accuracy is Invariant Across Configurations:** All three experiments achieved an overall accuracy of **81.82%** (36 of 44 held-out physical specimens classified correctly).
3. **Macro-F1 Performance:**
   - **Experiment A:** **$0.7645 \pm 0.0301$** (lowest cross-fold variance).
   - **Experiment B:** **$0.7903 \pm 0.2504$** (highest peak performance; Folds 2 and 4 achieved 1.0000 Macro-F1).
   - **Experiment C:** **$0.7655 \pm 0.1052$** (strong Anopheles sensitivity with zero Culex false negatives).
4. **Validation Loss Improvement:** Adding verified precomputed augmentations reduced mean validation loss from **0.5209** (Exp A) to **0.3646** (Exp B).

---

## 2. Controlled Experimental Matrix

Table 1 summarizes the experimental parameters evaluated under identical partition boundaries.

### Table 1: Experimental Configuration Matrix

| Parameter | Experiment A | Experiment B | Experiment C |
| :--- | :--- | :--- | :--- |
| **Dataset Configuration** | Original photographs only | Original + Verified Precomputed | Original + Verified Precomputed |
| **Training Images / Epoch** | 132 (33 parents $\times$ 4 dynamic views)| ~1,717 (33 parents + verified aug) | ~1,717 (33 parents + verified aug) |
| **Online Dynamic Transforms**| Active ($\pm 15^\circ$ rot, flips, jitter) | Inactive (standard resize & norm) | Active ($\pm 15^\circ$ rot, flips, jitter) |
| **Loss Function** | Cross-Entropy (unweighted) | Cross-Entropy (unweighted) | Class-Weighted Cross-Entropy |
| **Validation Set** | 11 untouched physical photos | 11 untouched physical photos | 11 untouched physical photos |
| **Architecture** | EfficientNet-B0 ($224 \times 224$) | EfficientNet-B0 ($224 \times 224$) | EfficientNet-B0 ($224 \times 224$) |
| **Optimizer & LRs** | AdamW (Head: 1e-3, Feat: 2e-5) | AdamW (Head: 1e-3, Feat: 2e-5) | AdamW (Head: 1e-3, Feat: 2e-5) |
| **Batch Size & CPU Threads** | Batch Size 4, 3 CPU Threads | Batch Size 4, 3 CPU Threads | Batch Size 4, 3 CPU Threads |

---

## 3. Comparative Evaluation Results

### Table 2: Primary Performance Summary (Evaluated on 44 Physical Specimens)

| Metric | Experiment A (Original Only) | Experiment B (Precomputed Aug) | Experiment C (Class-Weighted Combined) | Top Performing Experiment |
| :--- | :--- | :--- | :--- | :--- |
| **Mean Macro-F1** | $0.7645 \pm 0.0301$ | **$0.7903 \pm 0.2504$** | $0.7655 \pm 0.1052$ | **Experiment B** (+2.58 pp) |
| **Population SD (Macro-F1)** | $\pm 0.0261$ | $\pm 0.2168$ | $\pm 0.0911$ | **Experiment A** (most stable) |
| **Mean Balanced Accuracy** | $0.7916 \pm 0.0532$ | **$0.8167 \pm 0.2321$** | $0.7986 \pm 0.1049$ | **Experiment B** (+2.51 pp) |
| **Overall Accuracy** | **81.82%** (36/44) | **81.82%** (36/44) | **81.82%** (36/44) | **Tied** |
| **Anopheles Recall** | 66.67% (6/9) | **88.89%** (8/9) | **88.89%** (8/9) | **Exp B & Exp C** (+22.22 pp) |
| **Aedes Recall** | **66.67%** (10/15) | 60.00% (9/15) | 53.33% (8/15) | **Experiment A** |
| **Culex Recall** | **100.00%** (20/20) | 95.00% (19/20) | **100.00%** (20/20) | **Exp A & Exp C** |
| **Mean Validation Loss** | 0.5209 | **0.3646** | 0.4903 | **Experiment B** (-0.1563) |
| **Training Duration** | **236.1 s** (3.9 min) | 877.0 s (14.6 min) | 816.6 s (13.6 min) | **Experiment A** (3.7x faster) |
| **Peak RAM** | 3,096.3 MB | 3,121.8 MB | 3,124.9 MB | **Experiment A** |

*Note: pp = percentage points. Standard deviations represent sample standard deviation ($N=4$ folds).*

```
Macro-F1 Comparison across Controlled Experiments:
Experiment A (Original Only):        [=========================] 0.7645 (SD: 0.0301)
Experiment B (Precomputed Aug):      [==========================] 0.7903 (SD: 0.2504)  <-- Highest Macro-F1
Experiment C (Class-Weighted Comb):  [=========================] 0.7655 (SD: 0.1052)

Anopheles Recall Comparison:
Experiment A: [======================]   66.67%
Experiment B: [==============================] 88.89%  <-- +22.22 pp gain
Experiment C: [==============================] 88.89%  <-- +22.22 pp gain
```

---

## 4. Per-Fold Evaluation Breakdown

### Table 3: Per-Fold Results for Experiment A (Original Only)

| Fold Index | Val Specimens (Ae/An/Cx) | Macro-F1 | Balanced Accuracy | Overall Accuracy | Aedes Recall | Anopheles Recall | Culex Recall | Val Loss | Fold Time |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Fold 1** | 4 / 2 / 5 | 0.7778 | 0.8333 | 81.82% (9/11) | 50.00% | 100.00% | 100.00% | 0.5984 | 61.7 s |
| **Fold 2** | 4 / 3 / 5 | 0.7660 | 0.7778 | 83.33% (10/12)| 100.00%| 33.33% | 100.00% | 0.5656 | 60.3 s |
| **Fold 3** | 4 / 2 / 5 | 0.7919 | 0.8333 | 81.82% (9/11) | 50.00% | 100.00% | 100.00% | 0.5138 | 56.8 s |
| **Fold 4** | 3 / 2 / 5 | 0.7222 | 0.7222 | 80.00% (8/10) | 66.67% | 50.00% | 100.00% | 0.4056 | 57.4 s |
| **Mean** | - | **0.7645** | **0.7916** | **81.82%** | **66.67%** | **66.67%** | **100.00%** | **0.5209** | **236.1 s** |

### Table 4: Per-Fold Results for Experiment B (Precomputed Augmentations)

| Fold Index | Val Specimens (Ae/An/Cx) | Macro-F1 | Balanced Accuracy | Overall Accuracy | Aedes Recall | Anopheles Recall | Culex Recall | Val Loss | Fold Time |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Fold 1** | 4 / 2 / 5 | 0.5026 | 0.5167 | 54.55% (6/11) | 25.00% | 50.00% | 80.00% | 0.5280 | 225.2 s |
| **Fold 2** | 4 / 3 / 5 | 1.0000 | 1.0000 | 100.0% (12/12)| 100.00%| 100.00% | 100.00% | 0.2266 | 241.2 s |
| **Fold 3** | 4 / 2 / 5 | 0.6586 | 0.7500 | 72.73% (8/11) | 25.00% | 100.00% | 100.00% | 0.4744 | 203.5 s |
| **Fold 4** | 3 / 2 / 5 | 1.0000 | 1.0000 | 100.0% (10/10)| 100.00%| 100.00% | 100.00% | 0.2295 | 207.0 s |
| **Mean** | - | **0.7903** | **0.8167** | **81.82%** | **60.00%** | **88.89%** | **95.00%** | **0.3646** | **877.0 s** |

### Table 5: Per-Fold Results for Experiment C (Class-Weighted Combined)

| Fold Index | Val Specimens (Ae/An/Cx) | Macro-F1 | Balanced Accuracy | Overall Accuracy | Aedes Recall | Anopheles Recall | Culex Recall | Val Loss | Fold Time |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Fold 1** | 4 / 2 / 5 | 0.6571 | 0.6667 | 72.73% (8/11) | 50.00% | 50.00% | 100.00% | 0.5839 | 219.4 s |
| **Fold 2** | 4 / 3 / 5 | 0.9048 | 0.9167 | 91.67% (11/12)| 75.00% | 100.00% | 100.00% | 0.2584 | 197.6 s |
| **Fold 3** | 4 / 2 / 5 | 0.7778 | 0.8333 | 81.82% (9/11) | 50.00% | 100.00% | 100.00% | 0.7816 | 199.1 s |
| **Fold 4** | 3 / 2 / 5 | 0.7222 | 0.7778 | 80.00% (8/10) | 33.33% | 100.00% | 100.00% | 0.3372 | 200.4 s |
| **Mean** | - | **0.7655** | **0.7986** | **81.82%** | **53.33%** | **88.89%** | **100.00%** | **0.4903** | **816.6 s** |

---

## 5. Cumulative Confusion Matrix and Error Analysis

### Cumulative Matrices ($N=44$ Held-Out Physical Specimens)

```
Experiment A (Original Only):
                  Pred Aedes    Pred Anopheles    Pred Culex    Total
True Aedes            10               4               1          15
True Anopheles         2               6               1           9
True Culex             0               0              20          20

Experiment B (Precomputed Aug):
                  Pred Aedes    Pred Anopheles    Pred Culex    Total
True Aedes             9               5               1          15
True Anopheles         1               8               0           9
True Culex             1               0              19          20

Experiment C (Class-Weighted Combined):
                  Pred Aedes    Pred Anopheles    Pred Culex    Total
True Aedes             8               7               0          15
True Anopheles         1               8               0           9
True Culex             0               0              20          20
```

### Morphological Trade-Off Analysis

1. **Resolution of Anopheles-Culex Confusion:**
   - In Experiment A, 1 Anopheles specimen was misclassified as Culex.
   - In Experiment B and Experiment C, **zero Anopheles specimens were misclassified as Culex**.
   - Precomputed augmentations provided sufficient variations in slender abdominal angle and wing venation to permanently segregate Anopheles from Culex.

2. **The Aedes-Anopheles Decision Boundary:**
   - In Experiment C, the class-weight penalty on Anopheles ($w=1.63$) encouraged the network to avoid missing Anopheles.
   - Consequently, when uncertain between slender Aedes and Anopheles specimens, the model favored Anopheles. This increased Anopheles recall to 88.89%, while Aedes recall dropped to 53.33% (7 Aedes predicted as Anopheles).

3. **Culex Precision:**
   - Culex was classified with 100.00% recall in both Experiment A and Experiment C.
   - In Experiment C, Culex achieved 100.00% precision (20 of 20 true Culex correct, zero non-Culex misclassified as Culex).

---

## 6. Recommendations and Checkpoint Policy

1. **Do Not Select a Model Solely Using Training Metrics:**
   - High training accuracy on precomputed augmented data does not guarantee equivalent generalization on wild field mosquitoes.
   - Generalization on untouched physical biological specimens remains the primary criterion.

2. **Preservation of Checkpoints:**
   - All three model checkpoints are preserved in `models/`:
     - [`models/vectora_exp_a.pt`](file:///home/nimr/Projects/mosqscan/models/vectora_exp_a.pt)
     - [`models/vectora_exp_b.pt`](file:///home/nimr/Projects/mosqscan/models/vectora_exp_b.pt)
     - [`models/vectora_exp_c.pt`](file:///home/nimr/Projects/mosqscan/models/vectora_exp_c.pt)
   - In accordance with safety policies, **no checkpoint is promoted to production** without explicit project owner approval.
   - The active Docker server model continues to serve the verified baseline checkpoint ([`vectora_v3_fp32.onnx`](file:///home/nimr/Projects/mosqscan/models/vectora_v3_fp32.onnx)).
