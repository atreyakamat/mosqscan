# Vectora AI - Android Scan Workflow Verification Report

**Document ID:** `VECTORA-REP-AND-SCAN-01`  
**Date:** November 23, 2026  
**Status:** Verified on Physical Hardware  
**Target Device:** Samsung Galaxy Tab A7 Lite (SM-T225, Android 14 / One UI 6.0, Serial: `R9ZRB0DE85Y`)  
**Package:** `com.vectora.ai` (Target ABI: `arm64-v8a`, compileSdk: 35, targetSdk: 34)  
**Backend Endpoint:** `http://192.168.1.120:8000`  
**Model Checksum:** `c3a3656f746a1bb2e7ac428e44670d89cf51f0d0f923ad3aa15420e8a4592cfa`  

---

## 1. Executive Summary

This report documents comprehensive end-to-end validation of the simplified Vectora AI Android application on physical hardware (Samsung Galaxy Tab A7 Lite running Android 14). All testing was executed against the production ONNX CPU inference model (`models/vectora_v3_fp32.onnx`) hosted on the local network (`http://192.168.1.120:8000`).

### Deficiencies Identified in Prior Attempts & Resolved in Current Implementation
1. **ABI Incompatibility Warning on Android 14**: Sideloading 32-bit `armeabi-v7a` APK triggered an OS compatibility warning dialog ("This app isn't compatible with the latest version of Android"). Building and deploying the native 64-bit `app-arm64-v8a-release.apk` eliminated this warning.
2. **Dark Mode Typography Failure**: Text colors were hardcoded to `VectoraSlate900` (`#0F172A`), rendering branding, titles, and cards completely illegible on dark themes. Fixed by enforcing light theme default per Section 11 and binding colors to `MaterialTheme.colorScheme.onBackground` and `onSurface`.
3. **Missing Runtime Camera Permission Check in Workflows**: `AdultCaptureScreen` and `LarvaeCaptureScreen` lacked runtime `CAMERA` permission request logic; if camera permission was denied during initial setup, entering the workflow crashed or hung on a blank screen without explanation. Implemented in-workflow permission check, explanation card, Settings launcher for permanent denial, and Gallery fallback.
4. **Fabrication of Missing Scores in ResultScreen**: The previous implementation fabricated placeholder scores (`sub.scoreAedes ?: 0.85f`), violating Section 7 ("Do not invent missing results"). Updated to display only actual uncalibrated raw scores returned by the ONNX classifier.
5. **Crop Box Aspect Ratio Distortion**: The crop bounding box previously distorted into a non-square rectangle based on screen aspect ratio. Fixed to enforce a 1:1 square crop math (`sideDim = minOf(containerW, containerH) * cropSize`) matching model input requirements.
6. **Stale Model Version String**: `modelVersion` was hardcoded to `"vectora-2.2"` in several local entities instead of active model version `"3.0.0"`.

---

## 2. Adult Mosquito Scan Workflow Verification

### 2.1 Workflow Pipeline Architecture

```
[Main Screen]
     │ (Tap "Adult Mosquito")
     ▼
[Runtime CAMERA Permission Check]
     ├── [Permission Denied] ──► [Explanation Card + Gallery Fallback]
     └── [Permission Granted] ─► [CameraX Live Viewfinder]
                                        │ (Capture Specimen Photograph)
                                        ▼
                                [Square Specimen Crop Screen]
                                        │ (Confirm & Upload)
                                        ▼
                                [Upload & Inference Screen]
                                        │
                                        ├── [Network Drop / 401] ──► [Local Room DB: PENDING_UPLOAD]
                                        │                                  │ (Retry on Reconnect/Auth)
                                        │                                  ▼
                                        └── [POST /api/v1/adult/submit] ──► [ONNX CPU Classifier]
                                                                               │
                                                                               ▼
                                                                        [Result Screen]
                                                                        - Specimen Photo
                                                                        - Predicted Genus
                                                                        - 3 Raw Model Scores
                                                                        - Scan Time & Version 3.0.0
                                                                        - EXPERIMENTAL Notice
                                                                               │ (Tap "Done")
                                                                               ▼
                                                                        [Main Screen]
```

### 2.2 Step-by-Step Hardware Verification Record

#### Step 1: Main Screen Entry
- **Screen**: `Screen.Main`
- **UI Elements Verified**: Top branding "Vectora AI", heading "Choose what to scan", and exactly two cards (`Adult Mosquito` and `Mosquito Larvae`).
- **Action**: Tap `Adult Mosquito` card.
- **Evidence**: `reports/screenshots/step3_main_screen.png`

