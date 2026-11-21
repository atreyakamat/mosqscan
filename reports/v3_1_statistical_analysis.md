# Vectora AI 3.1 — Statistical Analysis and Significance Qualification Report

## 1. Executive Summary

This report reviews the statistical comparison methodology across cross-validation runs in Vectora AI.
All statements follow ASD-STE100 writing principles.
Antigravity evaluated the statistical significance tests used to select the primary adult mosquito classifier (`efficientnet_b0`, $224 \times 224$).

The statistical audit establishes that:
1. **Fold Non-Independence:** The eight evaluation folds across seeds 42 and 1337 share training and test specimens. The observations violate the independence assumption of the standard Student's paired $t$-test.
2. **Variance Underestimation:** A standard paired $t$-test on repeated cross-validation severely underestimates standard error. It inflates Type I error rates (false discovery rate).
3. **Nadeau-Bengio (2003) Correction Applied:** Antigravity applied the corrected resampled $t$-test formula with test-to-training ratio $\frac{n_{\text{test}}}{n_{\text{train}}} = \frac{11}{33} = 0.3333$.
4. **Recalculated Significance:**
   - **Candidate 1 (EffNet-B0 224) vs. Candidate 3 (MobileNet-V3):** The uncorrected $t = 5.010$ ($p = 0.0015$) corrects to **$t = 2.617$ ($p = 0.0345$, $df = 7$)**. The difference remains statistically significant at $\alpha = 0.05$, but with realistic confidence bounds.
   - **Candidate 1 (EffNet-B0 224) vs. Candidate 2 (EffNet-B0 384):** The uncorrected $t = 0.417$ ($p = 0.6893$) corrects to **$t = 0.218$ ($p = 0.8338$, $df = 7$)**. No statistically significant difference exists between resolutions.
5. **Scientific Reporting Policy:** Vectora AI 3.1 treats model differences descriptively rather than claiming unconditional statistical superiority.

---

## 2. The Overlapping Fold Independence Problem

In cross-validation experiments, researchers frequently test whether model architecture $A$ outperforms architecture $B$.
A common error is to apply Student's paired $t$-test directly to the per-fold metrics.

### Why Standard Paired $t$-Tests Fail on Cross-Validation (Dietterich, 1998)

1. **Shared Training Specimens:**
   In 4-fold cross-validation, any two training splits share $\frac{4-2}{4-1} = \frac{2}{3}$ (66.7%) of their training specimens.
   The resulting models are structurally dependent because they learn from largely identical weights and data points.

2. **Shared Validation Specimens Across Seeds:**
   When cross-validation is repeated across multiple seeds (Seed 42 and Seed 1337), each of the 44 physical specimens is evaluated twice.
   The test sets are not independent samples from an infinite population; they are the same physical objects evaluated under different model initializations.

3. **Artificially Deflated Variance:**
   Because repeated fold differences are positively correlated, the sample variance of the differences $S^2$ underestimates the true variance of the generalization error.
   This inflates the test statistic $t$ and produces artificially low $p$-values, leading to false claims of statistical superiority.

---

## 3. The Nadeau-Bengio (2003) Corrected Resampled $t$-Test

To account for the covariance between overlapping training and test splits, Nadeau and Bengio (2003) derived the corrected variance estimator for $R$ repetitions of $K$-fold cross-validation.

### Mathematical Formulation

Let $J = K \times R = 4 \times 2 = 8$ evaluation folds.
Let $d_j = M_{1, j} - M_{2, j}$ represent the performance difference (Macro-F1) on fold $j$.
The sample mean difference $\bar{d}$ and sample variance $S^2$ are:

$$\bar{d} = \frac{1}{J} \sum_{j=1}^J d_j$$

$$S^2 = \frac{1}{J-1} \sum_{j=1}^J (d_j - \bar{d})^2$$

The standard (uncorrected) variance of the mean is:

$$\sigma_{\text{uncorrected}}^2 = \frac{S^2}{J} = \frac{S^2}{8} = 0.125 \cdot S^2$$

The Nadeau-Bengio corrected variance introduces the ratio of test set size ($n_{\text{test}} = 11$) to training set size ($n_{\text{train}} = 33$):

$$\sigma_{\text{corrected}}^2 = \left( \frac{1}{J} + \frac{n_{\text{test}}}{n_{\text{train}}} \right) S^2$$

$$\sigma_{\text{corrected}}^2 = \left( \frac{1}{8} + \frac{11}{33} \right) S^2 = (0.1250 + 0.3333) \cdot S^2 = 0.4583 \cdot S^2$$

### Standard Error Inflation Factor

The ratio of corrected standard error to uncorrected standard error is:

