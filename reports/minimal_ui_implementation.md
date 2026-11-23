# Vectora AI - Minimal UI Implementation Report

**Document ID:** `VECTORA-REP-UI-MINIMAL-01`  
**Date:** November 23, 2026  
**Status:** Completed & Verified  
**Scope:** Android Native App (`com.vectora.ai`) and Web Application (`web/`)  

---

## 1. Executive Summary

Vectora AI was simplified from a multi-tab enterprise dashboard with analytics, telemetry, chatbot assistants, and promotional widgets into a streamlined, high-reliability field tool. The revised application strictly adheres to the core mission: rapid specimen capture and genus-level visual identification under field conditions.

### Architectural Transformation Overview

```
[Previous Complex UI]
- Splash Screen (generic)
- Multi-slide Onboarding Carousel
- Dashboard Screen (charts, vector distribution, metrics)
- Analytics / History / Map Explorer
- Gemma Chatbot Assistant
- Adult Scanner Screen
- Larvae Scanner Screen
- Result Screen (with conversational LLM explanation card)
- Bottom Navigation Bar (5 tabs)

                    ↓↓↓ TRANSFORMED TO ↓↓↓

[Minimal High-Reliability UI]
1. Minimal Startup Splash Screen:
   - Vectora AI vector badge + clean branding
   - Non-blocking fade transition (750ms)
   - Intelligent first-launch routing

2. Permission Setup Screen (First-Launch Only):
   - 3 focused cards: Camera (specimen photography), Location (geo-tagging), Photos & Media (fallback import)
   - Live permission status badges (Granted / Not Granted)
   - Non-blocking flow: optional permissions do not gate progress

3. Main Screen (Two Options Only):
   - Heading: "Choose what to scan"
   - Option 1: "Adult Mosquito" (Direct entry to CameraX capture / crop / genus inference)
   - Option 2: "Mosquito Larvae" (Direct entry to 3–5s behavioral video capture, tagged "Research only • Model not field-validated")
   - Top Bar: Vectora AI title and minimal Settings icon (endpoint/auth configuration)
   - Zero tabs, zero dashboards, zero chatbots.
```

---

## 2. Android Native Implementation Details

### 2.1 Navigation Architecture (`Screen.kt` & `VectoraNavGraph.kt`)
- **Route Consolidation**:
  - `Screen.Splash` (`"splash"`): Initial routing controller.
  - `Screen.PermissionSetup` (`"permission_setup"`): First-launch permissions walkthrough.
  - `Screen.Main` (`"main"`): The simplified two-option portal.
  - Retained functional sub-routes: `Screen.Scanner` (`"scanner"`), `Screen.Crop` (`"crop"`), `Screen.Upload` (`"upload"`), `Screen.Result` (`"result/{submissionId}"`), and `Screen.Settings` (`"settings"`).
  - Aliased deprecated routes (`Screen.Dashboard`, `Screen.Onboarding`) to `Screen.Main` for backwards route compatibility.
- **Backstack Safety**:
  - Splash routes directly to `Main` (or `PermissionSetup` if `!isPermissionSetupCompleted`) with `popUpTo(Screen.Splash) { inclusive = true }`.
  - Done action on `ResultScreen` pops back directly to `Screen.Main` with `popUpTo(Screen.Main) { inclusive = false }`.

### 2.2 Startup Splash Screen (`SplashScreen.kt`)
- **Visual Design**: Dark charcoal background (`#111827`) matching Vectora AI's design tokens.
- **Branding**: Clean vector logo icon (`Icons.Default.BugReport` in emerald `#10B981`) paired with clean typography ("Vectora AI - Mosquito Vector Surveillance").
- **Routing Decision Logic**:
  ```kotlin
  val isFirstLaunch = !serverClientManager.isPermissionSetupCompleted
  if (isFirstLaunch) {
      navController.navigate(Screen.PermissionSetup.route) {
          popUpTo(Screen.Splash.route) { inclusive = true }
      }
  } else {
      navController.navigate(Screen.Main.route) {
          popUpTo(Screen.Splash.route) { inclusive = true }
      }
  }
  ```

