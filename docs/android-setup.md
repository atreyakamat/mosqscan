# Android Build Setup — Vectora AI

This document describes how to build, run, and package the Vectora AI Android application.

---

## Prerequisites

Ensure the following tools are installed and on your `PATH`:

| Tool | Required Version | Notes |
|------|----------------|-------|
| Android SDK | API 34 (target) / API 35 (compile) | Install via Android Studio SDK Manager |
| Android NDK | 26.x | Required for native ONNX Runtime |
| Java / JDK | 17+ (27 recommended) | `java -version` to confirm |
| Gradle | 8.9 | Wrapper in repo — no manual install needed |
| Android Studio | Hedgehog or later | Optional but recommended |

> [!IMPORTANT]
> The ONNX Runtime Android AAR library requires NDK 26. Using an older NDK will cause build failures during native library linking.

Verify your environment:
```bash
java -version
# openjdk version "27.x.x" ...

sdkmanager --list | grep "ndk;26"
# ndk;26.x.x | ...
```

---

## Clone and Open

```bash
git clone <repo-url>
cd mosqscan/android
```

Open the `android/` directory in Android Studio, or build from the command line.

---

## Model Asset Packaging

The INT8 ONNX model must be placed in the app's assets before building:

```bash
# From the repository root
cp vectora-ai-starter/models/efficientnet_b0_int8.onnx \
   android/app/src/main/assets/efficientnet_b0_int8.onnx
```

Verify the checksum matches the registry:
```bash
sha256sum android/app/src/main/assets/efficientnet_b0_int8.onnx
# Expected: bac40d9af5441ddbdb6c6b19348fe04167ca4d8de7466611742022b7f505bd95
```

> [!CAUTION]
> Never bundle the FP32 model (`efficientnet_b0.onnx`) in the Android APK. It is 15 MB larger than the INT8 variant and is reserved for the backend. Use only `efficientnet_b0_int8.onnx` on Android.

---

## Build Steps

### Debug Build

```bash
cd android
./gradlew assembleDebug
```

The APK will be output to:
```
android/app/build/outputs/apk/debug/app-debug.apk
```

### Release Build (unsigned)

```bash
./gradlew assembleRelease
```

---

## Run on Device

Connect an Android device via USB with Developer Options and USB Debugging enabled:

```bash
# Install debug APK on connected device
./gradlew installDebug

# Or use adb directly
adb install app/build/outputs/apk/debug/app-debug.apk
```

For emulator:
```bash
# Launch emulator (from Android Studio AVD Manager, or CLI)
emulator -avd Pixel_8_API_34 &
./gradlew installDebug
```

---

## Run Unit Tests

```bash
# Local JVM unit tests
./gradlew test

# Instrumented tests (requires connected device or emulator)
./gradlew connectedAndroidTest
```

---

## Signing for Release

1. **Generate a keystore** (one-time):
   ```bash
   keytool -genkey -v \
     -keystore vectora-release.jks \
     -alias vectora \
     -keyalg RSA \
     -keysize 2048 \
     -validity 10000
   ```

2. **Configure signing** in `android/app/build.gradle.kts`:
   ```kotlin
   android {
       signingConfigs {
           create("release") {
               storeFile = file("../../vectora-release.jks")
               storePassword = System.getenv("KEYSTORE_PASSWORD")
               keyAlias = "vectora"
               keyPassword = System.getenv("KEY_PASSWORD")
           }
       }
       buildTypes {
           release {
               signingConfig = signingConfigs.getByName("release")
               isMinifyEnabled = true
               proguardFiles(
                   getDefaultProguardFile("proguard-android-optimize.txt"),
                   "proguard-rules.pro"
               )
           }
       }
   }
   ```

3. **Build signed APK**:
   ```bash
   export KEYSTORE_PASSWORD=<your-password>
   export KEY_PASSWORD=<your-key-password>
   ./gradlew assembleRelease
   ```

   Signed APK location:
   ```
   android/app/build/outputs/apk/release/app-release.apk
   ```

> [!WARNING]
> Never commit the keystore file or passwords to version control. Store them in a secrets manager (e.g., GitHub Actions secrets, GCP Secret Manager).

---

## Key Gradle Properties

| Property | Value | Purpose |
|----------|-------|---------|
| `compileSdk` | 35 | Compile against Android 15 APIs |
| `targetSdk` | 34 | Target Android 14 |
| `minSdk` | 26 | Minimum Android 8.0 (ONNX Runtime minimum) |
| `versionCode` | 1 | Integer build number |
| `versionName` | "1.0.0" | Human-readable version |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ONNX model load failed` | Model file missing from assets | Copy INT8 model to `app/src/main/assets/` |
| `NDK version mismatch` | Wrong NDK installed | Install NDK 26 via SDK Manager |
| `Unsupported class file version` | Java version too old | Switch to JDK 17+ |
| `Gradle sync failed` | Gradle wrapper not set up | Run `./gradlew wrapper --gradle-version 8.9` |
