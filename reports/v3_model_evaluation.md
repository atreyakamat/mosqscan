# Vectora AI 3.0 — Model Numerical Evaluation and Quantization Audit

**Date:** 2026-11-12  
**Platform:** Intel Core i7-2600 Workstation (16 GB RAM)  
**Standard:** ASD-STE100  
**Status:** Complete  

---

## 1. Executive Summary

This report documents the numerical evaluation, precision drift analysis, and latency benchmarking of the winning EfficientNet-B0 model (`vectora_v3_fp32.onnx`) and its dynamically quantized 8-bit counterpart (`vectora_v3_int8.onnx`).

Both models were evaluated across all 44 original photographic mosquito specimens (`data/staging/original/Original Images Mendeley/`) under deterministic preprocessing (224x224 RGB, ImageNet normalization).

The evaluation demonstrates that:
1. The FP32 ONNX model delivers low median inference latency of **23.40 ms** on the host Intel Core i7-2600 CPU.
2. Dynamic INT8 quantization reduces disk footprint by **3.68x** (from 15.29 MB to 4.16 MB), but introduces significant numerical probability drift on CPU (mean drift: 0.3483, maximum drift: 0.6333), altering the top-1 predicted genus in 32 of 44 specimens (72.73% disagreement).
3. Furthermore, on x86 Sandy Bridge architecture lacking AVX-512 VNNI, INT8 emulation is **7.59x slower** than FP32 (177.55 ms vs 23.40 ms).
4. **Architectural Recommendation:** Deploy the FP32 ONNX model (`vectora_v3_fp32.onnx`) on the central inference workstation.

---

## 2. Model Artifact Lineage and Cryptographic Hashes

| Artifact Property | Full Precision (FP32) | Dynamically Quantized (INT8) |
| :--- | :--- | :--- |
| **Model Filename** | `vectora_v3_fp32.onnx` | `vectora_v3_int8.onnx` |
| **Storage Directory** | `models/` and `models/v3/` | `models/` and `models/v3/` |
| **File Size (Bytes)** | 16,035,577 bytes | 4,362,904 bytes |
| **File Size (MB)** | 15.29 MB | 4.16 MB |
| **Compression Ratio** | 1.00x (Baseline) | **3.68x** |
| **SHA-256 Checksum** | `c3a3656f746a1bb2e7ac428e44670d89cf51f0d0f923ad3aa15420e8a4592cfa` | `f65cf4373b00bf8df812aedd039489107721c51112932956d7d98351b286ba4e` |
| **ONNX Opset Version** | Opset 17 | Opset 17 |
| **Quantization Format**| IEEE 754 32-bit Float | Dynamic Asymmetric QInt8 (`QuantType.QInt8`) |
| **Target Deployment** | Central Server (FastAPI / CPU) | Mobile Edge Client (Offline Android) |

---

## 3. Host Workstation CPU Latency Benchmarking

Inference benchmarks were conducted on the host Intel Core i7-2600 CPU using ONNX Runtime with `CPUExecutionProvider` configured for 4 execution threads:

| Benchmark Metric | FP32 ONNX (`vectora_v3_fp32.onnx`) | INT8 ONNX (`vectora_v3_int8.onnx`) | Relative Variance |
| :--- | :--- | :--- | :--- |
| **Median Latency** | **23.40 ms** | 177.55 ms | FP32 is **7.59x faster** |
| **95th Percentile (p95)**| **47.12 ms** | 228.39 ms | FP32 is **4.85x faster** |
| **Min Latency** | **18.65 ms** | 154.20 ms | — |
| **Max Latency** | **58.32 ms** | 245.10 ms | — |

### Why INT8 is Slower on Intel Sandy Bridge
The host CPU is an Intel Core i7-2600 (Sandy Bridge architecture, 2011). Sandy Bridge supports AVX (256-bit floating-point SIMD), but lacks:
- **AVX2:** 256-bit integer vector extensions.
- **AVX-512 VNNI / DL Boost:** Vector Neural Network Instructions for 8-bit dot products.

Because native hardware integer matrix multipliers are absent, ONNX Runtime executes INT8 kernels via software unpacking and dequantization, adding significant per-layer overhead. In contrast, FP32 utilizes Sandy Bridge's high-throughput AVX floating-point fused multiply-accumulate units directly.

---

## 4. Precision and Probability Drift Analysis

To assess the impact of 8-bit dynamic quantization on model outputs, softmax probability distributions were compared across all 44 original photographic biological specimens.

### 4.1 Summary Statistics

$$\Delta p_i = \max_{c \in \{\text{aedes, anopheles, culex}\}} |p_c^{\text{FP32}}(i) - p_c^{\text{INT8}}(i)|$$

| Drift Metric | Quantitative Value |
| :--- | :--- |
| **Total Specimens Evaluated** | 44 original photographs |
| **Mean Absolute Probability Drift ($\mu_{\Delta p}$)** | **0.3483 (34.83%)** |
| **Maximum Probability Drift ($\max \Delta p$)** | **0.6333 (63.33%)** |
| **Top-1 Genus Agreement Count** | 12 / 44 specimens (27.27%) |
| **Top-1 Genus Disagreement Count** | **32 / 44 specimens (72.73%)** |
| **Model Verification Status** | `EXPERIMENTAL_NOT_FIELD_VALIDATED` |

### 4.2 Representative Specimen Drift Examples

| Specimen ID | True Genus | FP32 Prediction (Probabilities) | INT8 Prediction (Probabilities) | Max Drift ($\Delta p$) | Agreement |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Aedes_aegypti_1.jpg` | *Aedes* | *Aedes* (Ae: 0.441, An: 0.406, Cx: 0.153) | *Aedes* (Ae: 0.418, An: 0.316, Cx: 0.266) | 0.1131 | Match |
| `Aedes_aegypti_10.jpg` | *Aedes* | *Aedes* (Ae: 0.495, An: 0.469, Cx: 0.036) | *Aedes* (Ae: 0.398, An: 0.325, Cx: 0.277) | 0.2418 | Match |
| `Anopheles_stephensi_1.jpg`| *Anopheles* | *Anopheles* (Ae: 0.301, An: 0.512, Cx: 0.187) | *Aedes* (Ae: 0.384, An: 0.332, Cx: 0.284) | 0.1800 | Disagreement |
| `Culex_quinquefasciatus_1.jpg`| *Culex* | *Culex* (Ae: 0.124, An: 0.210, Cx: 0.666) | *Aedes* (Ae: 0.362, An: 0.325, Cx: 0.313) | 0.3530 | Disagreement |

Detailed specimen logs are stored in `reports/v3_onnx_comparison.json`.

---

## 5. Architectural and Operational Conclusions

1. **Server Deployment Mandate:**
   The central inference server must deploy `vectora_v3_fp32.onnx`. FP32 provides deterministic 23.40 ms response times and preserves uncalibrated logits without quantization distortion.
2. **Field Client Delegation:**
   Because dynamic INT8 alters predicted genera on uncalibrated weights, mobile clients should delegate inference to the central workstation server via HTTPS authenticated requests whenever connectivity exists.
3. **Safety Disclaimer:**
   Neither the FP32 nor the INT8 scores are calibrated probabilities. The output represents raw softmax activation. The operational flag must remain:
   `status: "EXPERIMENTAL_NOT_FIELD_VALIDATED"`.
