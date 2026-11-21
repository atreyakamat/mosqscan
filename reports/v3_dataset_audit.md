# Vectora AI 3.0 — Dataset Audit and Quality Inspection Report

**Date:** 2026-11-12  
**Standard:** ASD-STE100  
**Status:** Complete  

---

## 1. Executive Summary

This report documents the verification, extraction, and quality audit of the original and augmented mosquito image archives for Vectora AI 3.0.

All 44 original photographs and 2,640 synthetic augmented photographs were verified against archive checksums, decoded, profiled for blur and luminance, audited for exact duplicates, and mapped for specimen provenance.

---

## 2. Archive Verification and Extraction

### 2.1 File Identifiers and Integrity

| Archive Name | File Size (Bytes) | SHA-256 Checksum | Extraction Directory |
| :--- | :--- | :--- | :--- |
| `Mosquito Images Original.zip` | 115,031,594 | `41321f35150a8c6af8144803311739c1c340f41a3e51d0474878902eaf568ff8` | `data/staging/original` |
| `Mosquito Images Augmented.zip` | 60,066,399 | `b635531e05ecb99f25ec96bc820fd01e31c5ba560370b6332d7d7475f0612636` | `data/staging/augmented` |

Both archives were preserved in their original locations without modification. Copies were extracted into isolated staging paths.

### 2.2 Specimen Counts by Genus

| Genus | Original Photographs | Augmented Photographs | Ratio (Augmented : Original) |
| :--- | :--- | :--- | :--- |
| **Aedes** (*Aedes aegypti*) | 15 | 900 | 60.0 : 1 |
| **Anopheles** (*Anopheles stephensi*) | 9 | 540 | 60.0 : 1 |
| **Culex** (*Culex quinquefasciatus*) | 20 | 1,200 | 60.0 : 1 |
| **Total** | **44** | **2,640** | **60.0 : 1** |

The image counts match the expected dataset architecture exactly.

---

## 3. Augmentation Provenance Recovery

### 3.1 Provenance Pipeline Architecture

The augmented images in `Mosquito Images Augmented.zip` use sequential filenames (for example `Aedes_aegypti_1.jpg` to `Aedes_aegypti_900.jpg`) and do not identify the source specimen in file metadata.

A multi-stage provenance recovery pipeline was executed:
1. **Perceptual Hashing (pHash):** Calculated 64-bit DCT-based perceptual hashes for each original and augmented image.
2. **Scale-Invariant Feature Transform (SIFT):** Extracted scale and rotation invariant keypoints and local descriptors.
3. **Descriptor Matching (BFMatcher with Lowe's Ratio Test):** Matched descriptors between augmented images and candidate originals within the same genus using $k=2$ and distance ratio $< 0.75$.
4. **Margin Verification:** Computed the margin between the best-matching original specimen and the runner-up specimen.

### 3.2 Provenance Results

The complete lineage mapping is recorded in `data/metadata/augmentation_lineage.csv`.

| Genus | Total Augmented | Verified Parent Lineage | High Confidence | Medium Confidence | Low Confidence (Unconfirmed) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Aedes** | 900 | 783 (87.0%) | 571 | 212 | 117 (13.0%) |
| **Anopheles** | 540 | 522 (96.7%) | 435 | 87 | 18 (3.3%) |
| **Culex** | 1,200 | 1,120 (93.3%) | 986 | 134 | 80 (6.7%) |
| **Total** | **2,640** | **2,425 (91.86%)** | **1,992** | **433** | **215 (8.14%)** |

### 3.3 Training Data Policy Enforcement

In accordance with strict dataset leakage prevention rules:
- **Verified Augmentations (2,425 images):** Permitted for training fold augmentation only when their assigned parent specimen is in the training fold.
- **Unconfirmed Augmentations (215 images):** Excluded from model training. Retained strictly for separate stress testing.
- **Validation Fold Isolation:** Validation folds use strictly clean, original photographs. No synthetic augmentations are added to validation sets.

Visual contact sheets showing original specimens alongside verified augmented children are saved in:
- `data/metadata/contact_sheets/contact_sheet_aedes.png`
- `data/metadata/contact_sheets/contact_sheet_anopheles.png`
- `data/metadata/contact_sheets/contact_sheet_culex.png`

---

## 4. Image Quality and Integrity Audit

All 2,684 image files (44 original + 2,640 augmented) were audited for decoding integrity, dimensions, blur, and exposure. Detailed row-by-row metrics are recorded in `data/metadata/data_quality_metrics.csv`.

### 4.1 Summary of Quality Metrics

| Metric | Original Photographs (44) | Augmented Photographs (2,640) |
| :--- | :--- | :--- |
| **Decoding Success (PIL & OpenCV)** | 44 / 44 (100%) | 2,640 / 2,640 (100%) |
| **Corruption Rate** | 0% | 0% |
| **Dimensions** | 3000 × 4000 pixels (high-resolution) | 256 × 256 pixels |
| **Color Space** | RGB (3-channel) | RGB (3-channel) |
| **Blur Score (Laplacian Variance)** | Mean: 218.4 (Min: 48.2, Max: 592.1) | Mean: 112.6 (Min: 18.4, Max: 412.0) |
| **Severe Blur ($< 15.0$)** | 0 images (0%) | 0 images (0%) |
| **Mean Luminance** | 210.5 / 255 (Clean white laboratory background) | 198.2 / 255 |
| **Exact Duplicate SHA-256 Collisions** | 0 collisions | 0 collisions |

### 4.2 Duplicate Detection

A full SHA-256 collision sweep was conducted across all 2,684 extracted files.
- Exact duplicates detected: 0.
- Every original photograph and synthetic variation has a distinct cryptographic hash.
- Full collision log is stored in `data/metadata/duplicate_report.csv`.

---

## 5. Audit Conclusions

1. **Integrity Verified:** All original and augmented archives are intact and match stated image counts.
2. **Provenance Restored:** 91.86% of synthetic augmentations have been mapped to specific parent specimens using feature matching.
3. **Leakage Prevented:** Specimen-level group isolation is established. All 215 unconfirmed synthetic variations are excluded from training.
4. **Separation of Workflows:** Adult mosquito photographs remain completely separate from larvae video analysis.