#### Step 2: Runtime Permission Check & Denial Fallback
- **Behavior**: When camera permission was requested, selecting "Don't allow" immediately presented an informative guidance card explaining that camera access is required to capture mosquito specimens.
- **Fallbacks Offered**: "Grant Camera Permission" button (or "Open Android Settings" if permanently denied) and "Select from Gallery" button.
- **Evidence**: `reports/screenshots/step5_adult_camera_permission_request.png`, `reports/screenshots/step6_permission_denied_screen.png`

#### Step 3: CameraX Viewfinder & Live Capture
- **Behavior**: Upon granting permission, CameraX live preview initialized seamlessly via `LifecycleEventObserver(ON_RESUME)`. Live camera feed displayed bounding guide and capture shutter.
- **Action**: Tap shutter button at screen center. High-resolution photograph captured and saved to app cache.
- **Evidence**: `reports/screenshots/step8_camera_preview_active.png`

#### Step 4: Square Specimen Cropping
- **Screen**: `Screen.AdultCrop`
- **Behavior**: Captured photograph rendered with square crop overlay (1:1 aspect ratio). Sliders and draggable bounding box allowed framing the mosquito specimen.
- **Action**: Tap "Confirm & Upload".
- **Evidence**: `reports/screenshots/step9_crop_screen_loaded.png`

#### Step 5: Upload, Authentication & Offline Resilience
- **Scenario A (Unauthenticated)**: Upload received HTTP 401 Unauthorized. The app saved the specimen photograph and normalized crop coordinates to Room database with status `PENDING_UPLOAD`. A clean prompt "Sign In to Authorize Upload" was displayed.
- **Action**: Tapped "Sign In", entered credentials (`field_agent@vectora.org`), and token was stored in Android Keystore.
- **Scenario B (Offline Network Drop)**: Tablet Wi-Fi was disabled (`svc wifi disable`). Submissions were queued as `PENDING_UPLOAD`. Upon re-enabling Wi-Fi (`svc wifi enable`), tapping "Retry Upload" dispatched the queued submission to `POST /api/v1/adult/submit`.
- **Evidence**: `reports/screenshots/auth_screen.png`, `reports/screenshots/auth_filled.png`, `reports/screenshots/step12_offline_pending.png`, `reports/screenshots/step12_retry_success.png`

#### Step 6: Minimal Result Presentation
- **Screen**: `Screen.Result`
- **Data Displayed**:
  - Specimen photograph: Visual thumbnail of captured/cropped specimen.
  - Predicted Genus: Displayed authoritative ONNX output (`Uncertain Genus` when confidence < 0.65 threshold).
  - Three Raw Model Scores: Real uncalibrated softmax activations (`Aedes: 0.3236`, `Anopheles: 0.3992`, `Culex: 0.2772`).
  - Scan Time: Timestamp of specimen processing (`2026-11-23 18:19:47`).
  - Model Version: Active version `3.0.0`.
  - Regulatory Status: `EXPERIMENTAL_NOT_FIELD_VALIDATED`.
  - Review Notice: Explicit notice that output is an uncalibrated heuristic and pathogen detection is not supported.
  - LLM Chatbot: Completely removed.
- **Action**: Tap "Done" (or top-bar Back arrow). Navigates directly back to `Screen.Main`.
- **Evidence**: `reports/screenshots/step10_result_screen.png`, `reports/screenshots/step10_result_screen_bottom.png`, `reports/screenshots/step10_returned_to_main.png`

---

## 3. Mosquito Larvae Scan Workflow Verification

### 3.1 Workflow Pipeline Architecture

```
[Main Screen]
     │ (Tap "Mosquito Larvae" card)
     ▼
[Larvae Viewfinder Screen]
     │ (Display 3.0s–5.0s recording boundary & water meniscus guide)
     ▼
[Video Recording Session]
     ├── [t < 3.0s] ──► Stop button disabled
     ├── [t = 5.0s] ──► Automatic hard stop triggered
     ▼
[Recorded Clip Review]
     ├── "Retake" ──► Discards buffer and resets timer
     └── "Submit Clip" ──► Saves to Room DB with status PENDING_UPLOAD
                                 │
                                 ├── Adult ONNX Model Invocation: NONE
                                 ├── Genus Prediction: NULL
                                 └── Evaluation Status: EXPERIMENTAL_NOT_FIELD_VALIDATED
                                 ▼
                          [Larvae Result Screen]
                                 │ (Tap "Done")
                                 ▼
                          [Main Screen]
```

