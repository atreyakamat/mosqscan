# Vectora AI - Permission Setup Verification Report

**Document ID:** `VECTORA-REP-PERM-SETUP-01`  
**Date:** November 23, 2026  
**Status:** Verified on Physical Hardware  
**Target Device:** Samsung Galaxy Tab A7 Lite (SM-T225, Android 14 / One UI 6.0, Serial: `R9ZRB0DE85Y`)  

---

## 1. Executive Summary

This report validates the implementation and runtime behavior of the dedicated **Permission Setup Screen** in Vectora AI. The permission architecture was designed to satisfy field operational needs while strictly adhering to Android 14 permission guidelines:
1. **Camera Permission** (`android.permission.CAMERA`): Required for live specimen viewfinder and 3–5s larvae clip recording. Gracefully degrades to system Photo Picker on denial.
2. **Foreground Location Permissions** (`ACCESS_FINE_LOCATION`, `ACCESS_COARSE_LOCATION`): Strictly optional for GPS geo-tagging of vector surveillance sites.
3. **Photos & Media Access** (`READ_MEDIA_IMAGES`, `READ_EXTERNAL_STORAGE`): Optional for gallery import. Leverages zero-permission `PickVisualMedia` contract on modern Android.
4. **Non-Blocking User Flow**: Users are never blocked from using the application if optional permissions are withheld.
5. **Persistent Setup State**: On initial launch, the user views the permission walkthrough. Subsequent launches bypass the setup screen and open directly to the Main Screen.

---

## 2. Android Manifest & Permission Definitions

The following permissions are defined in `android/app/src/main/AndroidManifest.xml`:

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-feature
        android:name="android.hardware.camera"
        android:required="false" />

    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <uses-permission android:name="android.permission.CAMERA" />
    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
    <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
    <uses-permission
        android:name="android.permission.READ_EXTERNAL_STORAGE"
        android:maxSdkVersion="32" />
    <uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />
...
```

### Key Technical Aspects
- `android.hardware.camera` is marked `required="false"` to allow installation on specialized field hardware or tablets where camera features might be restricted.
- Background location permissions (`ACCESS_BACKGROUND_LOCATION`) are intentionally excluded to prevent Google Play policy compliance issues and minimize battery consumption in field tablets.
- Storage permissions are scoped by SDK version (`maxSdkVersion="32"` for `READ_EXTERNAL_STORAGE` and `READ_MEDIA_IMAGES` for SDK 33+).

---

## 3. UI Component Architecture (`PermissionScreen.kt`)

The permission screen is structured with three dedicated cards, each managing its own permission lifecycle and state indicator:

```
┌────────────────────────────────────────────────────────┐
│                   Vectora AI Logo                      │
│                  Device Permissions                    │
│ "Grant camera access to photograph specimens..."       │
├────────────────────────────────────────────────────────┤
│ [📷] Camera Access                     [ Granted / ]   │
│      Required for real-time mosquito    [ Not Granted] │
│      photography and larvae recording.                 │
│      [Grant Camera Access]                             │
├────────────────────────────────────────────────────────┤
│ [📍] Location Access                   [ Optional / ]  │
│      Optional for GPS geo-tagging       [ Granted ]    │
│      surveillance field sites.                         │
│      [Grant Location Access]                           │
├────────────────────────────────────────────────────────┤
│ [🖼️] Photos & Media                    [ Available ]   │
│      Import saved specimen photographs                 │
│      from device gallery.                              │
├────────────────────────────────────────────────────────┤
│                                                        │
│                [ Continue to App  → ]                  │
└────────────────────────────────────────────────────────┘
```

### Dynamic State Resolution
Each permission card dynamically resolves its status:
```kotlin
val cameraGranted = ContextCompat.checkSelfPermission(
    context, Manifest.permission.CAMERA
) == PackageManager.PERMISSION_GRANTED

