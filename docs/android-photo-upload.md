# Vectora AI 2.2 — Android Specimen Capture and Photo Upload

## 1. Overview

Vectora AI 2.2 transitions the Android client from an on-device inference engine to an authenticated client for server-hosted inference.
The mobile application handles field acquisition: capturing high-resolution photos, allowing manual specimen crop framing, storing pending uploads locally in Room, and transmitting specimens to the development server over the local network.

---

## 2. Capture and Selection Workflows

The specimen acquisition interface is implemented in `android/app/src/main/java/com/vectora/ai/ui/screens/AdultCaptureScreen.kt`.
It provides two primary input pathways:

### 2.1 CameraX Specimen Capture
- **Camera Provider**: CameraX `ProcessCameraProvider` configured with high-resolution JPEG capture (`ImageCapture.CAPTURE_MODE_MAXIMIZE_QUALITY`).
- **Framing Reticle**: On-screen circular and rectangular target overlay guides the field researcher to place the adult mosquito in the center of the frame.
- **Flash / Torch Control**: An on-screen toggle allows switching the flash unit (`FLASH_MODE_ON`, `FLASH_MODE_OFF`, `FLASH_MODE_AUTO`) for low-light specimen photography.
- **Tap-to-Focus**: Uses `MeteringPointFactory` to focus and meter light on the specimen.

### 2.2 Gallery Photo Picker
- **Modern Photo Picker**: Uses Android's system `ActivityResultContracts.PickVisualMedia` with media type filter `PickVisualMedia.ImageOnly`.
- **System Fallback**: If the Android system lacks Google Play Services Photo Picker support, the client falls back to `ActivityResultContracts.GetContent` (`image/*`).
- **EXIF Preservation**: Gallery selections preserve original orientation headers and pixel data.

---

## 3. Specimen Crop and Framing Interface

Specimen framing is handled in `android/app/src/main/java/com/vectora/ai/ui/screens/AdultCropScreen.kt`:

1. **Visual Framing Canvas**:
   The captured photo is displayed on a Compose canvas.
   A semi-transparent mask covers the outer boundaries while an illuminated square reticle highlights the selected specimen region.

2. **90-Degree Clockwise Rotation**:
   A dedicated rotate button allows the user to rotate the image in 90-degree increments.
   This ensures mosquitoes photographed at awkward field angles can be properly oriented before cropping.

3. **Crop Size Adjustment**:
   Sliders and gesture controls permit resizing the crop window (range 40% to 100% of frame dimensions).
   The interface calculates normalized coordinates relative to image width and height:
   - `crop_x`: Normalized horizontal start coordinate `[0.0, 1.0]`
   - `crop_y`: Normalized vertical start coordinate `[0.0, 1.0]`
   - `crop_w`: Normalized width `[0.05, 1.0]`
   - `crop_h`: Normalized height `[0.05, 1.0]`

4. **Retake and Re-pick**:
   Navigation buttons allow the user to retake the camera photo or open the gallery picker again if the image is out of focus.

---

## 4. Local Persistence and Offline Capture Queue

Before network transmission, the application creates a persistent record in the local Room database (`android/app/src/main/java/com/vectora/ai/data/local/db/`):

- **Database Version**: Room database upgraded to Version 2.
- **Migration Schema**:
  ```sql
  ALTER TABLE submissions ADD COLUMN status TEXT NOT NULL DEFAULT 'COMPLETED';
  ALTER TABLE submissions ADD COLUMN cropX REAL;
  ALTER TABLE submissions ADD COLUMN cropY REAL;
  ALTER TABLE submissions ADD COLUMN cropW REAL;
  ALTER TABLE submissions ADD COLUMN cropH REAL;
  ALTER TABLE submissions ADD COLUMN rawScore REAL;
  ALTER TABLE submissions ADD COLUMN modelStatus TEXT;
  ```
- **Initial State**: New captures receive status `PENDING_UPLOAD`.
- **File Storage**: The original uncropped image is saved to app-internal storage (`context.filesDir/submissions/`).
  The original image is never modified or compressed during local storage.

---

## 5. Authenticated Multipart Upload Flow

Network submission is orchestrated by `android/app/src/main/java/com/vectora/ai/ui/screens/AdultUploadScreen.kt`:

1. **Authentication Token**:
   Requests include an `Authorization: Bearer <token>` header injected by `AuthInterceptor`.
   Tokens are stored encrypted in Android Keystore via `KeystoreManager`.

2. **Multipart Request Structure**:
   - `file`: Original high-resolution photograph (`image/jpeg`).
   - `crop_x`: Float string representing crop left boundary.
   - `crop_y`: Float string representing crop top boundary.
   - `crop_w`: Float string representing crop width.
   - `crop_h`: Float string representing crop height.
   - Target Endpoint: `POST /api/v1/adult/submit`.

3. **Progress Tracking**:
   The user interface displays four operational states:
   - `PREPARING`: Validating image file and reading coordinates.
   - `UPLOADING`: Streaming multipart payload to the server.
   - `PROCESSING`: Waiting for server-hosted ONNX Runtime CPU inference.
   - `COMPLETED`: Result received, database record updated, and transition to Result screen.

4. **Network Resilience and Offline Mode**:
   If the server is unreachable (HTTP timeout, connection refused, or DNS resolution failure):
   - The UI displays an "Offline / Queued" notification.
   - The record status remains `PENDING_UPLOAD` in the local Room database.
   - An orange warning badge appears on the Dashboard and History screens indicating unsynced records.
   - A "Retry Sync" action enables uploading the queued specimens once connectivity to the host server is restored.

---

## 6. Honest Scientific Result Presentation

Results are displayed in `android/app/src/main/java/com/vectora/ai/ui/screens/ResultScreen.kt`:

- **Confidence Threshold**:
  If the top predicted genus has a raw softmax score lower than `0.65`, the application does NOT declare a definitive species or genus.
  Instead, it displays:
  > **Identification Uncertain — Specialist Review Required**
  > (Raw confidence score: 0.54 — Below field-validation threshold of 0.65).
- **Experimental Notice**:
  Displays an amber alert banner:
  > `EXPERIMENTAL MODEL (Candidate Exp B): Predictions are not certified for clinical or diagnostic use.`
- **Metrics Displayed**:
  - Genus classification (`Aedes`, `Anopheles`, `Culex`) or Uncertain.
  - Raw uncalibrated softmax score (e.g., `0.941`).
  - Server inference processing time in milliseconds (e.g., `62 ms`).
  - Image quality flags (sharpness and illumination).
  - Visual preview of both original image and extracted specimen crop.
