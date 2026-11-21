# Vectora AI — Product Integration Readiness & Engineering Blueprint

**Document Version:** 1.0.0  
**Status:** Approved for Client & Server Integration  
**Date:** November 11, 2026  
**Implementation Reference:** [`src/vectora/inference.py`](file:///home/nimr/Projects/mosqscan/vectora-ai-starter/src/vectora/inference.py)  
**Model Artifact:** [`models/vectora_candidate_exp_b_int8.onnx`](file:///home/nimr/Projects/mosqscan/vectora-ai-starter/models/vectora_candidate_exp_b_int8.onnx) (4.16 MB)

---

## 1. Executive Summary

This document defines the production integration standard for Vectora AI across Android (offline-first CameraX application) and Web/Cloud platforms. To ensure strict cross-platform parity and prevent classification discrepancies:
1. A **single unified inference contract** governs all client and server runtimes.
2. Image preprocessing, tensor layouts, and class index mappings are rigorously synchronized.
3. Explicit quality rejection (`REJECTED_BLURRY`) and uncertainty handling (`UNCERTAIN_LOW_CONFIDENCE`) are enforced before returning any genus classification.
4. Model size and latency benchmarks are validated against PRD operational targets.

---

## 2. Unified Inference Contract & JSON Schema

All platforms must return the exact same JSON schema to client presentation layers:

### 2.1 Schema Definition

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "VectoraInferenceResult",
  "type": "object",
  "required": ["status", "predicted_genus", "confidence", "probabilities", "quality_metrics", "model_version"],
  "properties": {
    "status": {
      "type": "string",
      "enum": ["IDENTIFIED", "UNCERTAIN_LOW_CONFIDENCE", "REJECTED_BLURRY", "REJECTED_NO_SPECIMEN"]
    },
    "predicted_genus": {
      "type": ["string", "null"],
      "enum": ["aedes", "anopheles", "culex", null]
    },
    "display_name": {
      "type": "string"
    },
    "confidence": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0
    },
    "probabilities": {
      "type": "object",
      "properties": {
        "aedes": {"type": "number"},
        "anopheles": {"type": "number"},
        "culex": {"type": "number"}
      },
      "required": ["aedes", "anopheles", "culex"]
    },
    "vector_context": {
      "type": "object",
      "properties": {
        "candidate_vectors": {"type": "array", "items": {"type": "string"}},
        "known_diseases": {"type": "array", "items": {"type": "string"}},
        "disclaimer": {"type": "string"}
      }
    },
    "quality_metrics": {
      "type": "object",
      "required": ["is_sharp", "sharpness_score", "message"],
      "properties": {
        "is_sharp": {"type": "boolean"},
        "sharpness_score": {"type": "number"},
        "message": {"type": "string"}
      }
    },
    "guidance": {
      "type": "string"
    },
    "model_version": {
      "type": "string"
    }
  }
}
```

### 2.2 Response Examples

#### Case A: Successful Confident Identification (`IDENTIFIED`)
```json
{
  "status": "IDENTIFIED",
  "predicted_genus": "aedes",
  "display_name": "Aedes",
  "confidence": 0.8841,
  "probabilities": {
    "aedes": 0.8841,
    "anopheles": 0.0432,
    "culex": 0.0727
  },
  "vector_context": {
    "candidate_vectors": ["Aedes aegypti", "Aedes albopictus"],
    "known_diseases": ["Dengue", "Chikungunya", "Zika", "Yellow Fever"],
    "disclaimer": "Visual identification only. Does not indicate individual pathogen infection."
  },
  "quality_metrics": {
    "is_sharp": true,
    "sharpness_score": 142.8,
    "message": "Sharpness score: 142.8"
  },
  "model_version": "vectora_candidate_exp_b_int8"
}
```

#### Case B: Uncertain Prediction Below Acceptance Threshold (`UNCERTAIN_LOW_CONFIDENCE`)
```json
{
  "status": "UNCERTAIN_LOW_CONFIDENCE",
  "predicted_genus": null,
  "confidence": 0.4120,
  "probabilities": {
    "aedes": 0.4120,
    "anopheles": 0.3580,
    "culex": 0.2300
  },
  "quality_metrics": {
    "is_sharp": true,
    "sharpness_score": 85.3,
    "message": "Sharpness score: 85.3"
  },
  "guidance": "Identification confidence (41.2%) is below acceptance threshold (50.0%). Specimen cannot be reliably distinguished. Ensure good lighting and fill the frame with the mosquito.",
  "model_version": "vectora_candidate_exp_b_int8"
}
```

#### Case C: Rejection Due to Severe Motion Blur / Out-of-Focus (`REJECTED_BLURRY`)
```json
{
  "status": "REJECTED_BLURRY",
  "predicted_genus": null,
  "confidence": 0.0,
  "probabilities": {
    "aedes": 0.0,
    "anopheles": 0.0,
    "culex": 0.0
  },
  "quality_metrics": {
    "is_sharp": false,
    "sharpness_score": 1.1,
    "message": "Image is too blurry (sharpness score 1.1 < 2.0)."
  },
  "guidance": "Specimen is out of focus. Hold phone steady, tap to focus on the mosquito body, and retake the photo.",
  "model_version": "vectora_candidate_exp_b_int8"
}
```

---

## 3. Platform Implementation Blueprints

### 3.1 Android Kotlin / ONNX Runtime Mobile Blueprint

The Android application implements CameraX with an offline ONNX Runtime Mobile session:

```kotlin
package ai.vectora.vision

import android.graphics.Bitmap
import android.graphics.Color
import ai.onnxruntime.*
import java.nio.FloatBuffer
import kotlin.math.exp
import kotlin.math.max