### 2.3 Permission Setup Screen (`PermissionScreen.kt`)
- **Structure**:
  1. Header: "Device Permissions" and guidance: "Grant camera access to photograph specimens in the field. Location is optional for surveillance geo-tagging."
  2. Camera Access Card: Core hardware requirement. Action triggers `ActivityResultContracts.RequestPermission()`.
  3. Location Access Card: Optional foreground location (`ACCESS_FINE_LOCATION`, `ACCESS_COARSE_LOCATION`). Clearly marked "Optional for GPS mapping".
  4. Photos & Media Card: Optional for specimen import. Fallback on Android 13+ leverages `PickVisualMedia` without requiring broad storage permissions.
- **Non-blocking Progress**:
  - The `Continue` button at the bottom persists `isPermissionSetupCompleted = true` in SharedPreferences and transitions immediately to `Screen.Main`.

### 2.4 Main Screen (`MainScreen.kt`)
- **Layout**: Centered, distraction-free container with title "Choose what to scan".
- **Cards**:
  - **Card 1: Adult Mosquito**
    - Large vector bug icon with emerald tint (`#059669`).
    - Title: "Adult Mosquito".
    - Description: "Photograph specimen for AI genus identification (Aedes, Anopheles, Culex). Includes manual specimen crop."
    - Trailing arrow navigation indicator.
    - Click handler: navigates directly to `Screen.Scanner.createRoute("adult")`.
  - **Card 2: Mosquito Larvae**
    - Wave / water icon with amber tint (`#D97706`).
    - Research Badge: "Research only • Model not field-validated".
    - Title: "Mosquito Larvae".
    - Description: "Record 3–5s specimen movement clip. Saved locally for research submission. Larvae identification model is not yet field-validated."
    - Click handler: navigates directly to `Screen.Scanner.createRoute("larvae")`.

### 2.5 Result Screen Simplification (`ResultScreen.kt`)
- **Removed**: Gemma AI LLM natural language explanation card, complex analytics widgets, and vector mitigation recommendations.
- **Retained**:
  1. Captured specimen image preview with crop overlay.
  2. Predicted genus badge (`AEDES`, `ANOPHELES`, `CULEX`, or `UNCERTAIN`).
  3. Three exact raw probability scores with proportional progress bars.
  4. Inspection metadata: model version (`3.0.0`), ONNX artifact (`vectora_v3_fp32.onnx`), CPU inference latency (ms), and ISO timestamp.
  5. Regulatory banner: `EXPERIMENTAL_NOT_FIELD_VALIDATED - Field inspection required`.
  6. Action buttons: "Done" (returns to Main Screen) and "New Scan".

---

## 3. Web Application Implementation Details

### 3.1 Main Entry (`web/src/app/page.tsx`)
- **Replaced**: Entire landing page with hero marketing banners, interactive charts, and chatbot widgets.
- **New Structure**:
  - Clean Vectora AI header with emerald vector emblem.
  - "Device Access Guidance" informational card explaining browser camera permissions, file drag-and-drop, and location access.
  - "Choose what to scan" selection section with the exact same two cards:
    1. **Adult Mosquito** (links to `/adult`)
    2. **Mosquito Larvae** (links to `/larvae`, with amber "Research only • Model not field-validated" badge)

### 3.2 Navigation Bar (`web/src/components/Navbar.tsx`)
- Trimmed top navigation links to strictly `Adult Mosquito` (`/adult`) and `Mosquito Larvae` (`/larvae`).
- Removed all obsolete links: `/dashboard`, `/analytics`, `/history`, and `/assistant`.
- Maintained Auth state display (Sign In / Register or Log Out).

### 3.3 Adult Specimen Scan Page (`web/src/app/adult/page.tsx`)
- High-fidelity drag-and-drop and file upload with 100×100 px minimum validation and 20 MB size ceiling.
- Interactive manual specimen bounding box preview.
- Removed conversational LLM card; displays raw ONNX probabilities, genus prediction, blur score, and latency.

