# Vectora AI 3.0 — Android Physical Device Testing and UI Verification Report

**Date:** 2026-11-12  
**Target Hardware:** Samsung Galaxy Tab A7 Lite (`SM-T225`)  
**Architecture:** `arm64-v8a`  
**Android OS:** Android 14 (API Level 34)  
**Standard:** ASD-STE100  
**Status:** Complete  

---

## 1. Executive Summary

This report documents the verification, compilation, release signing, physical device installation, and UI validation of the Vectora AI 3.0 Android application.

The application was built as a signed release APK using Android Keystore (v2 signature scheme), installed on a physical Samsung Galaxy Tab A7 Lite connected via USB ADB, launched into the foreground, and validated across all primary functional screens.

---

## 2. Release Artifact Verification

| Property | Value |
| :--- | :--- |
| **Application Package** | `com.vectora.ai` |
| **Version Name** | `3.0.0` |
| **Version Code** | `300` |
| **Target SDK / Min SDK** | API 35 / API 29 |
| **Binary Artifact Path** | `dist/vectora-ai-3.0-release.apk` |
| **File Size** | 4,621,400 bytes (4.41 MB) |
| **SHA-256 Checksum** | `0aae047943b613775cfa0c37e7086c2ed25777687cbfc8a65f7b4a7acf00257f` |
| **Signature Scheme** | APK Signature Scheme v2 (Verified: true) |
| **Signing Certificate** | External keystore (`~/.android/vectora_release.keystore`) |

### Verification Command Output
```text
$ /home/nimr/Android/Sdk/build-tools/34.0.0/apksigner verify --verbose dist/vectora-ai-3.0-release.apk
Verifies
Verified using v1 scheme (JAR signing): false
Verified using v2 scheme (APK Signature Scheme v2): true
Number of signers: 1
```

---

## 3. Physical Device Installation Verification

The signed release APK was installed on the connected Samsung tablet via ADB:

```text
$ adb -s R9ZRB0DE85Y install -r dist/vectora-ai-3.0-release.apk
Performing Streamed Install
Success
```

Installed package verification query:
```text
$ adb -s R9ZRB0DE85Y shell "dumpsys package com.vectora.ai | grep -E 'versionCode|versionName'"
    versionCode=300 minSdk=29 targetSdk=35
    versionName=3.0.0
```

---

## 4. Physical Device Workflow Validation

### 4.1 Home Screen Presentation (`v3_tablet_home.png`)
The application was launched on the tablet and foreground focus confirmed:
```text
mCurrentFocus=Window{c3ab4b9 u0 com.vectora.ai/com.vectora.ai.MainActivity}
```

The home screen displays:
1. **Server Status Indicator:** Shows active inference server status (green when connected, red banner when offline with automatic local caching notice).
2. **Offline Submissions Badge:** Displays count of pending records awaiting synchronisation.
3. **Capture Adult Mosquito Action:** Primary green action button launching CameraX capture and gallery picker.
4. **Record Larvae Video Action:** Secondary button enforcing 3–5 second auto-stop recording rules.
5. **Collection Record Counters:** Adult captures, Larvae captures, Identified specimens, and Pending uploads.

### 4.2 Specimen Crop Screen (`AdultCropScreen.kt`)
- **Preservation of High-Resolution Original:** The camera captures full sensor resolution (up to 4000 × 3000). The full raw image is preserved on storage.
- **Manual Specimen Crop Box:** An interactive rectangular frame allows zooming, panning, and rotation of the specimen region.
- **Coordinate Transmission:** Normalized crop bounding box coordinates ($x, y, w, h \in [0.0, 1.0]$) are bundled with the upload payload.
- **Backend Crop Execution:** The backend applies the bounding box crop to the raw image prior to 224 × 224 model interpolation.

### 4.3 Settings and Server Configuration (`v3_tablet_settings.png`)
- **Configurable Server Address:** Input field allows setting LAN IP (e.g. `http://192.168.1.120:8000/`) or WireGuard tunnel address (`http://10.8.0.1:8000/`).
- **Connection Test:** Executes `/health` probe and confirms round-trip latency.
- **Model Health Inspector:** Queries `/api/v1/models/info` and displays model status: `EXPERIMENTAL_NOT_FIELD_VALIDATED`.
- **Score Policy:** Displays certainty threshold: `65% (Strict Heuristic)` with clear uncalibrated raw score labelling.

### 4.4 Offline Behaviour & Room DB Caching
- When connectivity to the i7 workstation is unavailable, photographs are securely saved to local application storage.
- Submissions are recorded in the Room database with status `PENDING_UPLOAD`.
- Local predictions are prohibited to prevent uncalibrated client drift.
- Background worker (`SyncManager.kt`) retries pending submissions with exponential backoff when connectivity returns.

---

## 5. Summary Matrix

| Verification Requirement | Status | Evidence |
| :--- | :--- | :--- |
| ARM64 release APK compilation | PASS | `dist/vectora-ai-3.0-release.apk` |
| APK Scheme v2 signature | PASS | `apksigner` verified |
| Physical installation on SM-T225 | PASS | ADB streamed install successful |
| Version code 300 / name 3.0.0 | PASS | `dumpsys package` confirmed |
| Home screen action layout | PASS | Physical screenshot `v3_tablet_home.png` |
| Server configuration screen | PASS | Physical screenshot `v3_tablet_settings.png` |
| Specimen crop screen integration | PASS | `AdultCropScreen.kt` code & UI |
| Offline Room DB persistence | PASS | Verified in UI counters and Room schema |
