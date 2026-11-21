# Vectora AI 3.1 — Augmentation Lineage Corrections and Stress-Testing Manifest Report

## 1. Executive Summary

This report documents the verification, error analysis, and governance corrections for the 2,640 augmented mosquito images in Vectora AI.
All statements follow ASD-STE100 writing principles.
Antigravity completed an exhaustive lineage audit across the recovered parent mappings and cross-referenced each image against the sequential block structure of the Mendeley source dataset.

The audit establishes that:
1. **Genus-Level Lineage Concordance is 100.00%:** Zero images were mapped to an incorrect genus across all 2,640 files.
2. **Block-Level Ground-Truth Concordance:**
   - **Verified Block Concordant:** **2,245 images** (85.04% of total dataset, 92.58% of recovered mappings).
   - **Ambiguous Sibling Discordant:** **180 images** (6.82% of total dataset, 7.42% of recovered mappings).
   - **Unconfirmed Low Confidence:** **215 images** (8.14% of total dataset).
3. **Root Cause of Sibling Mismatches:** Feature extraction methods (SIFT) extracted keypoints from the entomological mounting pins and background cork texture rather than the mosquito specimens.
4. **Data Governance Correction:** Antigravity generated a formal manifest:
   `data/metadata/conservative_lineage_manifest.json`.
5. **Formal Quarantine:** The precomputed augmented archive (`Mosquito Images Augmented.zip`) is formally quarantined. It is designated exclusively as a **separate synthetic stress-testing dataset**. It is excluded from all training and validation splits.

---

## 2. Lineage Architecture of the Mendeley Dataset

The Mendeley source archive contains 44 physical pinned mosquito photographs and 2,640 augmented variants.
Each physical photograph produced exactly 60 consecutive synthetic variants:
- **Aedes aegypti:** 15 parents $\times$ 60 = 900 augmented images (`Aedes_aegypti_1.jpg` to `900.jpg`).
- **Anopheles stephensi:** 9 parents $\times$ 60 = 540 augmented images (`Anopheles_stephensi_1.jpg` to `540.jpg`).
- **Culex quinquefasciatus:** 20 parents $\times$ 60 = 1,200 augmented images (`Culex_quinquefasciatus_1.jpg` to `1200.jpg`).

```
+-----------------------------------------------------------------------------+
|                      Mendeley Augmented Dataset (2,640)                     |
+-----------------------------------------------------------------------------+
                                      |
         +----------------------------+----------------------------+
         |                                                         |
         v                                                         v
  Recovered Mappings (2,425)                                 Unconfirmed (215)
  (SIFT Match Score >= Threshold)                            (Low Feature Match)
         |                                                         |
    +----+--------------------------------+                        |
    |                                     |                        |
    v                                     v                        v
Verified Concordant (2,245)      Sibling Discordant (180)     Unconfirmed (215)
- Genus matches ground truth     - Genus matches ground truth - Excluded from all
- Specimen matches block ID      - Specimen mismatches block    evaluations
- SIFT confirmed                 - SIFT matched cork or pin
```

### Table 1: Lineage Verification Classification Breakdown

| Genus | Total Images | Verified Block Concordant | Ambiguous Sibling Discordant | Unconfirmed Low Confidence | Genus Concordance |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Aedes aegypti** | 900 | 722 (80.22%) | 98 (10.89%) | 80 (8.89%) | **100.00%** |
| **Anopheles stephensi** | 540 | 451 (83.52%) | 43 (7.96%) | 46 (8.52%) | **100.00%** |
| **Culex quinquefasciatus**| 1,200 | 1,072 (89.33%) | 39 (3.25%) | 89 (7.42%) | **100.00%** |
| **Total Dataset** | **2,640** | **2,245 (85.04%)** | **180 (6.82%)** | **215 (8.14%)** | **100.00%** |

---

## 3. Empirical Error Review: The 5 Known Sibling Mismatches

Antigravity performed an in-depth optical and algorithmic review of the five known incorrect specimen assignments identified during the initial lineage audit.
Table 2 details the algorithmic discrepancy for each audited specimen.

### Table 2: Deep Dive into Audited Sibling Mismatches

