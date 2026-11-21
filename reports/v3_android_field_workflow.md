# Vectora AI 3.0 — Physical Android Field Workflow Audit

## 1. Executive Summary

This document records the physical device audit of Vectora AI 3.0 on a Samsung Galaxy Tab A7 Lite (`SM-T225`).
All statements follow ASD-STE100 writing principles.
Antigravity validated the Android release APK, offline queuing behavior, local Room database persistence, and remote synchronization with the Intel Core i7-2600 inference server.

The physical device workflow meets all requirements:
1. **APK Packaging:** The release APK contains **zero ONNX models** and **zero ONNX native libraries**.
2. **Offline Data Preservation:** When network connectivity is absent, photographs and bounding coordinates queue locally in Room database with status `PENDING_UPLOAD`.
3. **Zero Synthetic Fabrications:** The offline client generates no synthetic predictions.
4. **LAN Synchronization:** When connected to the server network, the client synchronizes pending records and displays uncalibrated server predictions.
5. **Mandatory Disclaimers:** All results display the `EXPERIMENTAL_NOT_FIELD_VALIDATED` status tag.

---

## 2. Test Device Specifications

Physical validation ran on the project reference tablet:

| Parameter | Specification |
| :--- | :--- |
| **Device Model** | Samsung Galaxy Tab A7 Lite (`SM-T225`) |
| **Device Serial** | `R9ZRB0DE85Y` |
| **Android Version** | Android 14 (API Level 34, One UI Core 6.1) |
| **Processor Architecture** | MediaTek Helio P22T (MT8768T), ARM Cortex-A53 (arm64-v8a) |
| **Package Name** | `com.vectora.ai` |
| **Application Version** | Version Name `2.2.0`, Version Code `3` |
| **APK Path** | `dist/vectora-ai-3.0-release.apk` (4,621,400 bytes) |
| **Signing Certificate** | Scheme v2 / v3 valid release signature |

---

## 3. Release APK Package Inspection

Antigravity decompressed and audited the contents of `dist/vectora-ai-3.0-release.apk`:

```
dist/vectora-ai-3.0-release.apk
├── assets/
│   ├── (Zero .onnx model files)
│   └── (Zero quantized model files)
├── lib/arm64-v8a/
│   ├── (Zero libonnxruntime.so)
│   └── (Zero libonnxruntime4j_jni.so)
└── classes.dex (Compiled application logic)
```

### Verification Findings

1. **Model Absence:** The `assets/` directory contains no `.onnx` or `.pt` files. The 15 MB model is not packaged into the mobile application.
2. **Runtime Absence:** The `lib/` directory contains no native ONNX Runtime binaries (`libonnxruntime.so`). The APK size is 4.4 MiB (reduced from 42 MiB).
3. **Execution Mode:** The mobile client operates strictly as an image capture and client ingestion tool. All machine learning inference executes remotely on the host server.

---

## 4. End-to-End Field Capture and Offline Queuing Audit

Antigravity conducted an end-to-end capture and offline test sequence:

```
+-------------------------------------------------------------------------+
|                  Physical Device Offline Ingestion Test                 |
+------------------------------------+------------------------------------+
                                     |
                                     v
                  +--------------------------------------+
                  | 1. Disable Wi-Fi Interface           |
                  |    adb shell cmd wifi set-wifi-enabled|
                  +------------------+-------------------+
                                     |
                                     v
                  +--------------------------------------+
                  | 2. Specimen Photographic Capture     |
                  |    High-resolution adult photograph  |
                  +------------------+-------------------+
                                     |
                                     v
                  +--------------------------------------+
                  | 3. Interactive Specimen Cropping     |
                  |    Window Size: 44%, X: 3%, Y: 8%    |
                  +------------------+-------------------+
                                     |
                                     v
                  +--------------------------------------+
                  | 4. Server Submission Attempt         |
                  |    Failed: Unreachable (Offline)     |
                  +------------------+-------------------+
                                     |
                                     v
                  +--------------------------------------+
                  | 5. Room Database Queuing             |
                  |    Status: PENDING_UPLOAD            |
                  |    Prediction: NONE (Zero synthetic) |
                  +------------------+-------------------+
                                     |
                                     v
                  +--------------------------------------+
                  | 6. Re-enable Wi-Fi Interface         |
                  |    Connect to 192.168.1.120:8000     |
                  +------------------+-------------------+
                                     |
                                     v
                  +--------------------------------------+
                  | 7. Authenticated Sync & Prediction   |
                  |    Host: Intel Core i7-2600 FP32     |
                  |    Result: Uncertain (43.1% < 65%)   |
                  |    Status: Completed on Server       |
                  +--------------------------------------+
```

