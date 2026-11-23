# Vectora AI — Product UI, Application Setup & Release Readiness Audit

**Document Reference:** `reports/vectora_product_ui_audit.md`  
**Evaluation Standard:** ASD-STE100 Technical English  
**Environment:** Linux 7.2.8-9-omarchy (x86_64), Intel Core i7-2600 CPU @ 3.40 GHz, 16 GB RAM  
**Active Model Artifact:** `models/vectora_v3_fp32.onnx`  
**Model Checksum (SHA-256):** `c3a3656f746a1bb2e7ac428e44670d89cf51f0d0f923ad3aa15420e8a4592cfa`  
**Operational Status:** `EXPERIMENTAL_NOT_FIELD_VALIDATED`  

---

## 1. Executive Summary

This audit assesses the state of Vectora AI across the native Android client, the responsive Next.js web application, the FastAPI backend, and the local Gemma 3:4B AI assistant. The project goal is to convert the existing codebase into a cohesive, production-ready scientific application for adult mosquito identification (*Aedes*, *Anopheles*, *Culex*).

The active ONNX classification model (`vectora_v3_fp32.onnx`) is preserved and verified. Its class index mapping (0: *Aedes*, 1: *Anopheles*, 2: *Culex*) and scientific disclaimer (`EXPERIMENTAL_NOT_FIELD_VALIDATED`) remain unchanged.

---

## 2. Codebase Architecture & Existing State

### 2.1 Android Application (`/android`)
* **Framework:** Jetpack Compose, Material3, Kotlin 1.9.23, Gradle 8.9, AGP 8.5.2.
* **Target Hardware:** Samsung Galaxy Tab A7 Lite (SM-T225, Android 14) and Android phones (Min SDK 29, Target SDK 35).
* **Storage & Security:** Room DB (`vectora_ai.db`), Android Keystore (`KeystoreManager` using AES-256-GCM encrypted SharedPreferences).
* **Networking:** Retrofit 2, OkHttp 3, Gson converter with dynamic base URL (`ServerClientManager`).
* **Existing Screens:**
  1. `DashboardScreen`: Overview card, submission counters, recent items, server ping.
  2. `AdultCaptureScreen`: CameraX preview, flash controls, gallery launcher, centering box.
  3. `AdultCropScreen`: EXIF orientation handling, normalized bounding box crop (x, y, w, h).
  4. `AdultUploadScreen`: Progress bar, multipart submission with crop coordinates, error handling.
  5. `ResultScreen`: Genus card, model version, experimental disclaimer, metadata breakdown.
  6. `HistoryScreen`: Room-backed tabbed listing (All, Adult, Larvae).
  7. `SettingsScreen`: Server URL input, health check trigger, model health verification.
  8. `AuthScreen`: Sign-in and registration forms with Keystore token persistence.
  9. `LarvaeCaptureScreen`: 3–5 second video validation with research status disclaimers.

### 2.2 Web Application (`/web`)
* **Framework:** Next.js 15.5.29 (Turbopack), React 19, TypeScript 5, Tailwind CSS v4.
* **Architecture:** App router (`/src/app`), Client-side authentication context (`/src/lib/auth.tsx`), Axios client with auto-refresh interceptors (`/src/lib/api.ts`).
* **Existing Routes:**
  1. `/` (Dashboard): Marketing landing when logged out, metrics and recent submissions when logged in.
  2. `/adult`: File dropzone, crop window sliders, submission action, result display.
  3. `/history`: Paginated history table with genus and status filtering.
  4. `/larvae`: 3–5 second locomotion video validation.
  5. `/login` & `/register`: JWT token authentication forms.
  6. `/profile`: User role and account information.
  7. `/admin`: User management and audit logs.

### 2.3 Backend API (`/backend`)
* **Framework:** FastAPI 0.115.5, Uvicorn 0.32.1, Pydantic v2, SQLAlchemy 2.0.
* **Core Endpoints:**
  * `POST /api/v1/auth/login`, `POST /api/v1/auth/register`, `GET /api/v1/auth/me`
  * `POST /api/v1/adult/submit` (Supports multipart file + `crop_x, crop_y, crop_w, crop_h` or `crop_box`)
  * `GET /api/v1/adult/submissions/{id}`, `GET /api/v1/adult/submissions/{id}/image`
  * `GET /api/v1/submissions` (User-scoped history with search, type, and date filters)
  * `GET /api/v1/dashboard/stats` (User-scoped statistics)
  * `GET /api/v1/models/health`, `GET /api/v1/models/info`
  * `POST /api/v1/assistant/explain-result`, `POST /api/v1/assistant/chat`, `POST /api/v1/assistant/summarize-history`, `GET /api/v1/assistant/health`
