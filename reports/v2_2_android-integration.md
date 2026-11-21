# Vectora AI 2.2 — Android Client Integration Report

## 1. Executive Summary

This report documents the Android native client integration for Vectora AI 2.2.
The mobile application was transformed into a client for server-hosted inference while retaining offline capture resilience.
All user interface screens, CameraX capture pipelines, specimen cropping interfaces, Room database v2 migrations, and network layers were implemented and verified on physical hardware.

---

## 2. Architecture and Component Overview

The application is built using modern Android Jetpack standards:
- **UI Framework**: Jetpack Compose with Material 3 styling.
- **Camera Subsystem**: CameraX (v1.4.0) with tap-to-focus and flash controls.
- **Local Persistence**: Room Database (v2.6.1) with SQLite.
- **Networking**: Retrofit 2 (v2.11.0) and OkHttp 4 (v4.12.0).
- **Security**: Android Keystore for AES-GCM token encryption and network security configuration.

---

## 3. Screen Implementations

### 3.1 Specimen Capture (`AdultCaptureScreen.kt`)
- CameraX `ImageCapture` configured for maximum JPEG quality.
- On-screen circular and square targeting reticle for specimen alignment.
- Flash toggle cycle: `Off` -> `On` -> `Auto`.
- System Photo Picker integration (`ActivityResultContracts.PickVisualMedia`) with fallback to `GetContent`.
- Real-time sharpness and illumination assessment prior to proceeding.

### 3.2 Specimen Crop Framing (`AdultCropScreen.kt`)
- Displays captured photograph on Compose Canvas with crop overlay.
- 90-degree clockwise image rotation button allows real-time re-orientation.
- Adjustable crop reticle calculating normalized bounding box coordinates `(crop_x, crop_y, crop_w, crop_h)` in range `[0.0, 1.0]`.
- Navigation options: "Confirm Crop & Upload", "Retake Photo", and "Pick From Gallery".
- Creates initial Room entity with status `PENDING_UPLOAD`.

### 3.3 Specimen Upload (`AdultUploadScreen.kt`)
- Constructs authenticated multipart request:
  - Part `file`: Raw image bytes.
  - Parts `crop_x, crop_y, crop_w, crop_h`: Normalized float strings.
- Interactive progress bar and phase descriptions: `PREPARING`, `UPLOADING`, `PROCESSING`, `COMPLETED`.
- Offline resilience: If network times out or drops, the submission remains in `PENDING_UPLOAD` status with an on-screen retry button.

### 3.4 Scientific Results (`ResultScreen.kt`)
- **Uncertain Classification Guard**: If confidence is below `0.65`, the top genus is NOT claimed. Instead, the screen displays **"Identification Uncertain — Verification Required"**.
- Displays uncalibrated raw score (e.g., `0.941`).
- Displays server inference duration (e.g., `62 ms`).
- Amber disclaimer banner: `EXPERIMENTAL MODEL (Candidate Exp B): Predictions are not certified for clinical or diagnostic use.`
- Side-by-side preview of the original capture and the extracted crop region.

### 3.5 Settings and Connectivity (`SettingsScreen.kt`)
- Editable `VECTORa_API_BASE_URL` persisted in SharedPreferences. Default: `http://192.168.1.120:8000/`.
- **Test Connection** button invokes `GET /health` to confirm server responsiveness.
- **Check Model Health** button invokes `GET /api/v1/models/info` to verify model status, checksum, and active classes.

### 3.6 Dashboard and History Integration
- `DashboardScreen.kt`: Shows server connectivity badge (Online / Offline) and pending upload alert counter.
- `HistoryScreen.kt`: Displays status tags (`PENDING_UPLOAD` vs `COMPLETED`) with one-tap upload triggers for offline captures.

---

## 4. Room Database Schema Migration (Version 2)

Room database upgraded from Version 1 to Version 2 in `android/app/src/main/java/com/vectora/ai/data/local/db/`:
- Added fields: `status` (String, default `COMPLETED`), `cropX` (Float), `cropY` (Float), `cropW` (Float), `cropH` (Float), `rawScore` (Float), `modelStatus` (String).
- Automatic migration path configured using `fallbackToDestructiveMigration()` or schema migration statements to preserve user records.

---

## 5. Security and Network Hardening

### 5.1 Network Security Config (`res/xml/network_security_config.xml`)
- Enforces strict HTTPS by default (`cleartextTrafficPermitted="false"`).
- Permits cleartext traffic exclusively to development endpoints:
  - `192.168.1.120` (Development Host LAN IP)
  - `10.0.2.2` (Android Emulator Loopback)
  - `localhost` / `127.0.0.1`
- Removed `android:usesCleartextTraffic="true"` from `AndroidManifest.xml`.

### 5.2 Token Storage
- User authentication tokens are encrypted using AES-GCM-256 with keys managed by Android Keystore.
- Tokens are injected into HTTP requests via `AuthInterceptor`.

---

## 6. Release Build and Asset Exclusion

### 6.1 Gradle Asset Separation
In `android/app/build.gradle.kts`:
```kotlin
sourceSets {
    getByName("main") {
        assets.setSrcDirs(emptyList<String>())
    }
    getByName("debug") {
        assets.setSrcDirs(listOf("src/main/assets"))
    }
}
```
- Release builds package 0 model files.
- Debug builds retain `src/main/assets/` to ensure regression tests and model parity tests pass.

### 6.2 Binary Verification
- Output File: `dist/vectora-ai-2.2-release.apk`
- Size: **24,113,382 bytes** (~23 MB).
- Model Check: `unzip -l dist/vectora-ai-2.2-release.apk | grep -i "\.onnx"` returned **0 results**.
- Signature: Scheme v2 verified by `apksigner`.

---

## 7. Physical Hardware Testing

- **Target Device**: Samsung Galaxy Tab A7 Lite (`SM_T225`)
- **Device Serial**: `R9ZRB0DE85Y`
- **Architecture**: `arm64-v8a` (Android 14 / API 34)
- **Installation**: Successfully installed via `adb install -r dist/vectora-ai-2.2-release.apk`.
- **Live Network Verification**:
  Logcat verified live HTTP ping to `http://192.168.1.120:8000/health`:
  ```
  11-12 12:50:41.182 I okhttp.OkHttpClient: --> GET http://192.168.1.120:8000/health
  11-12 12:50:41.380 I okhttp.OkHttpClient: <-- 200 OK http://192.168.1.120:8000/health (198ms)
  11-12 12:50:41.381 I okhttp.OkHttpClient: {"status":"healthy","service":"vectora-ai-backend","version":"2.0.0","environment":"production"}
  ```
