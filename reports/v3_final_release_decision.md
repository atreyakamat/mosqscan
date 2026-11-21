# Vectora AI 3.0 — Final Release Decision and Field Deployment Audit

## 1. Release Recommendation

**Release Status:** `APPROVED FOR CONTROLLED INTERNAL RESEARCH TESTING (v3.0.0-RC1)`  
**Production Status:** `WITHHELD — NOT APPROVED FOR CLINICAL OR EPIDEMIOLOGICAL RELEASE`  
**Regulatory Identifier:** `EXPERIMENTAL_NOT_FIELD_VALIDATED`  

Antigravity conducted the comprehensive Vectora AI 3.0 release audit.
All statements follow ASD-STE100 writing principles.
The software engineering architecture is complete, robust, and verified.
However, because model performance remains constrained by the 44-specimen laboratory dataset (balanced accuracy of 68.47% vs. the 92.00% PRD target), production approval is withheld.
The platform is approved exclusively for controlled internal research and field specimen collection.

---

## 2. Release Gate Verification Matrix

| Release Gate | PRD Requirement | Vectora AI 3.0 Result | Status |
| :--- | :--- | :--- | :--- |
| **Backend API Contract** | Reconciled REST API with OpenAPI spec | 28 endpoints verified, FastAPI production | **PASSED** |
| **Server AI Inference** | Host FP32 inference on Intel Core i7-2600 | 27.29 ms median latency, ONNX Runtime C++ | **PASSED** |
| **Memory Footprint** | Host container stack $< 500$ MB | **33.71 MiB** total container memory | **PASSED** |
| **Android APK Hygiene** | Zero models or ONNX runtimes in mobile APK | 0 `.onnx` files, 0 native libraries in APK | **PASSED** |
| **Offline Queuing** | Safe local storage, zero synthetic predictions | Room DB persistence, status `PENDING_UPLOAD` | **PASSED** |
| **Synchronization** | Reliable LAN upload and result return | Roundtrip 231 ms, verified on Galaxy Tab A7 Lite | **PASSED** |
| **Lineage Integrity** | Elimination of cross-fold data leakage | Grouped K-Fold by parent, 0 cross-fold leakage | **PASSED** |
| **Adult Model Balanced Accuracy**| $\ge 92.00\%$ balanced accuracy | **$68.47\% \pm 21.97\%$** | **FAILED (Blocked)** |
| **Statistical Superiority** | Validated candidate selection | Superior to MobileNet ($p=0.0015$); 224x224 chosen | **PASSED** |
| **Field Generalization** | Validated on damaged wild specimens | Laboratory specimens only (pinned, white background) | **FAILED (Blocked)** |

---

## 3. Cross-Validation and Statistical Superiority Summary

Antigravity audited all eight repeated cross-validation folds across two random seeds (`seed=42` and `seed=1337`).

### Cross-Validation Metrics Table

| Model Architecture | Input Resolution | Macro-F1 (Mean $\pm$ SD) | Balanced Accuracy (Mean $\pm$ SD) | Anopheles Recall (Mean $\pm$ SD) | Latency (PyTorch) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Candidate 1: EfficientNet-B0** | **224 $\times$ 224** | **$0.6527 \pm 0.2293$** | **$0.6847 \pm 0.2197$** | **$0.7500 \pm 0.3780$** | **56.79 ms** |
| **Candidate 2: EfficientNet-B0** | 384 $\times$ 384 | $0.6100 \pm 0.1448$ | $0.6639 \pm 0.0948$ | $0.6042 \pm 0.3666$ | 176.42 ms |
| **Candidate 3: MobileNet-V3** | 224 $\times$ 224 | $0.3245 \pm 0.0793$ | $0.4361 \pm 0.0739$ | $0.2083 \pm 0.2921$ | 48.91 ms |

*Note: Standard deviations represent sample standard deviation ($N=8$ fold runs).*