* **Inference Pipeline:** ONNX Runtime FP32 with single-thread/two-thread allocation tuned for Intel Core i7-2600.
* **Local Assistant:** Ollama HTTP client targeting Gemma 3:4B with ASD-STE100 guardrails.

---

## 3. Detailed Audit Findings & Gaps

| Area | Component | Existing Condition | Identified Gap / Required Remediation | Severity |
| :--- | :--- | :--- | :--- | :--- |
| **First-Time Setup** | Android | App defaults directly to `DashboardScreen`. | No onboarding flow. If server is unconfigured, users must navigate deep into settings. Missing permission explanation step. | **High** |
| **First-Time Setup** | Web | Navigating to app presents login or empty dashboard. | No guided setup / server connection verification dialog for new researchers. | **Medium** |
| **AI Assistant** | Android | No assistant screen or result explanation integration. | `VectoraNavGraph` lacks an assistant route. `ResultScreen` lacks the "Explain with Vectora AI" button. | **High** |
| **AI Assistant** | Web | `/assistant` route does not exist. | Users cannot interact with Gemma 3:4B or request AI explanation on scan results directly from Web. | **High** |
| **Scan Results** | Android | Shows single predicted genus and raw score. | Must display all 3 raw class scores (*Aedes*, *Anopheles*, *Culex*) explicitly as uncalibrated model scores. | **High** |
| **Scan Results** | Web | Shows raw score distribution bars. | Lacks "Explain with Vectora AI" action to trigger `/api/v1/assistant/explain-result`. | **Medium** |
| **Scan History** | Android | Simple list based on Room database only. | Needs specimen image thumbnail rendering, genus filtering, search bar, and full detail view. | **Medium** |
| **Scan History** | Web | History table without specimen thumbnails. | Needs specimen thumbnail images retrieved via `/api/v1/adult/submissions/{id}/image`. | **Medium** |
| **Settings** | Web | No dedicated `/settings` page. | Settings are split across `/profile` and navbar; no server health / model integrity inspector on web. | **Medium** |
| **Settings** | Android | Functional but basic. | Needs dedicated sync queue controls (view pending uploads, manual "Sync Now" action, last sync timestamp). | **Medium** |
| **Design System** | Both | Functional UI but inconsistent styling and visual language. | Need coherent scientific design tokens (clean neutrals, deep charcoal `#1E293B`, restrained teal `#0D9488`, clear cards, refined shadows). | **High** |
| **Larvae Workflow**| Both | Video upload forms exist. | Must maintain explicit disclaimers that larvae classification is `model_not_validated` and research-only. | **High** |

---

## 4. Remediation and Implementation Plan

1. **Design System & Visual Consistency:**
   * Standardize color palette across Jetpack Compose (`Color.kt`, `Theme.kt`) and Web Tailwind CSS (`globals.css`).
   * Implement shared design tokens for cards, buttons, badges, status banners, and loading skeletons.

2. **Android Setup & Onboarding Flow:**
   * Create `OnboardingScreen.kt` with a 5-step guided wizard:
     1. Welcome & capabilities overview.
     2. Server configuration (auto-detects LAN address `192.168.1.120:8000`, test connection).
     3. User account setup (Sign in / Register).
     4. Permissions rationale (Camera, Storage, Network).
     5. Connection verification and completion.
   * Wire onboarding into `VectoraNavGraph` as start destination when unconfigured.

3. **Android AI Assistant & Result Explanation:**
   * Create `AssistantScreen.kt` with a conversational chat interface communicating with `/api/v1/assistant/chat`.
   * Update `ResultScreen.kt` to:
     * Display all 3 raw uncalibrated model scores (*Aedes*, *Anopheles*, *Culex*).
     * Add "Explain with Vectora AI" card calling `/api/v1/assistant/explain-result`.
     * Handle graceful degradation if Ollama is stopped.

4. **Web UI Upgrades:**
   * Add `/assistant` page with interactive conversational UI, quick prompt starters, and history summarization.
   * Add `/settings` page with server health, model checksum verification, sync status, and account security.
   * Update `/adult` result card to feature "Explain with Vectora AI" action.
   * Update `/history` to render specimen thumbnails and allow rich inspection.
   * Add guided Setup modal for first-time web users.

5. **Offline Queue & Sync Experience:**
   * Enhance `SyncManager.kt` on Android to support explicit "Sync Now" requests, displaying pending queue items and updating Room state upon server receipt.

6. **End-to-End Verification & Release Artifacts:**
   * Verify all backend routes, execute `test_end_to_end_inference.py`.
   * Compile Android debug and release APKs.
   * Build Web production bundle (`npm run build`).
   * Produce comprehensive verification and readiness reports.