val locationGranted = ContextCompat.checkSelfPermission(
    context, Manifest.permission.ACCESS_FINE_LOCATION
) == PackageManager.PERMISSION_GRANTED || ContextCompat.checkSelfPermission(
    context, Manifest.permission.ACCESS_COARSE_LOCATION
) == PackageManager.PERMISSION_GRANTED
```

### Non-blocking Continuation
When the user taps **"Continue to App"**:
```kotlin
Button(
    onClick = {
        serverClientManager.isPermissionSetupCompleted = true
        onPermissionsCompleted()
    },
    modifier = Modifier.fillMaxWidth().height(50.dp)
) {
    Text("Continue to App")
}
```
The application persists the completion status and invokes `onPermissionsCompleted()`, navigating directly to `Screen.Main` with backstack pruning.

---

## 4. State Persistence & Launch Routing

Persistence is handled in `ServerClientManager.kt` via Android `SharedPreferences`:

```kotlin
var isPermissionSetupCompleted: Boolean
    get() = prefs.getBoolean(KEY_PERMISSION_SETUP_COMPLETED, false)
    set(value) = prefs.edit().putBoolean(KEY_PERMISSION_SETUP_COMPLETED, value).apply()
```

### Routing Matrix

| Condition | Action in `SplashScreen.kt` | Next Screen |
|-----------|-----------------------------|-------------|
| First launch after fresh install | `isPermissionSetupCompleted == false` | `Screen.PermissionSetup` |
| First launch, user tapped "Continue" | Sets `isPermissionSetupCompleted = true` | `Screen.Main` |
| Subsequent launches | `isPermissionSetupCompleted == true` | `Screen.Main` directly (bypasses permissions) |
| App data cleared (`pm clear`) | Resets `isPermissionSetupCompleted` to `false` | `Screen.PermissionSetup` |

---

## 5. Physical Hardware Verification Records

### Test Platform
- **Device Model**: Samsung Galaxy Tab A7 Lite (SM-T225)
- **OS Version**: Android 14 / One UI 6.0
- **Build**: ARM64 Native Release Build (`app-arm64-v8a-release.apk`)
- **Target SDK**: 34 / **Compile SDK**: 35

### Verification Test Cases

| Case ID | Scenario | Procedure | Expected Result | Actual Result | Status |
|---------|----------|-----------|-----------------|---------------|--------|
| **PR-01** | Fresh install launch | Install release APK via ADB on clean tablet, start `MainActivity`. | Splash displays, auto-navigates to Permission Setup Screen without OS compatibility popups. | Splash displayed, routed to Permission Setup. Native 64-bit ABI eliminated Android 14 warning popup. Screenshot: `reports/screenshots/step2_permission_setup.png`. | **PASS** |
| **PR-02** | Camera permission request | Tap "Grant Camera Access" button on Camera card. | Android OS runtime permission dialog appears ("While using the app"). | OS dialog appeared; when approved, badge updated to green "Granted". Screenshot: `reports/screenshots/step5_adult_camera_permission_request.png`. | **PASS** |
| **PR-03** | Optional location withholding | Leave location ungranted and tap "Continue to App". | App proceeds immediately to Main Screen without blocking or errors. | Navigated directly to Main Screen. Screenshot: `reports/screenshots/step3_main_screen.png`. | **PASS** |
| **PR-04** | Subsequent launch bypass | Kill app task (`am force-stop`), relaunch via ADB. | Splash displays, directly opens Main Screen without showing Permission Setup. | Main Screen opened directly in 750ms. Screenshot: `reports/screenshots/step4_relaunch_main_screen.png`. | **PASS** |
| **PR-05** | Fallback on camera denial | Select "Don't allow" on camera permission dialog. | Viewfinder displays clean explanation card with settings button and gallery fallback. | Clean explanation card displayed with Gallery button and Open Settings button. Screenshot: `reports/screenshots/step6_permission_denied_screen.png`. | **PASS** |
| **PR-06** | CameraX preview upon grant | Return from settings or grant camera permission. | Live CameraX viewfinder initializes smoothly on resume. | Preview initialized with specimen bounding guide. Screenshot: `reports/screenshots/step8_camera_preview_active.png`. | **PASS** |

---

## 6. Web Application Device Access Verification

On the Web client (`web/src/app/page.tsx`), native OS permission requests differ from Android. To provide equivalent clarity:
1. **Device Access Guidance Card**: Displayed on the home screen (`http://localhost:3001`), educating users that:
   - Web camera streaming uses `navigator.mediaDevices.getUserMedia`.
   - File drag-and-drop requires no browser permissions.
   - Geolocation queries the HTML5 Geolocation API on explicit user action.
2. Verified responsive rendering in mobile tablet browsers and desktop viewports.

---

## 7. Conclusion

The permission setup workflow functions smoothly and complies fully with Android 14 permission policies. The user is guided clearly on initial launch, optional permissions are strictly non-blocking, and subsequent launches bypass the setup step with zero UI latency.