---

## 4. Source Files Modified & Created

| Component | File Path | Change Description |
|-----------|-----------|--------------------|
| **Android Manifest** | `android/app/src/main/AndroidManifest.xml` | Added foreground location permissions |
| **Android Gradle** | `android/app/build.gradle.kts` | Target SDK set to 34 (Android 14 match), compileSdk set to 35, arm64-v8a ABI filter |
| **Android Nav** | `android/app/src/main/java/com/vectora/ai/ui/navigation/Screen.kt` | Added Splash, PermissionSetup, Main routes |
| **Android Nav Graph** | `android/app/src/main/java/com/vectora/ai/ui/navigation/VectoraNavGraph.kt` | Streamlined flow: Splash -> Permission -> Main -> Capture -> Crop -> Result |
| **Android Splash** | `android/app/src/main/java/com/vectora/ai/ui/screens/SplashScreen.kt` | Minimal branding, theme-aware contrast & smart route resolver |
| **Android Perms** | `android/app/src/main/java/com/vectora/ai/ui/screens/PermissionScreen.kt` | 3 cards with live status, ON_RESUME observer & non-blocking continue |
| **Android Main** | `android/app/src/main/java/com/vectora/ai/ui/screens/MainScreen.kt` | Clean two-option selection screen ("Choose what to scan") |
| **Android Capture** | `android/app/src/main/java/com/vectora/ai/ui/screens/AdultCaptureScreen.kt` | Runtime camera permission request, denial explanation & Gallery fallback |
| **Android Crop** | `android/app/src/main/java/com/vectora/ai/ui/screens/AdultCropScreen.kt` | Square 1:1 crop overlay math and modelVersion 3.0.0 update |
| **Android Upload** | `android/app/src/main/java/com/vectora/ai/ui/screens/AdultUploadScreen.kt` | Offline Room DB queuing (`PENDING_UPLOAD`), retry handler & auth navigation |
| **Android Larvae** | `android/app/src/main/java/com/vectora/ai/ui/screens/LarvaeCaptureScreen.kt` | 3–5s video recording auto-stop at 5.0s, runtime permission check & model isolation |
| **Android Result** | `android/app/src/main/java/com/vectora/ai/ui/screens/ResultScreen.kt` | Minimal result display; uncalibrated raw scores without fabrication; stripped LLM assistant |
| **Android Theme** | `android/app/src/main/java/com/vectora/ai/ui/theme/Theme.kt` | Light theme default, dynamic MaterialTheme semantic colors preventing dark-mode invisibility |
| **Android State** | `android/app/src/main/java/com/vectora/ai/data/remote/ServerClientManager.kt` | Added `isPermissionSetupCompleted` persistent flag |
| **Web Main** | `web/src/app/page.tsx` | Minimal two-option home page with access guidance |
| **Web Nav** | `web/src/components/Navbar.tsx` | Trimmed navLinks to Adult & Larvae only |
| **Web Adult** | `web/src/app/adult/page.tsx` | Stripped Gemma chatbot widget from result card; back navigation to `/` |
| **Web Larvae** | `web/src/app/larvae/page.tsx` | Back navigation to `/`, 3–5s validation, model isolation |

---

## 5. Verification Summary

- **Android Unit Tests**: Passed via `./gradlew testDebugUnitTest` (33 actionable tasks, 0 failures).
- **Android Release Build**: `app-arm64-v8a-release.apk` built cleanly (64-bit native eliminating Android 14 compatibility dialog).
- **Physical Device**: Verified on Samsung Galaxy Tab A7 Lite (SM-T225, Android 14) with 19 step-by-step screenshot artifacts.
- **Web Unit Tests**: 10 unit tests passed via `npm test`.
- **Web Production Build**: Next.js 15 Turbopack static compilation passed (14/14 pages). Container `mosqscan-web` running healthy on port 3001.
- **Backend & Model Tests**: 12/12 end-to-end inference tests passed via `test_end_to_end_inference.py`, SHA-256 `c3a3656...` verified, 20/20 benchmark passed.