### 3.2 Step-by-Step Hardware Verification Record

#### Step 1: Main Screen Entry
- **Card**: `Mosquito Larvae`
- **Indicator**: Prominent amber badge `"Research only • Model not field-validated"`.
- **Action**: Tap card to launch larvae recording workflow.
- **Evidence**: `reports/screenshots/step3_main_screen.png`

#### Step 2: Duration Boundary Enforcement
- **Viewfinder Guide**: Water meniscus alignment guide and duration constraint notice (`3.0s – 5.0s strictly`).
- **Boundary Test**: Tap record shutter button. Timer advances incrementally. At exactly 5.0 seconds, recording stops automatically via `VideoRecordingRules.mustStopAutomatically(elapsedSeconds)`. The elapsed banner displays `"Recorded: 5.0s (Target: 3.0s – 5.0s)"`.
- **Evidence**: `reports/screenshots/step11_larvae_capture.png`, `reports/screenshots/step11_larvae_recorded.png`

#### Step 3: Model Isolation & Research Confirmation
- **Action**: Tap "Submit Clip".
- **Result**: Record saved in Room DB with `predictedGenus = null` and `type = "larvae"`. Result screen displayed research collection status without adult ONNX invocation.
- **Action**: Tap "Done". Returns cleanly to `Screen.Main`.
- **Evidence**: `reports/screenshots/step11_larvae_result.png`, `reports/screenshots/step11_returned_to_main.png`

---

## 4. Hardware Screenshot Evidence Index

| Step | Artifact File | Resolution | Verification Target |
|:---|:---|:---:|:---|
| 1 | `reports/screenshots/step1_splash_screen.png` | 800×1340 | Startup splash with high contrast logo & typography |
| 2 | `reports/screenshots/step2_permission_setup.png` | 800×1340 | 3-card non-blocking permission setup |
| 3 | `reports/screenshots/step3_main_screen.png` | 800×1340 | Heading "Choose what to scan" & exactly two cards |
| 4 | `reports/screenshots/step4_relaunch_main_screen.png` | 800×1340 | App relaunch bypassing permission setup |
| 5 | `reports/screenshots/step5_adult_camera_permission_request.png` | 800×1340 | Android 14 runtime camera permission request |
| 6 | `reports/screenshots/step6_permission_denied_screen.png` | 800×1340 | Explanation card with Gallery fallback upon denial |
| 7 | `reports/screenshots/step8_camera_preview_active.png` | 800×1340 | CameraX live viewfinder on Galaxy Tab A7 Lite |
| 8 | `reports/screenshots/step9_crop_screen_loaded.png` | 800×1340 | Square 1:1 specimen crop interface |
| 9 | `reports/screenshots/auth_screen.png` | 800×1340 | Minimal sign-in prompt on upload 401 |
| 10 | `reports/screenshots/step10_result_screen.png` | 800×1340 | ONNX adult inference result with 3 raw scores |
| 11 | `reports/screenshots/step10_result_screen_bottom.png` | 800×1340 | Result screen footer, metadata & Done action |
| 12 | `reports/screenshots/step10_returned_to_main.png` | 800×1340 | Main screen return after adult workflow |
| 13 | `reports/screenshots/step11_larvae_capture.png` | 800×1340 | Larvae video capture viewfinder & meniscus guide |
| 14 | `reports/screenshots/step11_larvae_recorded.png` | 800×1340 | 5.0s automatic recording stop |
| 15 | `reports/screenshots/step11_larvae_result.png` | 800×1340 | Larvae research result (zero model prediction) |
| 16 | `reports/screenshots/step11_returned_to_main.png` | 800×1340 | Main screen return after larvae workflow |
| 17 | `reports/screenshots/step12_offline_pending.png` | 800×1340 | Offline Room queueing (`PENDING_UPLOAD`) |
| 18 | `reports/screenshots/step12_retry_success.png` | 800×1340 | Reconnection upload retry & server synchronization |
| 19 | `reports/screenshots/step12_returned_to_main.png` | 800×1340 | Final main screen state verification |

---

## 5. Conclusion

Both scan workflows operate with high reliability on physical Android 14 hardware. All critical edge cases—including offline resilience, permission denial recovery, uncalibrated score integrity, and larvae model isolation—have been verified with direct hardware evidence.