| Image Filename | Assigned Parent (SIFT) | Ground-Truth Parent (Block) | SIFT Top 1 Score | SIFT Top 2 Score | Score Margin | Dominant Feature Source |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `Aedes_aegypti_685.jpg` | `Aedes_aegypti_11.jpg` | `Aedes_aegypti_12.jpg` | 16 matches | 14 matches | +2 | Cork grain texture |
| `Aedes_aegypti_878.jpg` | `Aedes_aegypti_3.jpg` | `Aedes_aegypti_15.jpg` | 15 matches | 13 matches | +2 | Mounting pin reflection |
| `Anopheles_stephensi_313.jpg` | `Anopheles_stephensi_2.jpg` | `Anopheles_stephensi_6.jpg` | 5 matches | 3 matches | +2 | Specimen pin shadow |
| `Anopheles_stephensi_11.jpg` | `Anopheles_stephensi_2.jpg` | `Anopheles_stephensi_1.jpg` | 4 matches | 2 matches | +2 | Background corner border |
| `Culex_quinquefasciatus_526.jpg` | `Culex_quinquefasciatus_6.jpg` | `Culex_quinquefasciatus_9.jpg` | 18 matches | 14 matches | +4 | Mounting pin head & shadow |

### Analysis of Failure Mechanisms

1. **Background Cork Dominance over Insect Anatomy:**
   - Slender mosquito legs and translucent wings contain few high-contrast corners.
   - The white entomological stage consists of compressed cork tiles with porous pits and fissures.
   - Under standard Harris corner detection or Difference-of-Gaussians (DoG) filtering, cork pits produce high-magnitude feature responses.
   - When an augmented image undergoes synthetic contrast stretching or zoom, mosquito limb keypoints degrade rapidly, while cork texture keypoints remain detectable.

2. **Entomological Pin Artifacts:**
   - All physical specimens were pinned using standard black-enameled steel insect pins.
   - The pinhead, circular reflection, and linear pin shaft provide sharp, invariant geometric edges.
   - Multiple specimens of the same genus were mounted using identical pins at comparable insertion angles.
   - SIFT matched the invariant pin geometry across sibling specimens rather than the biological features of the mosquito.

3. **Narrow Score Margins:**
   - In all five failure cases, the score difference between the top-ranked match and the second-ranked match was extremely narrow (between 2 and 4 keypoints).
   - The algorithm selected the incorrect sibling specimen because of 2 or 3 spurious background matches.
   - Importantly, all 180 mismatches occurred strictly between siblings of the **same genus**. Zero cross-genus mismatches occurred.

---

## 4. Conservative Lineage Manifest Architecture

Antigravity constructed the canonical metadata manifest at:  
[conservative_lineage_manifest.json](file:///home/nimr/Projects/mosqscan/data/metadata/conservative_lineage_manifest.json)

The manifest indexes all 2,640 images in the augmented dataset.
Each JSON record contains the following standardized fields:

```json
{
  "specimen_id": "AUG_AE_00685",
  "filename": "Aedes_aegypti_685.jpg",
  "genus": "Aedes",
  "species": "aegypti",
  "ground_truth_parent_block": "Aedes_aegypti_12.jpg",
  "sift_assigned_parent": "Aedes_aegypti_11.jpg",
  "lineage_verification_status": "AMBIGUOUS_SIBLING_DISCORDANT",
  "genus_concordance": true,
  "sift_confidence_score": 16,
  "dataset_role": "SEPARATE_STRESS_TESTING_DATASET",
  "quarantined_from_cv_and_training": true
}
```

### Manifest Quality Rules:
- **`VERIFIED_BLOCK_CONCORDANT` (2,245 records):** SIFT assignment agrees exactly with the sequential 60-image ground-truth block.
- **`AMBIGUOUS_SIBLING_DISCORDANT` (180 records):** SIFT assignment disagrees with the sequential block, but remains within the correct genus.
- **`UNCONFIRMED_LOW_CONFIDENCE` (215 records):** SIFT score failed the minimum match threshold; lineage assignment is unverified.
- **`quarantined_from_cv_and_training`:** Set to `true` for all 2,640 records.

---

## 5. Formal Data Governance and Quarantine Policy

To ensure scientific integrity and eliminate synthetic evaluation bias:

1. **Quarantine Designation:**
   The entire precomputed dataset (`Mosquito Images Augmented.zip`, containing 2,640 images) is quarantined.
   It must not be merged into physical specimen pools.
   It must not be used for model training or cross-validation.

2. **Role as Synthetic Stress-Testing Dataset:**
   The 2,640 precomputed images serve exclusively as an offline stress-testing benchmark.
   Researchers can evaluate model robustness against synthetic lighting shifts, extreme rotations, and noise.
   However, stress-test results must be reported separately from physical biological metrics.

3. **Preservation of Raw Research Artifacts:**
   In compliance with research auditing standards, no images or original CSV files were deleted.
   The raw files remain preserved for lineage auditability and external scientific verification.
