# Vectora AI - Web Scan Workflow Verification Report

**Document ID:** `VECTORA-REP-WEB-SCAN-01`  
**Date:** November 23, 2026  
**Status:** Verified in Production Docker Container  
**Web Endpoint:** `http://localhost:3001`  
**Backend Endpoint:** `http://localhost:8000`  
**Runtime:** Next.js 15.5.29 (Turbopack) in Docker (`mosqscan-web`)  

---

## 1. Executive Summary

This report documents the restructuring and end-to-end verification of the Vectora AI Web Application (`web/`). All legacy enterprise dashboard widgets, telemetry graphs, and generative AI chat panels have been removed. The web interface now mirrors the minimalist native mobile experience:
1. **Root Page (`/`)**: Minimal landing displaying branding, browser device access guidance, and **exactly two options**: `Adult Mosquito` and `Mosquito Larvae`.
2. **Simplified Navbar**: Nav links strictly restricted to `Adult Mosquito` and `Mosquito Larvae`.
3. **Adult Scan Workflow (`/adult`)**: Specimen drag-and-drop, dimension and size validation, manual crop box configuration, real-time backend ONNX inference, and clean raw-score visualization (Gemma LLM explanation card removed).
4. **Larvae Scan Workflow (`/larvae`)**: 3–5 second behavioral video validation and submission isolation.
5. **Full Test Suite & Container Health**: 10/10 unit tests passing, static page generation passing (14/14), Docker container running healthy.

---

## 2. Web Interface Architecture & Routes

### 2.1 Route Map

```
/ (Home) ──► Minimal two-option portal + Device access guidance
  ├── /adult ──► Adult specimen upload, crop box, genus inference result
  ├── /larvae ──► 3–5s larvae video upload & research collection
  ├── /login ──► User authentication
  └── /register ──► User registration
```

*Note: Legacy navigation links to `/dashboard`, `/analytics`, `/history`, and `/assistant` were removed from the global navigation header.*

### 2.2 Root Page Implementation (`web/src/app/page.tsx`)

The landing page was rewritten to eliminate marketing clutter and present an immediate path to scanning:
- **Branding Header**: Emerald mosquito vector icon, "Vectora AI", subtitle "Visual Genus-Level Identification & Field Research Tool".
- **Device Access Guidance**: Informs users regarding browser permissions (camera access via `getUserMedia`, client-side image processing, and GPS geo-tagging).
- **Two Option Cards**:
  1. **Adult Mosquito Card** (link to `/adult`):
     - Icon: `Bug` (emerald `#10B981`)
     - Title: "Adult Mosquito"
     - Subtitle: "Photograph or upload an adult specimen image for instant visual genus identification (Aedes, Anopheles, Culex)."
     - Call to action: "Scan Adult Mosquito →"
  2. **Mosquito Larvae Card** (link to `/larvae`):
     - Icon: `Waves` (amber `#F59E0B`)
     - Badge: "Research only • Model not field-validated"
     - Title: "Mosquito Larvae"
     - Subtitle: "Upload a 3–5 second video clip of larvae movement. Submissions are collected for research; larvae identification model is not field-validated."
     - Call to action: "Submit Larvae Clip →"

### 2.3 Navbar Simplification (`web/src/components/Navbar.tsx`)

The navigation bar links were reduced from seven items down to two:
```tsx
const navLinks = [
  { href: '/adult', label: 'Adult Mosquito', icon: Bug },
  { href: '/larvae', label: 'Mosquito Larvae', icon: Waves },
];
```

---

## 3. Adult Specimen Scan Workflow (`/adult`)

### 3.1 Input Validation
The web interface enforces client-side safety checks prior to network dispatch:
- **MIME Types**: Restricts uploads to `image/jpeg`, `image/png`, and `image/jpg`.
- **File Size**: Ceiling at 20 MB (`20 * 1024 * 1024` bytes).
- **Minimum Dimensions**: Dynamically verifies that image width and height are at least 100×100 px via HTML Image onload:
  ```typescript
  const img = new Image();
  img.onload = () => {
    if (img.width < 100 || img.height < 100) {
      setError(`Image dimensions ${img.width}×${img.height} are below the minimum 100×100.`);
    }
  };
  img.src = url;
  ```

