# Vectora AI — Android APK Release & Integrity Report

**Document ID:** `REP-APK-001`  
**Date:** November 23, 2026  
**Audience:** Release Engineering, Mobile QA, Field Deployment Operations  
**Classification:** Production Verification Artifact  

---

## 1. Executive Summary

This report provides the cryptographically verified release manifest for all production Android APK variants of **Vectora AI v3.0.0 (Build 300)**. Each package has been compiled using the Android Gradle Plugin, minified via Proguard/R8, aligned with `zipalign`, and signed with APK Signature Scheme v2 using the production release keystore (`/home/nimr/.android/vectora_release.keystore`).

Every APK was verified using Android SDK build-tools `aapt` (v34.0.0) and `apksigner` (v34.0.0).

---

## 2. Release Package Manifest

| Artifact Filename | Target ABI Architecture | File Size (Bytes) | File Size (MB) | SHA-256 Checksum | Signature Scheme v2 | Verification Status |
|---|---|---|---|---|---|---|
| **`app-armeabi-v7a-release.apk`** | 32-bit ARM (`armeabi-v7a`) | 4,743,850 B | 4.52 MB | `7047dfa30839354cc95e4fd2163c18df15e159985db282fe999d9d0fc7d8c687` | **Verified** | **DEPLOYED (SM-T225)** |
| **`app-arm64-v8a-release.apk`** | 64-bit ARM (`arm64-v8a`) | 4,752,472 B | 4.53 MB | `ebf8d3b4f1445bf887c8759f16a3ba302f3a7a8dfbb048ef64a128fc76607dd1` | **Verified** | Production Ready |
| **`app-universal-release.apk`** | Multi-ABI (Universal) | 4,985,346 B | 4.75 MB | `1c9c95f1b9fe3bc736a73a4d18e8bfb9711883e6948d0b762cf5435224f61bc5` | **Verified** | Multi-Device Sideload |
| **`app-x86_64-release.apk`** | 64-bit x86 (`x86_64`) | 4,771,559 B | 4.55 MB | `6785784b3a60c18dd6e38fa256e263b4bd10c9cb1e95ff9b8517d2e666c9bdd2` | **Verified** | Emulator / ChromeOS |
| **`app-x86-release.apk`** | 32-bit x86 (`x86`) | 4,761,738 B | 4.54 MB | `9c0d8aa84a15e62f8bd2854402d399c658fb9a0d007eb70a5921e4a55a1cb197` | **Verified** | Legacy x86 Emulators |

---

## 3. Package Identity & Metadata Specifications

All variants share unified package definitions extracted via `aapt dump badging`:

- **Application ID:** `com.vectora.ai`
- **Version Code:** `300`
- **Version Name:** `3.0.0`
- **Minimum SDK Level:** `29` (Android 10.0)
- **Target SDK Level:** `35` (Android 15)
- **Compile SDK Level:** `35`
- **Application Class:** `com.vectora.ai.VectoraApp`
- **Main Activity:** `com.vectora.ai.MainActivity`
- **R8 Minification:** Enabled (`isMinifyEnabled = true`, `isShrinkResources = true`)
- **ProGuard Rules:** `proguard-android-optimize.txt`, `proguard-rules.pro`

---

## 4. Cryptographic Signature Verification (`apksigner`)

Verification executed on each artifact with `/home/nimr/Android/Sdk/build-tools/34.0.0/apksigner verify --verbose`:

```
Verifies: True
Verified using v1 scheme (JAR signing): false
Verified using v2 scheme (APK Signature Scheme v2): true
Verified using v3 scheme (APK Signature Scheme v3): false
Verified using v4 scheme (APK Signature Scheme v4): false
Number of signers: 1
Signer #1 certificate DN: CN=Vectora AI Release, OU=Vector Surveillance, O=Vectora AI, L=Bengaluru, ST=Karnataka, C=IN
Signer #1 key algorithm: RSA 2048-bit
Signer #1 digest algorithm: SHA-256
Signer #1 signature algorithm: SHA256withRSA
```

---

## 5. Physical Target Deployment Sign-off

The `app-armeabi-v7a-release.apk` build was selected for physical sideloading onto the **Samsung Galaxy Tab A7 Lite (SM-T225)**:

- **Processor:** MediaTek MT8768T Helio P22T
- **Primary ABI:** `armeabi-v7a`
- **Sideload Command:** `adb install -r -d app-armeabi-v7a-release.apk`
- **Result:** `Performing Streamed Install -> Success`
- **Launch Verification:** `com.vectora.ai/.MainActivity` running under PID `22514` / `23647` without crashes.
- **Operating Memory:** ~45 MB heap footprint, ~92 MB RSS.