### Step-by-Step Validation Evidence

#### Step 1: Specimen Capture Viewfinder
- CameraX initialized on physical rear sensor.
- Viewfinder displayed guideline overlay: *"Center mosquito specimen inside guide (Manual crop available on next screen)"*.
- Image captured at native camera resolution.

#### Step 2: Specimen Crop Interface
- The tablet opened `Specimen Preview & Crop`.
- User framed the specimen with the yellow bounding box and sliders:
  - Window Size: 44%
  - Horizontal X: 3%
  - Vertical Y: 8%
- Bounding parameters were stored alongside the photograph URI.

#### Step 3: Offline Submission Handling
- Wi-Fi was disabled (`Wifi is disabled`).
- The user tapped **Confirm & Upload**.
- The HTTP request failed immediately with:
  > *"Connection failed: Failed to connect to /192.168.1.120:8000. Photograph is safely saved locally."*
- The record was committed to the local Room SQLite database with `status = "PENDING_UPLOAD"`.
- The screen displayed:
  > *"Your photograph and crop parameters have been securely stored in the local Room database. No prediction will be fabricated without server response."*
- **Audit Check:** Antigravity confirmed that no predicted genus, probability, or dummy classification was written to the record.

#### Step 4: Reconnection and Server Ingestion
- Wi-Fi was re-enabled and connected to `ICMR-NIMR_2.4G` (`192.168.1.121`).
- The user signed in using encrypted credentials (`field_worker@vectora.org`).
- The pending record was submitted via multipart HTTP POST to `/api/v1/adult/submit`.
- The backend server executed ONNX Runtime FP32 inference on the host CPU in 231 ms total roundtrip.
- Server response:
  - Genus: Culex (raw probability 43.1%)
  - Certainty: Uncertain ($0.431 < 0.65$ certainty threshold)
  - Inference Host: `Intel Core i7-2600 CPU (Exp B FP32)`
  - Status Tag: `EXPERIMENTAL_NOT_FIELD_VALIDATED`
- The tablet database updated `synced = true` and `status = "Completed on Server"`.
- The dashboard updated pending count to `0`.

---

## 5. Visual Evidence Index

Antigravity captured and archived high-resolution screenshots in `docs/screenshots/`:

| Screenshot File | Screen Name | Verified Workflow State |
| :--- | :--- | :--- |
| `tablet_dashboard_online.png` | Dashboard | Server Online banner (`http://192.168.1.120:8000/`) |
| `tablet_offline_capture_screen.png` | Camera Viewfinder | Live viewfinder with specimen framing overlay |
| `tablet_captured_photo.png` | Crop Interface | Framing sliders (Size 44%, X 3%, Y 8%) |
| `tablet_offline_queued.png` | Offline Dialog | `PENDING_UPLOAD` dialog with zero synthetic predictions |
| `tablet_dashboard_offline_pending.png` | Dashboard | Server Offline banner and `1 Offline Submission(s) Pending` |
| `tablet_history_pending.png` | History List | Offline item queued with timestamp |
| `tablet_signin_screen.png` | Authentication | LAN server sign-in with Keystore AES-256 notice |
| `tablet_result_synced.png` | Specimen Result | Server prediction (43.1%, Uncertain, Host i7-2600) |
| `tablet_dashboard_clean.png` | Dashboard | Synced state showing 0 pending submissions |

---

## 6. Audit Conclusion

The Android field workflow audit is verified and approved.
The application operates without local model weight dependencies.
Offline specimens queue reliably in Room database without synthetic predictions.
LAN synchronization with the Intel Core i7-2600 host is verified.
All mandatory disclaimers and uncertainty safeguards are active.
