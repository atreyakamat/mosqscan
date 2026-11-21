# Vectora AI 3.1 — Release Status and Acceptance Audit Report

## 1. Executive Release Recommendation

**Release Title:** `v3.0.0-RC1 — CONTROLLED INTERNAL RESEARCH`  
**Production Release Status:** `WITHHELD — NOT APPROVED FOR CLINICAL, EPIDEMIOLOGICAL, OR AUTONOMOUS FIELD USE`  
**Mandatory Status Tag:** `EXPERIMENTAL_NOT_FIELD_VALIDATED`  
**Audit Date:** 2026-11-12  

Antigravity completed the final scientific validation audit for Vectora AI 3.0.0-RC1.
All statements follow ASD-STE100 writing principles.

### Summary Statement
The software engineering platform is production-ready, fully dockerized, and verified across all end-to-end integration flows.
However, scientific validation on raw biological specimens demonstrates that the adult mosquito identification model achieves a **Macro-F1 of $50.23\%$**, which falls **41.77 percentage points below the PRD target of $92.00\%$**.
Therefore, production approval for autonomous field surveillance is withheld.
The platform is authorized strictly as an **internal research and specimen collection tool** (`EXPERIMENTAL_NOT_FIELD_VALIDATED`).

---

## 2. Release Gate Verification Matrix

Table 1 summarizes the formal verification status for each release gate defined in the Product Requirements Document (PRD).

### Table 1: PRD Release Gate Verification Matrix

| Release Gate | PRD Specification | Measured Result | Status |
| :--- | :--- | :--- | :--- |
| **Primary PRD Accuracy Gate** | **Macro-F1 $\ge 92.00\%$** | **$50.23\% \pm 12.09\%$** (Gap: **41.77 pp**) | **FAILED (Blocked)** |
| **Secondary Balanced Accuracy** | $\ge 90.00\%$ balanced accuracy | **$56.32\% \pm 11.05\%$** (Gap: **33.68 pp**) | **FAILED (Blocked)** |
| **Field Biological Validation** | Validated on wild-caught damaged specimens | 44 pinned laboratory specimens only | **FAILED (Blocked)** |
| **Backend API Contract** | 28 OpenAPI REST endpoints reconciled | 28 endpoints verified, FastAPI production | **PASSED** |
| **Server Inference Engine** | Centralized FP32 ONNX Runtime on i7-2600 | 27.29 ms median latency, 100% verified | **PASSED** |
| **Active Model Integrity** | Checksum verified against registry | SHA-256 `c3a3656f...`, Health endpoint green | **PASSED** |
| **Host Memory Footprint** | Container stack $< 500$ MB RAM | **33.71 MiB** total RAM across all services | **PASSED** |
| **Android APK Hygiene** | Zero models or ONNX runtimes in mobile client | 0 `.onnx` files, 0 native C++ runtimes (10.9 MB) | **PASSED** |
| **Physical Hardware Testing** | Samsung Galaxy Tab A7 Lite (SM-T225) | Android 14 / API 34 verified via ADB | **PASSED** |
| **Offline Specimen Queuing** | Local persistence, zero synthetic predictions | Room DB persistence, status `PENDING_UPLOAD` | **PASSED** |
| **Lineage Governance** | Quarantine precomputed augmented dataset | 2,640 records quarantined in manifest | **PASSED** |

---

## 3. PRD Accuracy Gate Correction and Scientific Assessment

### Correction of the Primary Acceptance Target

The initial Vectora AI 3.0 evaluation report incorrectly prioritized Balanced Accuracy ($68.47\%$) as the primary gate.
In accordance with the PRD and epidemiological standards, the primary metric is **Macro-F1 across all three genera (Aedes, Anopheles, Culex)**.
Macro-F1 prevents class imbalance from masking poor sensitivity on critical disease vectors.

### The 41.77 Percentage Point Macro-F1 Gap

When evaluated strictly on raw, untouched physical specimens (zero synthetic augmentations in validation), the candidate model (`efficientnet_b0`, $224 \times 224$) performs as follows:

```
PRD Macro-F1 Target:    [=============================================] 92.00%
Clean Biological F1:    [=========================] 50.23%
                        <------------------------>
                             41.77 pp Deficit
```

### Table 2: Detailed Biological Metric Breakdown

| Metric | Target Specification | Clean Physical Result | Deficit / Status |
| :--- | :--- | :--- | :--- |
| **Macro-F1 Score** | $\ge 92.00\%$ (0.9200) | **$50.23\% \pm 12.09\%$** | **-41.77 percentage points** |
| **Balanced Accuracy** | $\ge 90.00\%$ (0.9000) | **$56.32\% \pm 11.05\%$** | **-33.68 percentage points** |
| **Overall Accuracy** | $\ge 90.00\%$ (0.9000) | **$62.50\%$** (55/88 correct) | **-27.50 percentage points** |
| **Culex Recall** | $\ge 90.00\%$ | **$95.00\% \pm 9.26\%$** | **PASSED (+5.00 pp)** |
| **Anopheles Recall** | $\ge 90.00\%$ | **$39.58\% \pm 31.75\%$** | **-50.42 percentage points** |
| **Aedes Recall** | $\ge 90.00\%$ | **$34.38\% \pm 44.28\%$** | **-55.62 percentage points** |

### Biological Cause of Deficit
1. The 44 laboratory specimens represent a single developmental cohort on uniform white cork backgrounds.
2. In raw photographic frames, slender mosquito anatomical structures (such as wing scales and palps) are too small at $224 \times 224$ resolution.
3. The classifier defaults to the majority class (Culex, 95% recall) because of its broad brown pigmentation, misclassifying 43.3% of Aedes and 44.4% of Anopheles specimens as Culex.

