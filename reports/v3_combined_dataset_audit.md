# Vectora AI — Combined Dataset Audit Report

## 1. Executive Summary

This report documents the combined dataset audit for Vectora AI.
All statements follow ASD-STE100 writing principles.
Antigravity completed an empirical audit of the original physical specimen photographs and the precomputed augmented dataset.

The audit establishes that:
1. **Biological Specimen Count is 44:** The dataset contains exactly 44 independent biological specimens. Augmented images are synthetic variants of these 44 specimens and are not independent biological entities.
2. **Exclusion of Unconfirmed and Ambiguous Lineages:**
   - **215 images** with low-confidence SIFT matching were strictly excluded.
   - **180 images** with ambiguous sibling-discordant mappings were strictly excluded.
   - **2,245 images** with verified block-concordant parent mappings were approved for training.
3. **Total Verified Image Pool:** **2,289 images** (44 original physical photographs + 2,245 verified precomputed augmentations).
4. **Partitioning Rule:** Partitions are grouped strictly by original biological specimen ID. Every derivative image remains in the same partition as its parent specimen.
5. **Validation Integrity:** Validation partitions contain only untouched physical photographs. Zero synthetic augmentations are applied to validation specimens.

---

## 2. Dataset Architecture and Lineage Segregation

The repository contains two image sources:
- `Mosquito Images Original`: 44 high-resolution physical photographs ($3000 \times 4000$ and $1944 \times 2592$).
- `Mosquito Images Augmented`: 2,640 synthetic transform variants ($256 \times 256$).

```
+-----------------------------------------------------------------------------+
|                         Combined Image Dataset (2,684)                      |
+-----------------------------------------------------------------------------+
                                      |
         +----------------------------+----------------------------+
         |                                                         |
         v                                                         v
  Original Photographs (44)                                Augmented Images (2,640)
  (15 Aedes, 9 Anopheles, 20 Culex)                        (900 Aedes, 540 Anopheles, 1200 Culex)
         |                                                         |
         |                                    +--------------------+--------------------+
         |                                    |                                         |
         |                                    v                                         v
         |                         Verified Concordant (2,245)                 Excluded Images (395)
         |                         - Lineage confirmed by block               - 215 Low confidence
         |                         - Approved for training                    - 180 Sibling discordant
         |                                    |                                         |
         +------------------------------------+                                         v
                                      |                                         Quarantined
                                      v                                         (Stress Test Only)
                         Verified Pool (2,289 Images)
                         (Derived from 44 Parents)
```

### Table 1: Dataset Composition and Lineage Audit Breakdown

| Mosquito Genus | Biological Parent Specimens | Original Physical Photos | Precomputed Augmented (Total) | Verified Block Concordant (Included) | Unconfirmed Low Confidence (Excluded) | Ambiguous Sibling Discordant (Excluded) | Total Verified Pool |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Culex** | 20 | 20 | 1,200 | 1,081 (90.1%) | 80 (6.7%) | 39 (3.2%) | **1,101** |
| **Aedes** | 15 | 15 | 900 | 685 (76.1%) | 117 (13.0%) | 98 (10.9%) | **700** |
| **Anopheles** | 9 | 9 | 540 | 479 (88.7%) | 18 (3.3%) | 43 (8.0%) | **488** |
| **Total** | **44** | **44** | **2,640** | **2,245 (85.0%)**| **215 (8.1%)** | **180 (6.8%)** | **2,289** |

---

## 3. Strict Partitioning and Leakage Prevention

To ensure zero biological specimen leakage between training and evaluation splits, Antigravity applied `StratifiedGroupKFold`:
- **Grouping Key:** Biological Specimen ID (1 to 44).
- **Repetitions:** 4 folds with fixed random seed (`seed=42`).
- **Constraint:** All 60 augmented variants of parent specimen $X$ are assigned to the exact same partition as parent photograph $X$.
- **Validation Protocol:** Validation splits contain strictly untouched physical photographs. No synthetic augmentations exist in validation splits.

### Table 2: 4-Fold Stratified Group Partitions

| Partition Index | Training Parents | Training Images (Phys + Aug) | Validation Parents | Validation Physical Photos (Untouched) | Class Support (Ae / An / Cx) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Partition 1** | 33 | 1,728 | 11 | 11 | 4 Aedes, 2 Anopheles, 5 Culex |
| **Partition 2** | 32 | 1,700 | 12 | 12 | 4 Aedes, 3 Anopheles, 5 Culex |
| **Partition 3** | 33 | 1,712 | 11 | 11 | 4 Aedes, 2 Anopheles, 5 Culex |
| **Partition 4** | 34 | 1,727 | 10 | 10 | 3 Aedes, 2 Anopheles, 5 Culex |
| **Total** | - | - | **44** | **44** | **15 Aedes, 9 Anopheles, 20 Culex** |

*Note: Partitions are identical across all controlled experiments (Exp A, Exp B, and Exp C).*

---

## 4. Safety Requirements Compliance Verification

Table 3 confirms compliance with each safety requirement specified for combined dataset training.

### Table 3: Safety Compliance Checklist

| Safety Requirement | Specification | Implementation Verification | Compliance |
| :--- | :--- | :--- | :--- |
| **Preserve Original Data** | Do not delete or modify original photos | All 44 original photographs preserved in raw directory | **COMPLIANT** |
| **Preserve Augmented Data**| Do not delete augmented photos | All 2,640 augmented files preserved intact | **COMPLIANT** |
| **Biological Independence** | Do not count augmentations as specimens | Specimen count is fixed at 44 biological specimens | **COMPLIANT** |
| **Exclude Unconfirmed** | Remove 215 low-confidence images | 215 unconfirmed images strictly filtered from training | **COMPLIANT** |
| **Exclude Ambiguous** | Exclude 180 sibling discordant images | 180 ambiguous mappings strictly filtered from training | **COMPLIANT** |
| **Grouped Partitions** | Group by physical specimen ID | `StratifiedGroupKFold` applied on parent ID | **COMPLIANT** |
| **Validation Hygiene** | Zero augmentations in validation | Validation folds evaluate untouched raw photographs only | **COMPLIANT** |
| **Identical Partitions** | Identical test splits for Exp A, B, C | Exact same 4 partitions evaluated across all experiments | **COMPLIANT** |
| **CPU Constraints** | Intel i7-2600 limits respected | 3 CPU threads, batch size 4, 0 workers, AVX only | **COMPLIANT** |
| **Server Protection** | Do not overwrite active server model | Active model (`vectora_v3_fp32.onnx`) preserved untouched | **COMPLIANT** |
