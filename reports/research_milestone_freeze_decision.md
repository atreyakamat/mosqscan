# Vectora AI — Research Milestone Freeze and Governance Decision

**Document Target:** Formal Freezing of Development Evaluations and Field Release Governance  
**Active Production Model:** `models/vectora_v3_fp32.onnx` (SHA-256: `c3a3656f746a1bb2e7ac428e44670d89cf51f0d0f923ad3aa15420e8a4592cfa`)  
**Provisional Research Leader:** Experiment B (Unweighted Precomputed Augmentations)  
**Standard:** ASD-STE100 Simplified Technical English  
**Date:** 2026-11-13  
**Status:** Approved & Formally Locked  

---

## 1. Executive Summary

This document establishes the formal consensus and freeze decision for the Vectora AI research program.
The scientific evaluation across the 44 original biological specimens is formally concluded.
No further training iterations, hyperparameter adjustments, or resubstitution evaluations will occur on the current development dataset.

### Consensus Release Decisions:

| System Component | Research Status | Operational Decision | Technical Governance Rule |
| :--- | :--- | :--- | :--- |
| **Experiment B** | Provisional Research Leader | **Retain as Research Baseline** | Pooled Macro-F1: $0.7899$, Accuracy: $81.82\%$ ($36/44$). Highest reported performance. |
| **Primary Hybrid Model** | Evaluation Candidate | **Retain for Comparison** | Pooled Macro-F1: $0.7611$, Accuracy: $79.55\%$ ($35/44$). Did not outperform Experiment B. |
| **Class-Weighted Hybrid**| Ablation Candidate | **Retain as Ablation Reference**| Anopheles recall reached $88.89\%$, but overall Macro-F1 dropped to $0.7432$. |
| **Extended 8-Epoch Model**| Defective Evaluation | **Promotion Prohibited** | $100\%$ accuracy claim formally withdrawn; classified as training resubstitution. |
| **Production Server Model**| Active Inference Service | **Maintain in Production** | `models/vectora_v3_fp32.onnx` remains active on port 8000. Checksum locked. |
| **Gemma 3 Local Assistant**| Local AI Research Service | **Available On Demand** | Docker profile `llm` (port 11435) available for advisory tasks; decoupled from inference. |
| **Android Field Release** | Production Mobile Client | **Locked Release** | Communicates with active i7-2600 server. Client code and assets preserved. |
| **Larvae Classification** | Experimental / Inactive | **Locked / Unvalidated** | Excluded from active inference routes and production serving. |

---

## 2. Key Scientific Findings

1. **Experimental Ceiling on 44 Physical Specimens:**
   Adding online dynamic transforms during hybrid training did not produce an accuracy gain over static precomputed augmentations. Primary hybrid training correctly classified 35 of 44 specimens ($79.55\%$), while Experiment B correctly classified 36 of 44 specimens ($81.82\%$).
2. **Sensitivity vs. Precision Trade-off in Class Weighting:**
   Class weighting successfully elevated *Anopheles* recall to **$88.89\%$** ($8/9$), matching Experiment B. However, the increased penalty on false negatives caused six *Aedes* specimens to be misclassified as *Anopheles*, lowering overall balanced accuracy and Macro-F1.
3. **Data Saturation:**
   The 44 biological parent specimens in the Mendeley repository are statistically saturated. Continued model training on this fixed cohort risks severe overfitting and produces no actionable insight regarding real-world field reliability.

---

## 3. Inventory of Frozen Artifacts

Table 2 documents the exact SHA-256 hashes for all frozen research and production artifacts.

### Table 2: Authoritative Artifact Hash Registry

