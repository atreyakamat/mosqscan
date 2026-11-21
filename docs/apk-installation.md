# Vectora AI 2.2 — Android Release APK Installation Guide

## 1. Release Artifact Specification

The signed release APK is packaged and distributed in the root `dist/` directory:
- **File Path**: `dist/vectora-ai-2.2-release.apk`
- **Application ID**: `com.vectora.ai`
- **Version Code**: `2`
- **Version Name**: `2.2.0`
- **Target Architecture (ABI)**: `arm64-v8a` (64-bit ARM)
- **Minimum SDK**: API 26 (Android 8.0 Oreo)
- **Target SDK**: API 35 (Android 15)
- **Binary Size**: ~23 MB (24,113,382 bytes)
- **SHA-256 Checksum**:
  ```
  b9967a881fca55ff29272948ae678a0bb4d185e48125b93696a3b856ed1e564b
  ```

---

## 2. Model Asset Exclusion Verification

Vectora AI 2.2 offloads model execution to the server.
The release build explicitly excludes all heavy ONNX neural network weights.

Verify with `unzip`:
```bash
unzip -l dist/vectora-ai-2.2-release.apk | grep -i "\.onnx"
```
**Expected Result**: Zero lines returned (exit code 1).
No `.onnx` models reside inside the production APK.

---

## 3. Cryptographic Signature Verification

The release APK is signed with the Vectora release keystore (`/home/nimr/.android/vectora_release.keystore`).

Verify the signature using the Android SDK `apksigner`:
```bash
/home/nimr/Android/Sdk/build-tools/35.0.0/apksigner verify --verbose dist/vectora-ai-2.2-release.apk
```

**Verification Output**:
- **Result**: `Verifies`
- **APK Signature Scheme v1 (JAR signing)**: `false`
- **APK Signature Scheme v2 (APK Signature Scheme v2)**: `true`
- **Number of signers**: `1`
- **Signer #1 Certificate DN**: `CN=Vectora AI, OU=Engineering, O=Vectora Org, L=Bangalore, ST=Karnataka, C=IN`
- **Key Algorithm**: RSA 2048-bit

---

## 4. Device Installation via ADB

Connect an Android device (ABI `arm64-v8a`) via USB with Developer Mode and USB Debugging enabled.

### 4.1 Check Connected Devices
```bash
adb devices -l
```

### 4.2 Install or Upgrade the APK
```bash
adb install -r dist/vectora-ai-2.2-release.apk
```
*Note: The `-r` flag reinstalls the application while preserving existing local database records.*

### 4.3 Launch the Application
```bash
adb shell monkey -p com.vectora.ai -c android.intent.category.LAUNCHER 1
```

---

## 5. Required Permissions

During first execution, the application requests the following runtime permissions:
- **`android.permission.CAMERA`**: Required for live camera capture in `AdultCaptureScreen`.
- **`android.permission.INTERNET`**: Required for network communication with the development server.
- **`android.permission.ACCESS_NETWORK_STATE`**: Required for network status detection and offline queue fallback.
