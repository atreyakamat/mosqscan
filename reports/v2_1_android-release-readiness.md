# Vectora AI 2.1 — Android Release Readiness Report

## 1. Executive Summary

This report documents the Android release readiness for Vectora AI 2.1.
All release build configurations, cryptographic signing pipelines, and binary optimizations were completed.
The release build generates ABI-split APKs with uncompressed ONNX model assets.
Automated unit tests pass with zero failures.
Physical device status and manual testing procedures are documented in this report.

---

## 2. Release Signing Configuration

### 2.1 Secret Management
Release signing credentials must not be stored in version control.
The file `android/app/build.gradle.kts` was configured to read signing parameters from local properties, environment variables, or Gradle properties in order of precedence:
1. `android/signing.properties` (gitignored local file)
2. Environment variables (`VECTOR_KEYSTORE_PATH`, `VECTOR_KEYSTORE_PASSWORD`, `VECTOR_KEY_ALIAS`, `VECTOR_KEY_PASSWORD`)
3. Gradle properties (`~/.gradle/gradle.properties`)

If these configurations are absent, Gradle builds unsigned release binaries without errors.

Both root `.gitignore` and `android/.gitignore` explicitly block all keystore and credential files:
```gitignore
*.jks
*.keystore
signing.properties
keystore.properties
```

### 2.2 Production Keystore Specification
A dedicated release keystore was generated outside the repository:
- **Keystore location**: `/home/nimr/.android/vectora_release.keystore`
- **Key alias**: `vectora_release_key`
- **Algorithm**: RSA 2048-bit
- **Validity**: 10,000 days
- **Certificate Distinguished Name**: `CN=Vectora AI, OU=Engineering, O=Vectora Org, L=Bangalore, ST=Karnataka, C=IN`

### 2.3 Signature Verification
The release APK was verified using the Android SDK `apksigner` tool:
```bash
/home/nimr/Android/Sdk/build-tools/35.0.0/apksigner verify --verbose \
  android/app/build/outputs/apk/release/app-arm64-v8a-release.apk
```

**Verification Output**:
- Result: `Verifies`
- APK Signature Scheme v1 (JAR signing): `false`
- APK Signature Scheme v2 (APK Signature Scheme v2): `true`
- Number of signers: `1`

---

## 3. Binary Optimization, ABI Splitting, and ProGuard

### 3.1 ABI Splits
Android devices use different CPU architectures.
Packing all native ONNX Runtime libraries into one APK causes excessive binary size.
ABI splitting was activated in `android/app/build.gradle.kts`.

Generated APK artifacts in `android/app/build/outputs/apk/release/`:

| Artifact | Target Architecture | File Size | Recommended Target |
| :--- | :--- | :--- | :--- |
| `app-arm64-v8a-release.apk` | 64-bit ARM (modern devices) | 26 MB | Standard production deployment |
| `app-armeabi-v7a-release.apk` | 32-bit ARM (legacy devices) | 21 MB | Older field hardware |
| `app-x86_64-release.apk` | 64-bit x86 | 28 MB | Emulators and ChromeOS |
| `app-x86-release.apk` | 32-bit x86 | 28 MB | Emulators |
| `app-universal-release.apk` | All supported architectures | 79 MB | Fallback distribution |

Targeting `arm64-v8a` reduces user download size by 67% compared to the universal APK (26 MB vs 79 MB).

### 3.2 Uncompressed ONNX Model Asset
ONNX Runtime on Android benefits from uncompressed assets.
Compressed assets cannot be directly accessed via file descriptors without extra decompression overhead.

In `android/app/build.gradle.kts`:
```kotlin
androidResources {
    noCompress += listOf("onnx")
}
```

Asset inspection via `unzip -lv android/app/build/outputs/apk/release/app-arm64-v8a-release.apk`:
```
  Length   Method   Size     Ratio   Date       Time   CRC-32   Name
 4360533   Stored  4360533    0%     1981-01-01 01:01  58077165 assets/efficientnet_b0_int8.onnx
```
The INT8 ONNX model asset is stored with 0% compression.

### 3.3 ProGuard / R8 JNI Reflection Keep Rules
With `isMinifyEnabled = true`, R8 obfuscates bytecode and strips unreferenced reflection symbols.
Initial on-device execution produced a fatal native crash (`SIGABRT` in `ai.onnxruntime.OrtSession.run` with `JNI DETECTED ERROR: java_class == null in call to GetMethodID`) because ONNX Runtime JNI reflection classes were obfuscated.

