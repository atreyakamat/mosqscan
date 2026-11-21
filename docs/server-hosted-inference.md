# Vectora AI 2.2 — Server-Hosted Inference Documentation

## 1. Overview and Purpose

Vectora AI 2.2 moves mosquito adult specimen identification from on-device Android inference to server-hosted inference on the local development machine.
This design eliminates mobile processor constraints, removes the heavy ONNX Runtime binary and model weights from the production APK, and allows the deployment of full-precision FP32 models.

---

## 2. Host Machine Hardware and Runtime Environment

The inference service runs on the development workstation with the following hardware specifications:
- **Processor**: Intel Core i7-2600 CPU @ 3.40 GHz (4 physical cores, 8 logical execution threads).
- **Instruction Set Support**: MMX, SSE, SSE2, SSE3, SSSE3, SSE4.1, SSE4.2, AVX. (Note: AVX2 and FMA are not supported on Sandy Bridge microarchitecture).
- **System Memory**: 16 GB DDR3 RAM.
- **Operating System**: Linux (Omarchy Linux / Arch-based kernel 6.17.7).
- **Execution Engine**: ONNX Runtime CPU (`onnxruntime` v1.31.1).
- **Application Framework**: FastAPI with Python 3.12 running under Uvicorn inside Docker container `vectora-backend`.

---

## 3. Lifespan Startup Sequence and Model Verification

The model loads strictly during the FastAPI application `lifespan` startup event before the server accepts HTTP traffic (`backend/app/main.py`).
The startup sequence performs five sequential integrity checks (`backend/app/inference/adult_classifier.py`):

1. **Path Resolution**:
   The service verifies the existence of `models/vectora_candidate_exp_b.onnx`.
   If the file does not exist, the server halts startup immediately with `RuntimeError`.

2. **Cryptographic Checksum Verification**:
   The service computes the SHA-256 hash of the candidate model file:
   - Expected Hash: `d644b9cd9c952d461bbfbb44e8b1926cdcf9bbbfb9cd43f85065cbed0d7b1499`
   - If the computed hash does not match, startup fails with `RuntimeError: Model integrity check failed`.
   This prevents serving unverified or corrupted model checkpoints.

3. **Inference Session Initialization**:
   An ONNX Runtime `InferenceSession` is initialized using CPU execution provider `CPUExecutionProvider`.
   Thread parameters are strictly configured:
   - `intra_op_num_threads = 2`: Limits intra-op parallelism to 2 threads to prevent thread contention.
   - `inter_op_num_threads = 1`: Executes operations sequentially within a graph run.
   - `execution_mode = ExecutionMode.ORT_SEQUENTIAL`.

4. **Input and Output Tensor Shape Validation**:
   The session inspects the computational graph:
   - Input shape must match `[1, 3, 224, 224]` with float32 data type.
   - Output shape must match `[1, 3]` corresponding to the 3 target mosquito genera (`aedes`, `anopheles`, `culex`).

5. **Warm-up Smoke Inference**:
   The session executes a synthetic forward pass using a zeros tensor `np.zeros((1, 3, 224, 224), dtype=np.float32)`.
   Only when the smoke test returns valid logits does the service report healthy and register the classifier.

---

## 4. Concurrency Control and Event Loop Protection

To ensure low latency and prevent high CPU load on the quad-core host:
- **Async Semaphore**: Concurrency is bounded by an `asyncio.Semaphore(1)` in `AdultClassifier.predict_async()`.
  This allows only 1 concurrent inference operation at any given moment.
  Simultaneous incoming requests queue in memory and execute sequentially.
- **Off Event Loop Execution**: Model inference uses a dedicated `ThreadPoolExecutor(max_workers=1)`.
  Inference computation runs via `loop.run_in_executor()`, ensuring the FastAPI async event loop never blocks during ONNX computation.
- **Worker Configuration**: The Uvicorn server runs with a single process worker inside Docker to maintain deterministic CPU affinity.

---

## 5. Specimen Cropping and Image Processing Pipeline

Every adult submission follows a strict image processing pipeline (`backend/app/services/adult_service.py`):

```mermaid
flowchart TD
    A[Client Request: Original Image + Crop Bounding Box] --> B[Save Original Photo to media/photos/]
    B --> C[EXIF Orientation Correction via ImageOps.exif_transpose]
    C --> D{Validate Crop Coordinates?}
    D -- Valid [0.0 <= x < x+w <= 1.0] --> E[Extract Crop from Transposed Image]
    D -- Invalid or Missing --> F[Full-Image Fallback]
    E --> G[Save Crop as Secondary Artifact in media/crops/]
    F --> G
    G --> H[Image Quality Evaluation: Blur and Brightness]
    H --> I[Resize Crop to 224x224 RGB]
    I --> J[Normalize: Mean [0.485, 0.456, 0.406], Std [0.229, 0.224, 0.225]]
    J --> K[Async ONNX Runtime CPU Inference]
    K --> L[Softmax Calculation & Quality Feedback Synthesis]
    L --> M[Store Submission Record in Database & Return Response]
```

### 5.1 EXIF Orientation
Android and mobile cameras embed orientation metadata in EXIF headers.
The server applies `PIL.ImageOps.exif_transpose(image)` immediately upon opening the file.
This prevents rotated or inverted images from corrupting bounding box math.

### 5.2 Bounding Box Application
The endpoint accepts normalized coordinates `[0.0, 1.0]`:
- `crop_x`: Left offset relative to image width.
- `crop_y`: Top offset relative to image height.
- `crop_w`: Bounding box width relative to image width.
- `crop_h`: Bounding box height relative to image height.
- Alternatively, client can supply `crop_box` as a JSON string `{"x": 0.1, "y": 0.1, "w": 0.6, "h": 0.6}`.

If crop dimensions are valid (width and height > 0.05 and within bounds `[0, 1]`), the specimen rectangle is sliced from the original high-resolution photograph.
If coordinates are out of bounds or missing, the server logs a warning and falls back to using the full image.

### 5.3 Secondary Artifact Storage
The original high-resolution photograph is always preserved untouched under `media/photos/`.
The extracted crop is saved as an independent JPEG image under `media/crops/` and recorded in the database `media_files` table with artifact type `specimen_crop`.

---

## 6. Model Status and Scientific Disclaimer

The candidate Exp B model is an experimental research model.
The API response includes explicit status fields:
- `raw_score`: Uncalibrated softmax score (floating point value between 0.0 and 1.0).
- `model_status`: `EXPERIMENTAL_NOT_FIELD_VALIDATED`.
- `quality_feedback`: Assessment of specimen blur (`sharp`, `blurry`), brightness (`optimal`, `too_dark`, `too_bright`), and crop size.

Clients and researchers must treat all predictions as uncalibrated research indications, not certified diagnostic decisions.