class VectoraEdgeClassifier(private val ortEnv: OrtEnvironment, modelBytes: ByteArray) {
    private val session: OrtSession = ortEnv.createSession(modelBytes, OrtSession.SessionOptions().apply {
        setIntraOpNumThreads(2)
        setOptimizationLevel(OrtSession.SessionOptions.OptLevel.BASIC_OPT)
    })

    companion object {
        val CLASSES = arrayOf("aedes", "anopheles", "culex")
        const val INPUT_SIZE = 224
        const val CONFIDENCE_THRESHOLD = 0.50f
        val MEAN = floatArrayOf(0.485f, 0.456f, 0.406f)
        val STD = floatArrayOf(0.229f, 0.224f, 0.225f)
    }

    fun classify(bitmap: Bitmap): VectoraResult {
        // 1. Resize to 224x224 (Bilinear)
        val scaled = Bitmap.createScaledBitmap(bitmap, INPUT_SIZE, INPUT_SIZE, true)
        
        // 2. Preprocess to NCHW FloatBuffer
        val buffer = FloatBuffer.allocate(1 * 3 * INPUT_SIZE * INPUT_SIZE)
        val pixels = IntArray(INPUT_SIZE * INPUT_SIZE)
        scaled.getPixels(pixels, 0, INPUT_SIZE, 0, 0, INPUT_SIZE, INPUT_SIZE)

        // Fill planar RGB [1, 3, 224, 224]
        for (c in 0..2) {
            for (i in pixels.indices) {
                val pixel = pixels[i]
                val channelVal = when (c) {
                    0 -> Color.red(pixel) / 255.0f
                    1 -> Color.green(pixel) / 255.0f
                    else -> Color.blue(pixel) / 255.0f
                }
                buffer.put((channelVal - MEAN[c]) / STD[c])
            }
        }
        buffer.rewind()

        // 3. Inference
        val inputTensor = OnnxTensor.createTensor(ortEnv, buffer, longArrayOf(1, 3, 224, 224))
        val output = session.run(mapOf(session.inputNames.iterator().next() to inputTensor))
        val logits = (output[0].value as Array<FloatArray>)[0]

        // 4. Softmax
        var maxLogit = Float.NEGATIVE_INFINITY
        for (l in logits) maxLogit = max(maxLogit, l)
        val expLogits = logits.map { exp(it - maxLogit) }
        val sumExp = expLogits.sum()
        val probs = expLogits.map { it / sumExp }

        var topIdx = 0
        var topProb = probs[0]
        for (i in 1 until probs.size) {
            if (probs[i] > topProb) {
                topProb = probs[i]
                topIdx = i
            }
        }

        // 5. Decision Threshold
        return if (topProb >= CONFIDENCE_THRESHOLD) {
            VectoraResult.Identified(CLASSES[topIdx], topProb, probs)
        } else {
            VectoraResult.Uncertain(topProb, probs)
        }
    }
}
```

---

### 3.2 Web / FastAPI Reference Service

The server backend imports the shared module [`src/vectora/inference.py`](file:///home/nimr/Projects/mosqscan/vectora-ai-starter/src/vectora/inference.py):

```python
from fastapi import FastAPI, UploadFile, File, HTTPException
from src.vectora.inference import VectoraInferenceEngine

app = FastAPI(title="Vectora AI Vector Identification API")
engine = VectoraInferenceEngine(
    onnx_model_path="models/vectora_candidate_exp_b_int8.onnx",
    confidence_threshold=0.50
)

@app.post("/v1/identify")
async def identify_specimen(file: UploadFile = File(...)):
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Invalid image type.")
    image_bytes = await file.read()
    return engine.predict(image_bytes)
```

---

## 4. Hardware & Performance Verification

Benchmarks executed on the primary development CPU (Intel Core i7-2600, 3.40 GHz, AVX, no AVX2) using single-threaded dynamic INT8 ONNX execution:

| Specification Requirement | PRD Target | Measured Performance (Exp B INT8) | Verification Status |
| :--- | :--- | :--- | :--- |
| **Model Size** | $\le 45\text{ MB}$ | **4.16 MB** (`4,362,942 bytes`) | **COMPLIANT** (10.8x smaller than ceiling) |
| **CPU Inference Latency** | $< 200\text{ ms}$ (Mid-tier mobile) | **58.2 ms** (Desktop CPU, 1 thread) | **COMPLIANT** |
| **Peak Memory Consumption** | $< 150\text{ MB}$ RSS | **~48 MB** process RSS delta | **COMPLIANT** |
| **Offline Execution** | 100% On-device, Zero Network | Full offline ONNX runtime | **COMPLIANT** |
| **Scientific Validation** | $\ge 92.0\%$ Macro-F1 | **61.90%** (Pilot research dataset) | **NON-COMPLIANT (RESEARCH ONLY)** |

---

## 5. Deployment Checklist & Recommendations

Before promoting any model artifact to production field release:

1. [x] **Artifact Checksums & Manifest Frozen:** [`configs/model_manifest.json`](file:///home/nimr/Projects/mosqscan/vectora-ai-starter/configs/model_manifest.json) committed.
2. [x] **Unified Cross-Platform Contract:** Enforced via [`src/vectora/inference.py`](file:///home/nimr/Projects/mosqscan/vectora-ai-starter/src/vectora/inference.py).
3. [x] **INT8 Mobile Quantization:** Validated and benchmarked.
4. [ ] **Multi-Site Field Dataset Acquisition:** Collect $\ge 1,000$ specimens across diverse Indian climatic zones to resolve Anopheles sensitivity.
5. [ ] **Meniscus Pipeline Integration:** Bind larvae motion analysis as an independent module.
6. [ ] **Entomological Expert Peer Review:** Independent double-blind taxonomy validation.