### 3.2 Manual Specimen Crop
- Users can adjust the specimen crop bounding box (percentage position and size).
- Crop parameters are normalized to `[crop_x, crop_y, crop_w, crop_h]` and sent in the multipart form request to `/api/v1/adult/submit`.

### 3.3 End-to-End Inference Verification
Submitting test specimen `Mosquito Images Augmented/Aedes Aegypti/Aedes_aegypti_1.jpg` via the API endpoint verified live inference output:

```json
{
  "id": "aadea2b1-66fa-4b83-88fc-0f136d86a8b9",
  "status": "completed",
  "type": "adult",
  "result": {
    "predicted_genus": "aedes",
    "raw_class_scores": {
      "aedes": 0.5024269223213196,
      "anopheles": 0.2811398506164551,
      "culex": 0.21643322706222534
    },
    "model_version": "3.0.0",
    "model_artifact": "vectora_v3_fp32.onnx",
    "model_checksum": "c3a3656f746a1bb2e7ac428e44670d89cf51f0d0f923ad3aa15420e8a4592cfa",
    "inference_latency_ms": 73,
    "model_status": "EXPERIMENTAL_NOT_FIELD_VALIDATED",
    "scientific_disclaimer": "Visual genus-level identification only. Research pilot model. Not field-validated."
  }
}
```

### 3.4 Minimal Result Presentation
- Displays specimen photograph preview.
- Displays predicted genus badge (`Aedes`).
- Displays 3 raw class probability bars (`Aedes`: 50.2%, `Anopheles`: 28.1%, `Culex`: 21.6%).
- Displays model metadata: latency (73 ms), model artifact checksum, version 3.0.0.
- Gemma AI LLM chatbot card has been completely excised.

---

## 4. Mosquito Larvae Workflow (`/larvae`)

### 4.1 Duration Boundary Validation
Both web client (`web/src/app/larvae/page.tsx`) and backend (`app/services/larvae_service.py`) enforce strict 3–5s duration validation:
- `t < 3.0s`: Rejected with `VIDEO_TOO_SHORT`.
- `t > 5.0s`: Rejected with `VIDEO_TOO_LONG`.
- `3.0s <= t <= 5.0s`: Accepted for research collection.

### 4.2 Research Isolation
Submissions to `/api/v1/larvae/submit` do not trigger the adult ONNX model. The response returns `status: "model_not_validated"` and `predicted_genus: null`, maintaining strict model integrity.

---

## 5. Web Unit Test Suite Verification

The web test suite was executed via `npm test` using Node.js test runner:

```
> web@0.1.0 test
> node --experimental-strip-types --test src/__tests__/*.test.ts

✔ Authentication token store lifecycle: login sets token, logout clears (1.368ms)
✔ History filter: filters correctly by type (adult vs larvae vs all) (0.430ms)
✔ History filter: search query filters by genus or ID (0.323ms)
✔ Larvae model contract: status must be model_not_validated with null prediction (0.364ms)
✔ Video duration 2.99s must be rejected with too short error (1.965ms)
✔ Video duration 3.00s must be accepted (0.220ms)
✔ Video duration 4.00s must be accepted (0.194ms)
✔ Video duration 5.00s must be accepted (0.202ms)
✔ Video duration 5.01s must be rejected with too long error (0.238ms)
✔ Zero or NaN duration must be rejected as corrupted (0.192ms)

ℹ tests 10 | pass 10 | fail 0 | cancelled 0 | skipped 0
ℹ duration_ms 291.7ms
```

---

## 6. Production Container Verification

### 6.1 Container Build & Health
- Docker container `vectora-web` was rebuilt with Next.js Turbopack.
- Status: `Up (healthy)`, port mapping `0.0.0.0:3001->3000/tcp`.

### 6.2 HTTP Endpoint Audit
- `curl -I http://localhost:3001` -> `HTTP/1.1 200 OK`
- `curl -I http://localhost:3001/adult` -> `HTTP/1.1 200 OK`
- `curl -I http://localhost:3001/larvae` -> `HTTP/1.1 200 OK`
- HTML content verification confirms zero references to `dashboard`, `analytics`, or chatbot widgets on the landing page.

---

## 7. Conclusion

The Vectora AI Web Application is fully aligned with the minimal field-focused design specification. The root page offers clean device guidance and exactly two scan options, all tests pass, and the production Docker deployment is healthy.
