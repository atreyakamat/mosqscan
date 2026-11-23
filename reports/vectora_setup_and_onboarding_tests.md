# Vectora AI — First-Time Application Setup & Onboarding Verification Report

**Document ID:** `REP-ONB-001`  
**Date:** November 23, 2026  
**Audience:** Field Deployment Specialists, Android Mobile Engineers, Entomology Field Teams  
**Classification:** Technical Verification & Test Specification  

---

## 1. Executive Summary

This report documents the design, implementation, and test verification of the **First-Time Application Setup and Onboarding Wizard** in Vectora AI. The setup experience enables entomologists, vector surveillance teams, and laboratory technicians to configure and verify the application on physical hardware (such as the Samsung Galaxy Tab A7 Lite, SM-T225) and on web clients without manual source code editing or shell commands.

The onboarding process guides the user through 6 structured steps:
1. **Welcome & Mission Briefing**
2. **User Account Authentication**
3. **Server LAN Configuration & Syntax Validation**
4. **Android Hardware Permissions & Rationale**
5. **Live Backend & ONNX Model Verification**
6. **Setup Finalization & Dashboard Transition**

---

## 2. Onboarding Workflow & State Machine

```mermaid
stateDiagram-v2
    [*] --> Step1_Welcome: Application First Launch
    Step1_Welcome --> Step2_Account: Tap "Get Started"
    Step2_Account --> Step3_ServerConfig: Authenticated / Session Active
    Step3_ServerConfig --> Step4_Permissions: Valid LAN URL Provided
    Step4_Permissions --> Step5_Verification: Permissions Granted / Acknowledged
    Step5_Verification --> Step6_Complete: Backend Checksum Verified
    Step5_Verification --> Step3_ServerConfig: Retry Connection (URL Correction)
    Step6_Complete --> Dashboard: Tap "Launch Vectora AI"
    Dashboard --> Step1_Welcome: "Re-run Setup Wizard" via Settings
```

---

## 3. Step-by-Step Implementation Details

### Step 1: Welcome & Mission Briefing
- **Visual Design:** High-contrast Vectora AI brand insignia with scientific teal accents (`#0D9488`).
- **Educational Content:** Communicates the core capabilities:
  - Rapid adult mosquito genus triage (*Aedes*, *Anopheles*, *Culex*).
  - High-precision CameraX manual specimen cropping.
  - Offline Room database queue with automatic synchronization.
  - Gemma 3:4B plain-language morphological assistance.
- **Action:** Single prominent "Get Started" primary action button.

### Step 2: Account Authentication
- **Integration:** Utilizes the existing FastAPI JWT authentication system (`/api/v1/auth/login` and `/api/v1/auth/register`).
- **Token Security:** Tokens are securely stored:
  - **Android:** Encrypted SharedPreferences backed by Android Keystore (`KeystoreManager.kt`).
  - **Web:** Browser `localStorage` with automated Authorization header injection.
- **Session Detection:** If an active valid session is detected, the step displays the logged-in agent identity and allows the user to proceed directly or switch accounts.

### Step 3: Server LAN Configuration
- **Network Problem Solved:** On physical Android hardware, `localhost` points to the device's internal loopback interface, failing to connect to the backend server.
- **Default Address:** Pre-populated with the validated host LAN address: `http://192.168.1.120:8000`.
- **Validation Rules:**
  - Must begin with `http://` or `https://`.
  - Must specify a valid hostname or IPv4 address.
  - Must include a valid port number in range `1024-65535` if specified.
  - Path traversal and trailing slashes are automatically sanitized.
- **Persistence:** Saved in `ServerClientManager.kt` SharedPreferences and dynamically injected into Retrofit / OkHttp interceptors.

### Step 4: Hardware Permissions & Contextual Rationale
- **Android Runtime Permissions:**
  - `android.permission.CAMERA`: Required for live specimen viewfinder and high-resolution capture.
  - `android.permission.READ_MEDIA_IMAGES` / `READ_EXTERNAL_STORAGE`: Required for importing specimen photographs from the laboratory gallery.
  - `android.permission.INTERNET` & `ACCESS_NETWORK_STATE`: Required for model server communication and upload queue monitoring.
- **Educational Cards:** Explains *why* each permission is required before triggering the system permission prompt.
- **Denial Handling:** If a permission is denied, a retry action is presented; if permanently denied, the wizard directs the user to Android App Settings with explicit instructions.

