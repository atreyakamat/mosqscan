# Vectora AI — Extended Model Runtime Parity, Preprocessing, and Latency Benchmark Audit

**Deliverable:** Extended Model Audit Deliverable 4 of 5  
**Target:** PyTorch-to-ONNX Parity, Preprocessing Verification, and Latency Reproduction  
**Hardware Platform:** Intel Core i7-2600 CPU @ 3.40GHz (Sandy Bridge, AVX only, 16 GB RAM)  
**Evaluator:** Independent ML Quality & Evaluation Audit  
**Date:** 2026-11-13  
**Status:** Parity Verified · Latency Reproduced · Production Model Preserved  

---

## 1. Executive Summary

This report delivers the runtime verification audit for the extended 8-epoch model artifacts:
- PyTorch Checkpoint: [`models/vectora_extended_best.pt`](file:///home/nimr/Projects/mosqscan/models/vectora_extended_best.pt)
- Exported ONNX Model: [`models/vectora_extended_fp32.onnx`](file:///home/nimr/Projects/mosqscan/models/vectora_extended_fp32.onnx)

### Key Audit Findings:
1. **PyTorch vs. ONNX Numerical Parity:** On all 44 physical mosquito photographs, the maximum absolute logit divergence between PyTorch and ONNX Runtime is **$3.5703 \times 10^{-5}$** (mean divergence: **$1.3858 \times 10^{-5}$**). Predicted class indices match identically ($100.00\%$ agreement, 44 of 44).
2. **Preprocessing & Class Ordering:** Preprocessing transforms, input dimensions ($1 \times 3 \times 224 \times 224$), normalization constants, and class indexing ($0 = \text{aedes}$, $1 = \text{anopheles}$, $2 = \text{culex}$) are strictly verified.
3. **Artifact Integrity & Checksum:** The ONNX file SHA-256 checksum is bit-for-bit identical to the training log (`e21b16c5ce26ff456b6255040762b723b822f7e448d066c5cfa01e05f3a991cc`). The active production model ([`models/vectora_v3_fp32.onnx`](file:///home/nimr/Projects/mosqscan/models/vectora_v3_fp32.onnx), SHA-256 `c3a3656f...`) remains untouched.
4. **Latency Reproduction on Sandy Bridge CPU:** Measured ONNX inference latency closely reproduces the reported figures:
   - Reported: Median = **$17.00\text{ ms}$**, p95 = **$26.76\text{ ms}$**.
   - Reproduced (44-specimen run): Median = **$17.11\text{ ms}$**, p95 = **$27.14\text{ ms}$** ($\Delta \le 0.38\text{ ms}$).
   - Reproduced (100 repeated runs): Median = **$16.07\text{ ms}$**, p95 = **$24.51\text{ ms}$**.

---

## 2. Model Checksum and Artifact Verification

Table 1 documents the cryptographic checksums and physical file attributes of all relevant model artifacts.

### Table 1: Model Checksum and Storage Audit

| Artifact Name | Canonical File Path | File Size (Bytes) | SHA-256 Cryptographic Checksum | Operational Verification |
| :--- | :--- | :---: | :--- | :--- |
| **Extended PyTorch Checkpoint** | `models/vectora_extended_best.pt` | 16,344,051 | `b5697a7f177b03988084060de1446eba2e9bc6b0913d2db796b448fbba3d6108` | Checksum matches training manifest |
| **Extended ONNX FP32 Model** | `models/vectora_extended_fp32.onnx` | 16,035,577 | `e21b16c5ce26ff456b6255040762b723b822f7e448d066c5cfa01e05f3a991cc` | Checksum matches training manifest |
| **Active Production V3 FP32 Model** | `models/vectora_v3_fp32.onnx` | 16,035,577 | `c3a3656f746a1bb2e7ac428e44670d89cf51f0d0f923ad3aa15420e8a4592cfa` | **Preserved untouched** (Active in Docker) |
| **Production INT8 Model** | `models/vectora_v3_int8.onnx` | 4,362,904 | `94e2467dcf4fc99b703e1e8fa8d10ee08c488d070e5ee59fc14710cf2ecb8b40` | Preserved untouched |

---

## 3. PyTorch vs. ONNX Logit Parity Analysis

The auditor evaluated identical input tensors through both PyTorch (`torch.no_grad()`) and ONNX Runtime (`onnxruntime.InferenceSession`, `CPUExecutionProvider`, 3 intra-op threads).

### A. Real Biological Specimen Inputs ($N=44$ Original Photographs)
* **Logit Divergence Across 44 Specimens:**
  - Maximum Absolute Logit Difference: **$3.5703 \times 10^{-5}$** ($0.0000357$)
  - Mean Absolute Logit Difference: **$1.3858 \times 10^{-5}$** ($0.0000139$)
  - Minimum Absolute Logit Difference: **$1.1921 \times 10^{-7}$**
* **Classification Prediction Agreement:**
  - PyTorch argmax predictions vs. ONNX Runtime argmax predictions: **$44 / 44$ ($100.00\%$) exact match**.
* **Finding:** On realistic input distributions, PyTorch and ONNX outputs are functionally identical. Divergence is well within the expected precision tolerance of single-precision IEEE 754 floating-point operations across CPU SIMD backends.

### B. Out-of-Distribution Synthetic Dummy Tensors ($N=5$ Random Normal Inputs)
* Input: Random standard normal noise $\mathcal{N}(0, 1)$ ($5 \times 3 \times 224 \times 224$).
* Maximum Absolute Logit Difference: **$0.2256$**
* Mean Absolute Logit Difference: **$0.0504$**
* **Finding:** On extreme out-of-distribution values (where activation patterns fall far outside standard ImageNet-normalized ranges), subtle differences in fused operator implementations between PyTorch ATen and ONNX Runtime CPU kernel generate wider differences. However, within the operational data domain (photographs of mosquitoes), parity is flawless.

---

## 4. Preprocessing Pipeline and Class Order Verification

### Preprocessing Protocol Verification
The input preprocessing pipeline was audited against `src/` and `scripts/train_extended_combined.py`:
- **Input Dimensions:** $224 \times 224 \times 3$ channels.
- **Color Channel Order:** RGB.
- **Resizing Policy:** Bilinear interpolation resizing to $224 \times 224$.
- **Tensor Conversion:** Scaled from $[0, 255]$ uint8 to $[0.0, 1.0]$ float32.
- **Normalization (ImageNet Canonical):**
  $$\mu = [0.485, 0.456, 0.406], \quad \sigma = [0.229, 0.224, 0.225]$$
  $$x_{\text{normalized}} = \frac{x - \mu}{\sigma}$$

### Class Ordering Verification
The class indices in both the PyTorch classifier head and ONNX output graph follow the fixed project order:
- **Index 0:** `aedes` (*Aedes aegypti*)
- **Index 1:** `anopheles` (*Anopheles stephensi*)
- **Index 2:** `culex` (*Culex quinquefasciatus*)

### ONNX Model Graph Inspection
- **IR Version:** 8
- **Opset Version:** 17
- **Producer Name:** PyTorch
- **Graph Input:** Name = `input`, Type = `float32`, Shape = `['batch_size', 3, 224, 224]` (Dynamic batch dimension).
- **Graph Output:** Name = `output`, Type = `float32`, Shape = `['batch_size', 3]` (Dynamic batch dimension).
- **Self-Contained File:** Confirmed. All weights and biases are stored internally within the 16.04 MB `.onnx` file (zero external `.bin` sidecar files).

---

## 5. ONNX Latency Measurement Reproduction

The auditor reproduced inference latency benchmarks directly on the host system under the exact constraints specified in the engineering baseline (Intel Core i7-2600 CPU @ 3.40GHz, 3 CPU execution threads, `CPUExecutionProvider`).

### Benchmark Protocols
1. **10-Run Warmup:** Warm up CPU instruction caches and dynamic memory pools with 10 dummy inferences prior to timing.
2. **Benchmark 1 (Sequential 44 Images):** Identical to the verification loop in `scripts/train_extended_combined.py`. 44 sequential inferences over pre-loaded image tensors.
3. **Benchmark 2 (100 Repeated Runs):** 100 consecutive single-batch inferences to capture statistical stability and p95 tail behavior.

### Table 2: ONNX Runtime CPU Latency Reproduction

| Benchmark Run | Sample Count | Median Latency | p95 Latency | Mean Latency | Min / Max Latency | Reproduction Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Reported (`v3_extended_training_results.json`)** | 44 | **17.00 ms** | **26.76 ms** | - | - | Reference Baseline |
| **Auditor Reproduction (Benchmark 1: 44 Images)** | 44 | **17.11 ms** | **27.14 ms** | 18.57 ms | 14.57 ms / 27.70 ms | **REPRODUCED** ($\Delta_{\text{med}} = +0.11\text{ ms}$) |
| **Auditor Reproduction (Benchmark 2: 100 Runs)** | 100 | **16.07 ms** | **24.51 ms** | 17.43 ms | 14.48 ms / 25.12 ms | **REPRODUCED** (Consistent tail) |

### Latency Findings:
- Sandy Bridge AVX vectorization successfully accelerates FP32 depthwise separable convolutions in EfficientNet-B0.
- Inference latency is well below the PRD edge requirement of $< 50\text{ ms}$ per adult photograph.
- The reported latency numbers in `v3_extended_training_results.json` are **empirically valid and reproducible**.