```
Macro-F1 Performance Distribution across Folds:
Candidate 1 (EffNet-B0 224): [=========================] 0.6527 (SD: 0.2293)  <-- Selected
Candidate 2 (EffNet-B0 384): [=======================]   0.6100 (SD: 0.1448)
Candidate 3 (MobileNet-V3):  [============]             0.3245 (SD: 0.0793)
```

### Paired Comparison Significance Analysis

1. **Candidate 1 (`effnet_b0_224`) vs. Candidate 3 (`mobilenet_v3_224`):**
   - Mean Difference: $+0.3282$ (+32.82 percentage points).
   - Paired Student's $t$-statistic: $t = 5.010$.
   - Two-tailed $p$-value: $p = 0.0015$.
   - **Conclusion:** Candidate 1 is statistically superior to MobileNet-V3 ($p < 0.01$).
2. **Candidate 1 (`effnet_b0_224`) vs. Candidate 2 (`effnet_b0_384`):**
   - Mean Difference: $+0.0427$ (+4.27 percentage points).
   - Paired Student's $t$-statistic: $t = 0.417$.
   - Two-tailed $p$-value: $p = 0.6893$.
   - **Conclusion:** The difference is **not statistically significant**.
   - **Selection Justification:** Candidate 1 is selected because it delivers **3.1x lower computational overhead** (56.79 ms vs. 176.42 ms in PyTorch, 27.29 ms in ONNX Runtime) and simpler input pipeline requirements.

---

## 4. Key Limitations Preventing Production Release

Three scientific and epidemiological limitations prevent unrestricted release:

1. **Dataset Specimen Paucity:**
   - The entire training dataset derives from only **44 pinned laboratory specimens** (15 Aedes, 9 Anopheles, 20 Culex).
   - Folds containing difficult Anopheles specimens suffer severe performance drops (F1 varies between 0.31 and 0.94 across folds).
   - The model has not observed morphological variations across geographic populations.
2. **Artificial Laboratory Artifacts:**
   - All photographs depict intact, pinned specimens on uniform white backgrounds with controlled studio lighting.
   - Real-world surveillance collects crushed, descaled, legless, or fragmented specimens on diverse surfaces (traps, cloth, soil).
3. **Uncalibrated Softmax Probabilities:**
   - Model confidence values represent raw uncalibrated softmax scores.
   - Softmax scores can show overconfidence on out-of-distribution inputs.

---

## 5. Mandatory Deployment Guardrails Active in 3.0

To ensure safe controlled usage, the following safeguards are enforced in code:

1. **Mandatory Disclaimer Tag:**
   - Every API prediction JSON, mobile screen, and web report displays:
     > `status: "EXPERIMENTAL_NOT_FIELD_VALIDATED"`
     > *"Raw softmax output is an uncalibrated experimental heuristic. Visual identification only. Not field-validated for epidemiological decisions."*
2. **Certainty Threshold Gating ($\tau = 0.65$):**
   - Predictions with $\max(P) < 0.65$ set `is_uncertain = True`.
   - The UI displays an explicit warning and suppresses definitive action.
3. **Zero Local Synthetic Predictions:**
   - The Android client creates no dummy or estimated classifications when offline.
   - Captures remain in Room database with `PENDING_UPLOAD` until verified by the host server.
4. **Architectural Separation of Adult and Larvae Pipelines:**
   - Adult classifier strictly processes static photographs.
   - Larvae analysis strictly processes 3–5s video clips with meniscus tracking.

---

## 6. Action Plan for Version 3.1 Production Qualification

To achieve production approval in release 3.1, the project must complete:

1. **Multi-Center Specimen Expansion:**
   - Collect and annotate at least 200 distinct specimens per genus from multiple field locations.
   - Include damaged, wild-caught, and trap-collected specimens.
2. **Probability Calibration:**
   - Implement temperature scaling or Platt scaling on a quarantined calibration set.
3. **Double-Blind Entomological Validation Trial:**
   - Benchmark model predictions against blinded expert entomologist microscopic examinations.

---

## 7. Final Decision

Vectora AI 3.0 is approved for **Internal Research Testing (v3.0.0-RC1)**.
All production deployments for public health interventions remain withheld until field dataset expansion and clinical validation.