---

## 4. Operational Guardrails for Controlled Internal Research

Because Vectora AI 3.0-RC1 is approved exclusively for controlled internal research, the platform operates under four mandatory guardrails:

```
+-----------------------------------------------------------------------------+
|               Vectora AI 3.0-RC1 Operational Research Guardrails             |
+-----------------------------------------------------------------------------+
|                                                                             |
|  1. SERVER-ONLY INFERENCE                                                   |
|     - All AI computation occurs on central i7-2600 server                   |
|     - Android devices are strictly image capture and upload terminals       |
|                                                                             |
|  2. MANDATORY CONFIDENCE GATING (65.0% THRESHOLD)                           |
|     - Inferences with certainty < 65% marked LOW_CONFIDENCE                 |
|     - User UI displays: "Provisional Result — Expert Verification Required"  |
|                                                                             |
|  3. OFFLINE QUEUING INTEGRITY                                               |
|     - Unconnected field captures saved to local Room DB                     |
|     - Zero offline heuristics or synthetic inferences generated             |
|                                                                             |
|  4. COMPLETE DATA QUARANTINE                                                |
|     - 2,640 precomputed images quarantined in conservative manifest         |
|     - Physical and synthetic data strictly segregated                       |
|                                                                             |
+-----------------------------------------------------------------------------+
```

1. **Server-Only Inference:**
   - The Android mobile application contains zero neural network weights and zero inference runtimes.
   - All identification requests are transmitted over authenticated HTTPS/LAN to the FastAPI backend.
   - This prevents mobile battery drain and ensures model version consistency.

2. **Provisional Research Gating:**
   - Every inference response returned by the backend includes the field:
     `"disclaimer": "EXPERIMENTAL_NOT_FIELD_VALIDATED — INTERNAL_RESEARCH_ONLY"`.
   - Predictions below $65.0\%$ confidence are tagged as `LOW_CONFIDENCE_MANUAL_REVIEW_REQUIRED`.

3. **Room DB Offline Queue:**
   - If field workers lose Wi-Fi/LAN connectivity, the Android application stores images locally in Room DB.
   - Records receive status `PENDING_UPLOAD`.
   - The application does not attempt local heuristic classification.

4. **Lineage Segregation:**
   - The 2,640 precomputed augmented images are archived in `data/metadata/conservative_lineage_manifest.json`.
   - They are quarantined from future training pipelines and designated as an offline stress test.

---

## 5. Active System State and Verification Artifacts

The active deployment state on the host machine (`Intel Core i7-2600`, 16 GB RAM) is verified as follows:

### Table 3: Active Software and Hardware Artifacts

| Component | Path / Location | Version / Identifier | Operational Status |
| :--- | :--- | :--- | :--- |
| **FastAPI Backend** | `docker compose: backend` | Port `8000` | **HEALTHY** |
| **Web Frontend** | `docker compose: web` | Port `3001` (Next.js 14) | **HEALTHY** |
| **Database** | `docker compose: postgres` | PostgreSQL 16 Alpine | **HEALTHY** |
| **Task Queue** | `docker compose: redis` | Redis 7 Alpine | **HEALTHY** |
| **Background Worker** | `docker compose: video_worker` | Celery Worker | **HEALTHY** |
| **Active Adult Model** | `models/vectora_v3_fp32.onnx` | SHA-256 `c3a3656f746a1bb2...` | **VERIFIED (FP32)** |
| **Android APK** | `dist/vectora-ai-3.0-release.apk` | Version `3.0.0` (Code `3`) | **COMPILED (10.9 MB)** |
| **Clean CV Dataset** | `reports/v3_1_cv_clean_results.json` | 8 Folds (Seeds 42, 1337) | **GENERATED** |
| **Lineage Manifest** | `data/metadata/conservative_lineage_manifest.json` | 2,640 Quarantined Records | **GENERATED** |

---

## 6. Strategic Roadmap to Production Approval (Vectora AI 3.1)

To close the 41.77 percentage point Macro-F1 gap and achieve production release:

1. **Phase 1: Field Specimen Data Collection (Target: $N \ge 1,500$):**
   - Deploy the Samsung Galaxy Tab A7 Lite across municipal surveillance sites.
   - Collect high-resolution photographs of wild-caught mosquitoes in varying conditions (fresh, desiccated, damaged limbs).
   - Ensure geographic diversity across urban and peri-urban habitats.

2. **Phase 2: Two-Stage Specimen Localization (YOLOv8-Nano):**
   - Integrate a lightweight specimen detector to detect the mosquito body and crop out background cork, pins, and lighting glare.
   - Pass cropped high-resolution specimen patches to the classification backbone.

3. **Phase 3: Multi-Angle Diagnostic Photography:**
   - Update the Android CameraX capture workflow to prompt the user for three photographs per specimen:
     - View 1: Dorsal view (scutal scales, abdominal bands).
     - View 2: Lateral view (pleural scale patches, legs).
     - View 3: Macro head view (proboscis, maxillary palps).

4. **Phase 4: Entomological Verification Panel:**
   - Form an independent taxonomic panel to inspect physical voucher specimens and verify ground-truth labels.
   - Maintain a verifiable audit trail with physical specimen accession IDs.

5. **Phase 5: Production Acceptance Gate:**
   - Evaluate the two-stage pipeline on an independent, unseen test set of wild-caught specimens.
   - Production approval will be granted when the model achieves **Macro-F1 $\ge 92.00\%$** with Anopheles recall $\ge 90.00\%$.
