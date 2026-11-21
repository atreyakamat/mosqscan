# Vectora AI 3.0 — Dataset Processing Results

**Date:** 2026-11-12  
**Standard:** ASD-STE100  
**Status:** Complete  

---

## 1. Overview

This document presents the final quantitative results of the dataset extraction, lineage recovery, and quality inspection workflows for Vectora AI 3.0.

---

## 2. Ingestion and Extraction Results

| Category | Ingested Files | Verified Decodable | Dimensions | Channels | Storage Path |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Original Specimens** | 44 | 44 (100%) | 3000 × 4000 | 3 (RGB) | `data/staging/original/Original Images Mendeley/` |
| **Augmented Variations** | 2,640 | 2,640 (100%) | 256 × 256 | 3 (RGB) | `data/staging/augmented/` |
| **Total Images Processed** | **2,684** | **2,684 (100%)** | — | — | — |

---

## 3. Augmentation Lineage Distribution

The recovery pipeline mapped 2,425 augmented images to parent specimens with high or medium confidence. 215 images fell below confidence thresholds and were designated unconfirmed.

```
+-------------------------------------------------------------------------+
|                      Augmented Dataset (2,640 images)                   |
+------------------------------------+------------------------------------+
|   Verified Lineage (2,425 images)  |   Unconfirmed Lineage (215 images) |
|   - Aedes: 783                     |   - Aedes: 117                     |
|   - Anopheles: 522                 |   - Anopheles: 18                  |
|   - Culex: 1,120                   |   - Culex: 80                      |
|   Status: Used in training folds   |   Status: EXCLUDED from training   |
+------------------------------------+------------------------------------+
```

### Lineage Mapping Metrics

- **Matching Algorithm:** SIFT Local Invariant Features + FLANN/BFMatcher + Perceptual Hash (pHash).
- **Average Keypoints per Augmented Image:** 64.3.
- **Top-1 to Top-2 Match Ratio Margin:** Mean margin 8.4 matches.
- **Lineage Verification File:** `data/metadata/augmentation_lineage.csv`.
- **Quality Manifest File:** `data/metadata/dataset_manifest.json`.

---

## 4. Quality Inspection Metrics

- **Mean Laplacian Blur Variance:**
  - Original images: $218.4 \pm 78.2$
  - Augmented images: $112.6 \pm 41.5$
  - Blurry images ($< 15.0$ variance): 0 (0%)
- **Exposure Quality:**
  - Mean luminance: $204.3$ / 255
  - Severe underexposure ($< 20$): 0%
  - Severe overexposure ($> 245$): 0%
- **Exact Duplicate Collisions:** 0 across all 2,684 files.

All data quality gates have passed without exception.
