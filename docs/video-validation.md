# Vectora AI — Video Validation Specification

## 1. Scope & Objective

Mosquito larvae locomotion analysis uses short video clips of living larvae submerged in water. To prevent unbounded compute usage and ensure locomotion features are representative, Vectora AI strictly enforces a **3.0 to 5.0 second** video duration rule across all platforms.

---

## 2. Validation Matrix

| Decoded Duration ($t$) | Android Action | Web Frontend Action | Server API Result | Status Code | Error Code |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **$t < 3.00\text{ s}$** | Recording disabled from stopping early | Client rejection message | Rejected | `422 Unprocessable Entity` | `VIDEO_TOO_SHORT` |
| **$3.00\text{ s} \le t \le 5.00\text{ s}$** | Accepted | Accepted | Processed | `202 Accepted` | `None` |
| **$t > 5.00\text{ s}$** | Hard auto-stop enforced at $5.00\text{ s}$ | Rejected with explicit error | Rejected | `422 Unprocessable Entity` | `VIDEO_TOO_LONG` |
| **Corrupted Media** | Recording error toast | Format error prompt | Rejected | `422 Unprocessable Entity` | `VIDEO_CORRUPTED` |

---

## 3. Mandatory Implementation Constraints

1. **No Client Trimming**:
   The web platform and backend **must not** automatically trim, crop, or shorten an uploaded video longer than 5 seconds. Videos longer than 5 seconds are rejected outright.
2. **Server-Side Timestamp Verification**:
   The server decodes actual media frames and container timestamps using OpenCV (`cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)`). Client metadata and file headers are never trusted.
3. **Android Video Recording Rules**:
   - The recording timer starts when CameraX video capture begins.
   - Manual stop button is locked/disabled for the first 3.0 seconds.
   - Recording stops automatically at 5.0 seconds.
   - Encoded duration is validated prior to local persistence or synchronization.

---

## 4. API Error Contract

Duration rejection responses follow strict structured schemas:

```json
{
  "success": false,
  "error_code": "VIDEO_TOO_SHORT",
  "message": "The video must be at least 3 seconds."
}
```

```json
{
  "success": false,
  "error_code": "VIDEO_TOO_LONG",
  "message": "The video must not exceed 5 seconds."
}
```

---

## 5. Automated Verification

The automated test suite in `backend/tests/test_video_validation.py` explicitly tests the following exact boundaries:
- `2.99s` $\rightarrow$ Rejected (`VIDEO_TOO_SHORT`)
- `3.00s` $\rightarrow$ Accepted
- `4.00s` $\rightarrow$ Accepted
- `5.00s` $\rightarrow$ Accepted
- `5.01s` $\rightarrow$ Rejected (`VIDEO_TOO_LONG`)
- Corrupted file $\rightarrow$ Rejected (`VIDEO_CORRUPTED`)