To resolve this blocker, `android/app/proguard-rules.pro` was created with explicit keep rules:
```proguard
-keep class ai.onnxruntime.** { *; }
-dontwarn ai.onnxruntime.**
-keep class com.vectora.ai.domain.model.** { *; }
-keep class com.vectora.ai.inference.** { *; }
```
Rebuilding with these rules eliminated the crash and verified on-device inference execution.

---

## 4. Automated Android Test Results

The Android unit test suite was executed:
```bash
cd android && ./gradlew test
```

Results:
- Total tests executed: 18 (9 debug variants, 9 release variants).
- Failures: 0.
- Errors: 0.
- Skipped: 0.

Covered test suites:
- `com.vectora.ai.ModelContractTest` (4 tests per variant): Verifies class labels, label count, probability sum normalization, and prediction confidence types.
- `com.vectora.ai.VideoRecordingRulesTest` (4 tests per variant): Verifies 3.0-second minimum duration, 5.0-second hard auto-stop, and frame rate boundaries.
- `com.vectora.ai.ImageQualityValidatorTest` (1 test per variant): Verifies image resolution and aspect ratio constraints.

---

## 5. Physical Device Status and Installation

### 5.1 ADB Device State
Command execution:
```bash
adb devices -l
```
Output:
```
List of devices attached
R9ZRB0DE85Y            device usb:2-1.7 product:gta7litexx model:SM_T225 device:gta7lite transport_id:1
```

**Status Assessment**:
A physical Samsung Galaxy Tab A7 Lite device (`SM_T225`, ARM64) is connected via USB and verified in `device` (authorized) status.

### 5.2 APK Installation Verification
The signed release APK was installed onto the connected hardware:
```bash
adb install -r android/app/build/outputs/apk/release/app-arm64-v8a-release.apk
```
Output:
```
Performing Streamed Install
Success
```

### 5.3 On-Device Execution Verification
1. Granted camera and audio permissions via ADB package manager:
   ```bash
   adb shell pm grant com.vectora.ai android.permission.CAMERA
   adb shell pm grant com.vectora.ai android.permission.RECORD_AUDIO
   ```
2. Launched release application activity:
   ```bash
   adb shell am start -W -n com.vectora.ai/com.vectora.ai.MainActivity
   ```
   Result: Launched cleanly in 1334 ms with focus `Window{... com.vectora.ai.MainActivity}`.
3. Verified UI Hierarchy:
   - "Offline AI Inference Ready"
   - "ONNX Mobile INT8 • Model v1.0.0 • No internet required for adult identification"
   - "Capture Adult Mosquito" and "Record Larvae Video" options displayed.
4. Camera Preview: Initialized without distortion or frame drops.
5. In-flight Specimen Capture: Tested capture flow; confirmed ONNX inference runs without JNI reflection crashes following ProGuard remediation.

---

## 6. Step-by-Step Physical Device Test Protocol

Field testers must follow this exact sequence to complete physical acceptance testing:

### Test Case 1: Application Launch and Permissions
1. Launch the Vectora AI app on the device.
2. Verify that the app requests `CAMERA` and `RECORD_AUDIO` permissions.
3. Grant permissions.
4. Verify that the Camera Preview initializes without black frames or distortion.

### Test Case 2: Adult Mosquito Offline Inference
1. Switch to Airplane Mode (disable Wi-Fi and Cellular Data).
2. Point the camera at a mosquito specimen or test card.
3. Tap the Capture button.
4. Verify that the app displays the inference result in under 200 ms.
5. Verify that the genus classification displays one of: `Aedes`, `Anopheles`, `Culex`, or `Uncertain`.
6. Verify that an uncalibrated confidence score percentage is shown.

### Test Case 3: Larvae Video Recording Duration Constraints
1. Switch to Larvae Video Mode.
2. Press and hold (or tap) Record.
3. Attempt to stop before 3.0 seconds: Verify that the UI displays a warning and rejects videos shorter than 3 seconds.
4. Start recording and let it run: Verify that the recording stops automatically when the timer reaches 5.0 seconds.
5. Verify that the recorded video is saved to local storage.

### Test Case 4: Local Offline History and Filtering
1. Open the History tab while still in Airplane Mode.
2. Verify that all captured adult scans and recorded larvae videos appear in the local list.
3. Verify that genus filters (`Aedes`, `Anopheles`, `Culex`) filter the list correctly.
4. Verify that tapping an item opens the detailed scan view.

### Test Case 5: Background Synchronization
1. Re-enable Wi-Fi or Cellular Data.
2. Pull down to refresh or observe background sync.
3. Verify that pending local records upload to the Vectora backend without data loss.
