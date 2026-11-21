# Vectora AI — Known Limitations & Technical Constraints

## 1. Machine Learning & Model Limitations

- **Tiny Pilot Dataset**: The approved adult mosquito classifier was trained on a small pilot dataset (44 images from Mendeley Data 88s6fvgg2p v4). It is exploratory and **not field-validated**. It must not be used for clinical, diagnostic, or public health vector control decisions without substantial field validation.
- **Unvalidated Larvae Genus Classifier**: In accordance with the Master Product Specification, the larvae video pipeline performs meniscus edge detection, motion filtering, and keypoint orientation extraction, but **no larvae genus classifier is integrated or validated**. The system explicitly returns `model_not_validated` with prediction `null` to avoid fabricating predictions.
- **Quantization Drift on Ambiguous Specimens**: While FP32 and INT8 ONNX models produce consistent predictions on reference specimens, INT8 dynamic quantization introduces small numerical jitter (~0.05-0.10 probability delta) on out-of-distribution or ambiguous images. The 0.65 uncertainty threshold safely captures these as uncertain.

---

## 2. Platform & Hardware Constraints

- **CPU-Only Execution**: The system is tuned for CPU execution (Intel Core i7-2600 / 16 GB RAM). No CUDA or GPU acceleration is required.
- **Video Codec Compatibility**: OpenCV video decoding relies on container-level FFmpeg codecs (`h264`, `mp4v`, `webm`). Non-standard mobile recording formats (e.g., raw HEVC without container timestamps) must be transcoded or rejected with `VIDEO_CORRUPTED`.
- **Physical Camera Testing**: Emulators simulate CameraX capture with fixed virtual scenes. Verification of focus validation and physical meniscus reflection requires deployment to a physical Android device.
