# Vectora AI — Android Application Readiness Report

**Document Reference:** `reports/vectora_android_readiness.md`  
**Target Hardware:** Samsung Galaxy Tab A7 Lite (SM-T225, Android 14) & Standard Android Devices  
**Minimum SDK:** 29 (Android 10) | **Compile & Target SDK:** 35 (Android 15)  
**Release Version:** 3.0.0 (Build Code 300)  
**Status:** BUILD VERIFIED & RELEASE READY  

---

## 1. Executive Summary

The native Android client for Vectora AI has been updated to deliver a professional, fluid, and robust user experience. The application features a complete 6-step onboarding and setup wizard, direct integration with the local Gemma 3:4B assistant, explicit 3-genus raw score visualization, and offline-first Room database queuing with batch synchronization.

Both Debug and Release APK builds compile successfully, with release artifacts signed by the verified release keystore (`/home/nimr/.android/vectora_release.keystore`).

---

## 2. Architecture & Technological Framework

| Subsystem | Technology | Purpose & Implementation |
| :--- | :--- | :--- |
| **UI Layer** | Jetpack Compose & Material3 | Declarative, reactive UI following the Vectora Scientific Design System. |
| **Theme & Tokens** | Material3 `lightColorScheme` & `darkColorScheme` | Custom tokens (`VectoraTeal`, `VectoraSlate`, `VectoraEmerald`, `VectoraAmber`). |
| **Camera & Capture** | AndroidX CameraX (`1.4.0`) | High-resolution image capture with flash modes, back-camera binding, and framing box. |
| **Gallery Ingestion** | Android Photo Picker (`ActivityResultContracts.PickVisualMedia`) | Privacy-compliant media selection without broad storage permissions. |
| **Local Storage** | Room Database v3 (`AppDatabase.kt`, `SubmissionEntity.kt`) | SQLite persistence with offline upload queue (`PENDING_UPLOAD`). |
| **Security** | Android Keystore (`KeystoreManager.kt`) | Hardware-backed AES-256-GCM encryption for JWT authentication tokens. |
| **Networking** | Retrofit 2 (`2.11.0`) & OkHttp 3 (`4.12.0`) | Dynamic base URL management, token interceptors, and multipart upload. |
| **Local AI** | Gemma 3:4B via FastAPI Assistant Routes | Natural-language explanation and interactive research chat. |

---

## 3. Screen Implementations & User Workflows

### 3.1 First-Time Setup Wizard (`OnboardingScreen.kt`)
* **Step 1 (Welcome):** Vectora AI brand identity, product introduction, and capability overview.
* **Step 2 (Account Setup):** Sign in or account registration with instant Keystore session persistence.
* **Step 3 (Server Configuration):** Backend URL configuration defaulting to the i7 host LAN address (`http://192.168.1.120:8000`), with an interactive "Test Connection" button calling `/health` and `/api/v1/models/health`.
* **Step 4 (Device Permissions):** Plain-language rationale for Camera and Storage permissions, with graceful handling of denied states.
* **Step 5 (Connection Verification):** End-to-end service verification confirming the backend, ONNX model artifact, and local AI assistant.
* **Step 6 (Setup Completion):** Summary confirmation, setting `isOnboardingCompleted = true` and navigating to Dashboard.

### 3.2 Adult Mosquito Specimen Scanning (`AdultCaptureScreen.kt` & `AdultCropScreen.kt`)
* **Viewfinder:** Centered framing box with clear instructions for specimen positioning.
* **Gallery Fallback:** Direct access to device photos via the system Photo Picker.
* **EXIF Correction & Manual Rotation:** Preserves natural mosquito geometry without distortion.
* **Normalized Specimen Crop:** Allows positioning and resizing of the region of interest; generates normalized coordinates `(x, y, w, h)` identical to the backend contract.

### 3.3 Result Inspection & Raw Score Breakdown (`ResultScreen.kt`)
* **Specimen Display:** Renders the photographed mosquito.
* **Predicted Genus:** Clear genus identification (*Aedes*, *Anopheles*, or *Culex*) with certainty evaluation.
* **Uncalibrated Model Scores:** Explicit distribution bars for all three genera, with clear disclaimers that values are uncalibrated softmax logits, not field-validated confidence percentages.
* **Explain with Vectora AI:** One-tap action calling `/api/v1/assistant/explain-result` using Gemma 3:4B on the host CPU. If the assistant is offline, displays a friendly offline notification without altering the classification.
* **Safety Banner:** Prominent `EXPERIMENTAL_NOT_FIELD_VALIDATED` notice.

### 3.4 Scan History & Offline Queue (`HistoryScreen.kt` & `SyncManager.kt`)
* **Specimen Thumbnails:** High-performance local thumbnail rendering directly from cached image files.
* **Filter Chips:** Instant filtering by genus (*Aedes*, *Anopheles*, *Culex*, Uncertain, Pending Upload).
* **Search:** Case-insensitive search by submission ID or genus name.
* **Offline Queue Management:** Pending specimens (`PENDING_UPLOAD`) are visibly badged and can be uploaded immediately or via "Sync Now".

### 3.5 AI Research Assistant (`AssistantScreen.kt`)
* Conversational chat interface targeting local Gemma 3:4B.
* Quick inquiry chips for morphological traits and taxonomic differences.
* Clear "Assistant Offline" state if Ollama is stopped, ensuring users know scanning remains functional.

---

## 4. Build Artifacts & Signing Verification

* **Debug Artifacts:**
  * Universal APK: `android/app/build/outputs/apk/debug/app-universal-debug.apk`
  * Architecture APKs: `arm64-v8a`, `armeabi-v7a`, `x86`, `x86_64`
* **Release Artifacts:**
  * Universal APK: `android/app/build/outputs/apk/release/app-universal-release.apk`
  * Signed by Keystore: `/home/nimr/.android/vectora_release.keystore`
  * Keystore Alias: `vectora_release_key`
  * Minification: R8 / Proguard optimizations applied.

---

## 5. Unit & Automated Test Results

* Task: `:app:testDebugUnitTest`
* Execution Environment: OpenJDK 17.0.21 on Linux Omarchy
* Result: **100% Passed (BUILD SUCCESSFUL)**
* Modules Verified:
  * Database schema migrations (v2 -> v3)
  * Preprocessor image normalization
  * Keystore encryption and decryption cycles
  * SyncManager queue logic