$$\frac{\text{SE}_{\text{corrected}}}{\text{SE}_{\text{uncorrected}}} = \sqrt{\frac{0.4583}{0.1250}} = \sqrt{3.6667} \approx 1.9148$$

The true standard error is **1.915 times larger** than the standard formula assumes.
The corrected $t$-statistic is computed with degrees of freedom $df = J - 1 = 7$:

$$t_{\text{corrected}} = \frac{\bar{d}}{\sqrt{\left(\frac{1}{J} + \frac{n_{\text{test}}}{n_{\text{train}}}\right) S^2}} = \frac{t_{\text{uncorrected}}}{1.9148}$$

---

## 4. Comprehensive Candidate Comparison Analysis

Antigravity recalculated the statistical comparisons between Candidate 1 (`effnet_b0_224`), Candidate 2 (`effnet_b0_384`), and Candidate 3 (`mobilenet_v3_224`).

### Table 1: Comparative Significance Testing Matrix ($J=8$ Folds, $df=7$)

| Comparison | Mean Difference ($\bar{d}$) | Sample SD ($S$) | Uncorrected $t$ | Uncorrected $p$-value | Corrected $t_{\text{NB}}$ | Corrected $p$-value | Statistical Conclusion |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **EffNet-B0 224 vs. MobileNet-V3 224** | $+0.3282$ (+32.82 pp) | $0.1853$ | $5.010$ | $p = 0.0015$ | **$2.617$** | **$p = 0.0345$** | Statistically significant ($\alpha=0.05$) |
| **EffNet-B0 224 vs. EffNet-B0 384** | $+0.0427$ (+4.27 pp) | $0.2894$ | $0.417$ | $p = 0.6893$ | **$0.218$** | **$p = 0.8338$** | Not statistically significant |
| **EffNet-B0 384 vs. MobileNet-V3 224** | $+0.2855$ (+28.55 pp) | $0.1982$ | $4.074$ | $p = 0.0047$ | **$2.128$** | **$p = 0.0708$** | Marginally significant ($p > 0.05$) |

*Note: pp = percentage points. All comparisons use Macro-F1 across 8 repeated cross-validation folds.*

```
Paired Comparison t-Statistics:
Candidate 1 vs Candidate 3:
  Uncorrected: [==================================================] t = 5.010 (p = 0.0015)
  Corrected:   [==========================]                         t = 2.617 (p = 0.0345) <-- Valid

Candidate 1 vs Candidate 2:
  Uncorrected: [====] t = 0.417 (p = 0.6893)
  Corrected:   [==]   t = 0.218 (p = 0.8338) <-- No statistical difference
```

---

## 5. Architectural Selection Rationale

While Candidate 1 and Candidate 2 show no statistically significant accuracy difference ($p = 0.8338$), engineering constraints strongly favor Candidate 1 (`efficientnet_b0` at $224 \times 224$):

1. **Computational Latency on Host Hardware:**
   - Candidate 1 ($224 \times 224$): **27.29 ms** median latency in ONNX Runtime FP32 on the Intel Core i7-2600.
   - Candidate 2 ($384 \times 384$): **84.50 ms** median latency (3.1 times slower).
   - The $224 \times 224$ input preserves server responsiveness under concurrent mobile field uploads.

2. **Container Memory Footprint:**
   - Candidate 1 uses approximately one-third of the activation buffer memory compared to Candidate 2.
   - The entire Docker deployment occupies only **33.71 MiB** of RAM on the host server.

3. **Field Generalization Parity:**
   - Both models suffer identical failure modes when classifying raw, uncropped physical photographs.
   - Increasing input resolution without biological region proposal (YOLO) provides negligible F1 improvement (+4.27 percentage points, non-significant).

---

## 6. Uncertainty Reporting and Scientific Restraint

Antigravity establishes the following principles for model evaluations in Vectora AI:

1. **Do Not Claim Statistical Superiority from Laboratory Pinned Data:**
   - An evaluation of 44 pinned specimens collected from a single laboratory colony cannot establish operational superiority for wild mosquito surveillance.
   - The $p$-value ($p = 0.0345$) establishes that EfficientNet-B0 learns the laboratory dataset better than MobileNet-V3. It does not establish clinical or field diagnostic reliability.

2. **Always State Uncertainty Intervals:**
   - The 95% confidence interval for the Macro-F1 difference between EfficientNet-B0 and MobileNet-V3 using corrected variance is:
     $$\Delta \text{Macro-F1} = +0.3282 \pm (2.365 \times 0.1254) = +0.3282 \pm 0.2966 \quad [0.0316, 0.6248]$$
   - The wide confidence interval reflects the small sample size ($N=44$ physical specimens).

3. **Treat Differences Descriptively:**
   - Model comparisons must be framed as empirical observations under controlled experimental conditions, not absolute claims of diagnostic efficacy.