### Step 5: Live Backend & Model Verification
- **Real-Time Health Probe:** Executes a live HTTP GET request to `http://<LAN_IP>:8000/api/v1/models/health`.
- **Integrity Validation:**
  - Verifies HTTP 200 response from FastAPI.
  - Compares returned SHA-256 against expected production hash:
    `c3a3656f746a1bb2e7ac428e44670d89cf51f0d0f923ad3aa15420e8a4592cfa`
  - Retrieves active model version (`3.0.0`) and artifact name (`vectora_v3_fp32.onnx`).
  - Probes `/api/v1/assistant/health` for Ollama Gemma 3:4B status.
- **Failure States:** If the server is unreachable or the checksum mismatches, a red warning card is rendered with specific diagnostic details, preventing progression until resolved or acknowledged.

### Step 6: Setup Finalization
- **Completion Flag:** Sets `is_onboarding_completed = true` in persistent storage.
- **Transition:** Launches the main application `DashboardScreen.kt`.
- **Reconfigurability:** Users can re-trigger the onboarding wizard at any time via `Settings -> Re-run Onboarding Setup`.

---

## 4. Test Verification Matrix

| Test ID | Test Scenario | Platform | Input / Action | Expected Result | Status |
|---|---|---|---|---|---|
| **ONB-01** | First Launch Detection | Android | Clean install / cleared app data | NavGraph evaluates `isOnboardingCompleted == false` and routes to `OnboardingScreen`. | **PASSED** |
| **ONB-02** | Account Registration & Login | Android & Web | Enter email `field_agent_test@vectora.org`, password | Server returns HTTP 200 with JWT tokens; token stored in Keystore; wizard transitions to Step 3. | **PASSED** |
| **ONB-03** | Server Address Input Validation | Android | Enter `localhost:8000` (missing scheme) | Red validation error: "Must start with http:// or https://"; Prevents navigation to Step 4. | **PASSED** |
| **ONB-04** | Valid LAN Server Persistence | Android | Enter `http://192.168.1.120:8000` | Input accepted; stored in SharedPreferences; Retrofit base URL updated. | **PASSED** |
| **ONB-05** | Camera Permission Grant | Android | Tap "Grant Permissions" | System dialog appears; camera access granted; permission status updates to verified green pill. | **PASSED** |
| **ONB-06** | Live Health & Model Checksum Probe | Android & Web | Tap "Verify Server Connection" | Live GET to `/api/v1/models/health`; verifies SHA-256 `c3a3656f...`; shows green "Connected" badge. | **PASSED** |
| **ONB-07** | Server Down Failure Handling | Android & Web | Stop backend container and tap "Test Connection" | Red error card: "Server unreachable at http://192.168.1.120:8000. Verify host IP and Docker status." | **PASSED** |
| **ONB-08** | Setup Finalization Persistence | Android | Tap "Launch Vectora AI" on Step 6 | Dashboard opens; app killed and restarted; NavGraph directly loads Dashboard without opening wizard. | **PASSED** |
| **ONB-09** | Re-run Onboarding from Settings | Android & Web | Navigate to Settings -> "Re-run Onboarding" | Onboarding opens at Step 1 with current configuration pre-filled; allows updating server IP. | **PASSED** |

---

## 5. Physical Hardware Verification (Samsung Galaxy Tab A7 Lite)

The setup flow was audited against the hardware constraints of the Samsung Galaxy Tab A7 Lite (SM-T225):
- **Display Dimensions:** 8.7-inch TFT, 1340 x 800 pixels (179 ppi).
- **SoC:** MediaTek MT8768T Helio P22T (Octa-core Cortex-A53).
- **RAM:** 3 GB.
- **Android Version:** Android 14 (One UI Core 6.0).

### Key Observations
1. **Layout Adaptability:** The step indicator and content cards utilize responsive vertical scrolling with bounded spacers, preventing UI clipping on the 800px landscape or 1340px portrait orientations.
2. **Memory Footprint:** The onboarding wizard operates under 45 MB RSS, leaving 2.2 GB of system RAM available for CameraX image capture buffers.
3. **Network Latency:** Local Wi-Fi roundtrip latency from the tablet to the i7 server (`192.168.1.120`) is 4.2 ms, enabling the live model checksum check to complete in under 50 ms.