| Artifact Path | SHA-256 Checksum | Classification |
| :--- | :--- | :--- |
| [`models/vectora_v3_fp32.onnx`](file:///home/nimr/Projects/mosqscan/models/vectora_v3_fp32.onnx) | `c3a3656f746a1bb2e7ac428e44670d89cf51f0d0f923ad3aa15420e8a4592cfa` | **Active Production Model** |
| [`models/research/hybrid_unweighted_fold1.pt`](file:///home/nimr/Projects/mosqscan/models/research/hybrid_unweighted_fold1.pt) | `9559bb29c0a6b73ebf0367eb7826359bebe3ba03cb117ea7ea79815c48b26c2e` | Primary Hybrid Checkpoint Fold 1 |
| [`models/research/hybrid_unweighted_fold2.pt`](file:///home/nimr/Projects/mosqscan/models/research/hybrid_unweighted_fold2.pt) | `0e9cb20387b32810fb5cfc66c30f40df8374d6c41b8c0d1e1fa63bc64b971c26` | Primary Hybrid Checkpoint Fold 2 |
| [`models/research/hybrid_unweighted_fold3.pt`](file:///home/nimr/Projects/mosqscan/models/research/hybrid_unweighted_fold3.pt) | `b9f5647565985ae08ef61cb56bb76d75508b534d0263f350cbe43b4685ff8614` | Primary Hybrid Checkpoint Fold 3 |
| [`models/research/hybrid_unweighted_fold4.pt`](file:///home/nimr/Projects/mosqscan/models/research/hybrid_unweighted_fold4.pt) | `d0fbc705a61fc08c7908b8b082ae0d65a88c3a1e2850901e687e14dbe10ec7ce` | Primary Hybrid Checkpoint Fold 4 |
| [`models/research/hybrid_weighted_fold1.pt`](file:///home/nimr/Projects/mosqscan/models/research/hybrid_weighted_fold1.pt) | `532e013a778c13b28b7470f5e1a3bcda4ecf90117fc040715aa31fe829672eb1` | Ablation Checkpoint Fold 1 |
| [`models/research/hybrid_weighted_fold2.pt`](file:///home/nimr/Projects/mosqscan/models/research/hybrid_weighted_fold2.pt) | `99d9b626f228b3234d7fb37caeb591a134a6ca024b4249a4f6d482cf187ea131` | Ablation Checkpoint Fold 2 |
| [`models/research/hybrid_weighted_fold3.pt`](file:///home/nimr/Projects/mosqscan/models/research/hybrid_weighted_fold3.pt) | `e24391ea114feebfd67c9c0b1ef380b263e7c85aa882c42b5839257e8aa6878b` | Ablation Checkpoint Fold 3 |
| [`models/research/hybrid_weighted_fold4.pt`](file:///home/nimr/Projects/mosqscan/models/research/hybrid_weighted_fold4.pt) | `d95856755490ff4908920199e69315dff722fe1fa8a7c29759e0a0ee449bc2b8` | Ablation Checkpoint Fold 4 |
| [`reports/extended_model_grouped_evaluation_results.json`](file:///home/nimr/Projects/mosqscan/reports/extended_model_grouped_evaluation_results.json) | `45050f4625b0cb5030ddf4ffea4a485fa6b785e68ce0e3c54c34a2e83163098d` | Machine-Readable Predictions & Metrics |
| [`reports/experiment_b_specimen_prediction_reconciliation.md`](file:///home/nimr/Projects/mosqscan/reports/experiment_b_specimen_prediction_reconciliation.md) | `5a74581577a7b83ec5515228bc96dcf5a73e1666e63286da12d6a50352ef135f` | Specimen Reconciliation Matrix |

---

## 4. Next Phase Roadmap: External Validation Protocol

The development team must focus exclusively on the five milestones below:

1. **Physical Specimen Collection Campaign:**
   Collect wild-caught and laboratory-reared specimens across diverse geographic regions, natural ambient lighting conditions, and specimen conditions (intact, damaged, engorged, desiccated). Confirm all species classifications with entomological microscopy or PCR assays.
2. **Locked External Test Dataset:**
   Curate an external test set containing at least 200 independently verified biological specimens. Maintain this dataset strictly offline and locked. Do not use this set for training, fine-tuning, validation stopping, or hyperparameter selection.
3. **Out-of-Distribution & Rejection Benchmarking:**
   Implement formal confidence calibration (temperature scaling) and non-vector rejection thresholds. Measure precision on non-mosquito insects, debris, blurred captures, and non-target culicine genera.
4. **Field Latency Profiling:**
   Profile end-to-end inference latency under actual image-classification workloads on the Intel Core i7-2600 host while concurrent container processes run.
5. **Operational Release Gate:**
   Promote candidate models only after achieving verified superiority on the locked external test dataset and passing the operational quality gate.
