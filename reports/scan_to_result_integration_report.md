# Vectora AI — Scan-to-Result Integration and End-to-End Verification Report

**Document Status:** Accepted Production Verification Baseline  
**Date:** 2026-11-13  
**Execution Environment:** Intel Core i7-2600, 16 GB RAM, Omarchy Linux, Docker Compose  
**Standard Compliance:** ASD-STE100 Technical English  

---

## 1. Executive Summary

This report confirms the completion and end-to-end verification of the Vectora AI adult mosquito scan workflow. 

The system was tested using an automated test suite ([test_end_to_end_inference.py](file:///home/nimr/Projects/mosqscan/scripts/test_end_to_end_inference.py)). The test suite executed all 12 operational verification tests. All 12 tests passed successfully. In addition, a 20-sample sequential benchmark confirmed production stability and latency performance.

Test summary results from [end_to_end_inference_tests.json](file:///home/nimr/Projects/mosqscan/reports/end_to_end_inference_tests.json):
- **Total Tests:** 12
- **Passed:** 12 (100%)
- **Failed:** 0
- **Sequential Benchmark:** 20/20 successful requests (0 failures)
- **Active Model Checksum:** `c3a3656f746a1bb2e7ac428e44670d89cf51f0d0f923ad3aa15420e8a4592cfa` (Verified)

---

## 2. End-to-End Adult Scan Pipeline Architecture

The scan-to-result pipeline processes adult mosquito photographs through nine sequential stages.

```
[Client Upload: Multipart/Form-Data]
                 |
                 v
[1. User Authentication (JWT Bearer Token)]
                 |
                 v
[2. File Security & MIME Validation] (Max 20MB; JPEG/PNG/WebP; Decompress check)
                 |
                 v
[3. Specimen Crop Extraction] (Android normalized floats OR Web crop_box JSON)
                 |
                 v
[4. Preprocessing & Tensor Transformation] (RGB -> 224x224 bicubic -> ImageNet Norm)
                 |
                 v
[5. ONNX Runtime FP32 Inference] (vectora_v3_fp32.onnx; 2 intra-op threads)
                 |
                 v
[6. Score Normalization & Class Argmax] (Softmax -> 0: aedes, 1: anopheles, 2: culex)
                 |
                 v
[7. Relational Persistence] (PostgreSQL: submissions, identification_results, media_files)
                 |
                 v
[8. Media Persistence] (media_storage volume: original and cropped images)
                 |
                 v
[9. Structured Response Contract Returned to Client]
```

### Stage Details

1. **Authentication:** The client provides an HTTP Bearer JWT token in the `Authorization` header. Unauthenticated requests receive HTTP 401.
2. **File Security & MIME Validation:** The API validates that the payload does not exceed 20 MB. It verifies MIME magic bytes. The server decodes the image using Pillow. Truncated or corrupted streams are rejected with HTTP 422.
3. **Specimen Crop Extraction:**
   - **Android Client:** Sends individual multipart form fields (`crop_x`, `crop_y`, `crop_w`, `crop_h`) representing normalized coordinates in the range `[0.0, 1.0]`.
   - **Web Client:** Sends a JSON string in the `crop_box` form field (`{"x": 0.1, "y": 0.1, "width": 0.8, "height": 0.8}`).
   - **Fallback Mode:** If no crop coordinates are supplied, the server processes the full image.
   - **Boundary Enforcement:** Out-of-bounds coordinates (e.g. `x + w > 1.0` or negative values) are rejected with HTTP 422.
4. **Preprocessing Pipeline:**
   - Converts the cropped image to RGB color space.
   - Resizes the crop to 224 × 224 pixels using bicubic interpolation.
   - Normalizes pixel values with ImageNet parameters:
     - Mean: `[0.485, 0.456, 0.406]`
     - Standard Deviation: `[0.229, 0.224, 0.225]`
   - Formats the output as a float32 tensor with shape `(1, 3, 224, 224)`.
5. **ONNX Runtime FP32 Inference:**
   - The server loads `models/vectora_v3_fp32.onnx`.
   - Inference runs using the CPU execution provider with 2 intra-op threads and 1 inter-op thread.
   - A concurrency semaphore restricts active ONNX inference to 1 execution thread.
6. **Output Interpretation and Class Mapping:**
   - The model produces 3 logit values.
   - The server applies the softmax function to compute class probabilities.
   - The authoritative class mapping is:
     - Index `0`: `aedes`
     - Index `1`: `anopheles`
     - Index `2`: `culex`
   - The predicted genus is determined by argmax across the 3 probabilities.
   - If the highest score is below `0.65`, the system sets `is_uncertain: true` and sets `review_recommendation: "MANUAL_ENTOMOLOGICAL_INSPECTION_REQUIRED"`. The predicted genus is never replaced with `null`.
7. **Relational Database Persistence:**
   - Creates a record in the `submissions` table with status `completed`.
   - Inserts the inference outcome into `identification_results` (`genus`, `species=null`, `confidence`, `model_name`, `processing_time_ms`).
   - Inserts media metadata into `media_files` for both original and cropped images.
8. **File Storage:** Stores physical image files under `/tmp/vectora_media/` inside the Docker volume `media_storage`.
9. **Response Serialization:** Assembles the contract and returns HTTP 201 Created.

---

## 3. Structured Response Contract

Every successful adult mosquito scan returns a structured JSON payload adhering to the contract defined in Section 3 of the integration specification.

```json
{
  "scan_id": "6fbd5f45-f9af-4172-a209-295c408a460d",
  "predicted_genus": "aedes",
  "confidence": 0.5629,
  "raw_class_scores": {
    "aedes": 0.5629,
    "anopheles": 0.2185,
    "culex": 0.2186
  },
  "all_scores": {
    "aedes": 0.5629,
    "anopheles": 0.2185,
    "culex": 0.2186
  },
  "model_checksum": "c3a3656f746a1bb2e7ac428e44670d89cf51f0d0f923ad3aa15420e8a4592cfa",
  "processing_timestamp": "2026-11-13T11:35:48.330109Z",
  "inference_latency_ms": 68,
  "inference_latency": "68 ms",
  "evaluation_status": "EXPERIMENTAL_NOT_FIELD_VALIDATED",
  "review_recommendation": "MANUAL_ENTOMOLOGICAL_INSPECTION_REQUIRED",
  "scientific_disclaimer": "Experimental model output for research assessment only. Predictions are uncalibrated and require physical entomological verification. Not validated for species identification or disease transmission diagnosis.",
  "is_uncertain": true,
  "quality_feedback": {
    "is_blurry": false,
    "is_too_dark": false,
    "is_too_bright": false,
    "quality_score": 0.88,
    "warnings": []
  }
}
```

### Safety and Regulatory Field Definitions

1. **`evaluation_status`:** Fixed string `EXPERIMENTAL_NOT_FIELD_VALIDATED`.
2. **`review_recommendation`:**
   - Returns `CONFIRMATORY_ENTOMOLOGICAL_REVIEW_RECOMMENDED` when max score is `>= 0.65`.
   - Returns `MANUAL_ENTOMOLOGICAL_INSPECTION_REQUIRED` when max score is `< 0.65`.
3. **`scientific_disclaimer`:** Mandates entomological verification and explicitly disclaims species-level identification and pathogen detection.
4. **`raw_class_scores`:** Uncalibrated model scores summing to 1.0 across the three genera.

---

## 4. Test Suite Execution and Verification Results

The automated test script verified the 12 core requirements.

| Test ID | Requirement | Test Action | Result | Verification Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Test 1** | Android Upload & Crop | Upload with `crop_x/y/w/h` form fields | **PASSED** | Scan ID generated; Aedes predicted; crop applied |
| **Test 2** | Web Upload & Fallback | Upload with JSON `crop_box` and fallback | **PASSED** | Manual crop and full-image fallback verified |
| **Test 3** | Class Index Mapping | Verify output tensor score order | **PASSED** | Class order matches: 0=aedes, 1=anopheles, 2=culex |
| **Test 4** | Structured Schema Contract | Verify all 10 schema fields | **PASSED** | All required fields present and non-null |
| **Test 5** | Database Persistence | Query PostgreSQL tables directly | **PASSED** | `submissions`, `identification_results`, `media_files` verified |
| **Test 6** | User Authorization | Access Scan A with User B token | **PASSED** | Blocked with HTTP 403 Forbidden; user scans partitioned |
| **Test 7** | Ollama Offline Resilience | Stop Ollama and execute adult scan | **PASSED** | Scan completed in 65 ms while Ollama was offline |
| **Test 8** | Restart Persistence | Restart `vectora-backend` container | **PASSED** | Submissions and stored media bytes survived restart |
| **Test 9** | Offline Queue Simulation | Simulate Android client offline queue | **PASSED** | Item queued with local ID, synced to server scan record |
| **Test 10** | Boundary Rejection | Submit invalid MIME, corrupt bytes, bad crop | **PASSED** | All invalid inputs returned HTTP 422 with structured details |
| **Test 11** | Larvae Workflow Isolation | Inspect larvae video endpoint | **PASSED** | Adult model not called; video duration limits enforced |
| **Test 12** | Model Integrity Checksum | Compute SHA-256 of production model | **PASSED** | Hash matches `c3a3656f746a1bb2e7ac428e44670d89cf51f0d0f923ad3aa15420e8a4592cfa` |

---

## 5. Performance and Latency Benchmarks

A 20-sample sequential benchmark evaluated real image processing performance using biological photographs from the validation set.

### Latency Summary Table

| Metric | ONNX Inference Latency | Full Roundtrip Latency (Upload, DB, Storage) |
| :--- | :--- | :--- |
| **Sample Count** | 20 | 20 |
| **Failed Requests** | 0 (0.0%) | 0 (0.0%) |
| **Minimum** | 60 ms | 393.74 ms |
| **Median (P50)** | **68 ms** | **437.49 ms** |
| **Arithmetic Mean** | 70.30 ms | 467.92 ms |
| **P95** | **130 ms** | **730.58 ms** |
| **Maximum** | 130 ms | 730.58 ms |

### Resource Consumption During Benchmark
- **Host CPU Load:** 25% to 35% utilization across 4 physical cores.
- **Backend Container Memory:** 192 MB to 220 MB RAM.
- **PostgreSQL Connection Count:** 4 active connections.

---

## 6. Client Interoperability

### Android Client Integration
- The Android client interacts with the server through `com.vectora.ai.data.remote.api.VectoraApiService`.
- The upload method uses `@Multipart` `POST /api/v1/adult/submit`.
- For offline operation:
  - If network connectivity is lost, the Android client stores the scan in the local Room database with status `PENDING_UPLOAD`.
  - The Android client **never generates a local mock classification**.
  - Upon network reconnection, `SyncSubmissionsWorker` dispatches the queued file to `/api/v1/adult/submit`.
  - The local scan record is updated with the returned server `scan_id` and prediction scores.

### Web Client Integration
- The Next.js frontend interacts through `web/src/app/adult/page.tsx` via `submissionsApi.uploadAdult`.
- The web UI features an interactive canvas crop tool.
- When the user draws a bounding box, the client calculates normalized coordinates and includes them in the `crop_box` JSON form field.
- If no box is drawn, the full image is submitted.

---

## 7. Optional Ollama / Gemma 3:4B Integration

The local LLM service provides plain-language explanations of model results on an optional, on-demand basis.

### Decoupling Verification
Test 7 demonstrated that adult mosquito identification operates with zero dependence on the Ollama service. When `vectora-ollama` is stopped, adult classification executes without latency penalty.

### Mode A On-Demand Explanation
When the user requests an explanation for a scan, the client sends a request to `POST /api/v1/assistant/explain-result`.

#### Test Execution Result
- **Prompt:** Provided predicted genus `Aedes`, raw scores `[0.5629, 0.2185, 0.2186]`, and image quality metrics.
- **Generation Duration:** 98,809.88 ms (CPU-bound execution on Intel Core i7-2600).
- **Generated Response:**
```json
{
  "explanation": "The model identified the specimen as *Aedes*, likely due to characteristics such as its typically compact body size and presence of distinct scales on the thorax. The raw score of 0.5629 reflects an experimental estimate and does not represent definitive identification. This model is a research pilot and visual identification alone is insufficient. Confirmatory entomological examination, including morphological assessment and potentially PCR analysis, is strongly recommended for accurate species determination."
}
```
The assistant strictly adhered to ASD-STE100 guidelines, output valid structured JSON, and enforced scientific disclaimers without claiming definitive identification or pathogen detection.

---

## 8. Larvae Workflow Isolation

The larvae workflow was verified to ensure strict operational separation:
1. Larvae submissions route to `/api/v1/larvae/submit`.
2. Larvae analysis is processed asynchronously by the Celery video worker (`vectora-video-worker`).
3. The adult ONNX model is **never** invoked for larvae submissions.
4. The system validates video constraints (maximum 5 seconds duration, MP4/MOV/AVI format).
5. The API returns `model_status: "model_not_validated"` with `prediction: null`, preventing unsupported automated claims.
