# Vectora AI — Environment & Hardware Compatibility Report

**Date:** 2026-11-11  
**Auditor:** Senior ML / Systems Engineer (Antigravity)  
**Host Platform:** Desktop Workstation  

---

## 1. Operating System & Kernel Specifications

* **Operating System:** Omarchy Linux (Arch Linux rolling distribution)
* **OS Release:** `Omarchy 4.0.6 (x86_64)`
* **Linux Kernel:** `7.2.8-9-omarchy-x86_64`
* **C Library:** `glibc 2.44`
* **Architecture:** `x86_64` (64-bit little endian)

---

## 2. Processor & Hardware Capabilities

```text
Model name:            Intel(R) Core(TM) i7-2600 CPU @ 3.40GHz
Cores / Threads:       4 physical cores / 8 logical threads (1 socket)
Base Frequency:        3.40 GHz (Turbo up to 3.80 GHz)
L1 Data Cache:         32 KB per core (128 KB total)
L2 Cache:              256 KB per core (1 MB total)
L3 Cache:              8 MB shared
BogoMIPS:              6784.94
```

### CPU Instruction Flags Audit

```text
Flags: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 
clflush dts acpi mmx fxsr sse sse2 ht tm pbe syscall nx rdtscp lm constant_tsc 
arch_perfmon pebs bts rep_good nopl xtopology nonstop_tsc cpuid aperfmperf pni 
pclmulqdq dtes64 monitor ds_cpl vmx smx est tm2 ssse3 cx16 xtpr pdcm pcid 
sse4_1 sse4_2 x2apic popcnt tsc_deadline_timer aes xsave avx lahf_lm epb pti 
ssbd ibrs ibpb stibp tpr_shadow flexpriority ept vpid xsaveopt dtherm ida arat 
pln pts vnmi md_clear flush_l1d
```

### Critical Hardware Constraint: AVX vs AVX2
* **AVX (Advanced Vector Extensions):** Supported (`avx: True`).
* **AVX2 (Advanced Vector Extensions 2):** **NOT Supported** (`avx2: False`).
* **AVX-512:** **NOT Supported**.
* **GPU Acceleration:** No NVIDIA discrete GPU detected. CUDA is unavailable (`torch.cuda.is_available() == False`).

> [!IMPORTANT]
> Because the Intel Core i7-2600 (Sandy Bridge generation) supports AVX but lacks AVX2, high-performance CPU neural network libraries like NNPACK emit hardware warnings:
> `[NNPACK.cpp:56] Could not initialize NNPACK! Reason: Unsupported hardware.`
> However, PyTorch and ONNX Runtime automatically fall back to standard AVX/SSE optimized kernels and execute reliably without crashing or memory corruption.

---

## 3. Memory & Resource Profile

```text
Total System RAM:     15.0 GiB (16,043,904 KB)
Used Memory:          ~9.8 GiB (baseline desktop + browser)
Available Memory:     ~5.7 GiB
Configured Swap:      38.0 GiB (4.8 GiB used, 34 GiB free)
```

### Recommended Resource Policy for i7-2600
* **PyTorch CPU Threads:** Set `torch.set_num_threads(3)` and `OMP_NUM_THREADS=3` (leaves 1 physical core for OS/background processes).
* **DataLoader Workers:** `num_workers=0` or `num_workers=2` (avoids multi-process RAM ballooning on 48 MP images).
* **Batch Size:** 8 for 224x224 classification models.

---

## 4. Python Environment & Library Matrix

* **Python Version:** `3.12.15` (managed via `mise` at `/home/nimr/.local/share/mise/installs/python/3.12.15`)
* **Virtual Environment Path:** `/home/nimr/Projects/mosqscan/vectora-ai-starter/.venv`
* **Pip Version:** `26.3`

### Installed Packages & Versions

| Package | Version | Compatibility Status on i7-2600 | Role |
|---|---|---|---|
| `torch` | `2.15.0+cpu` | **Verified PASS** | Deep learning framework (CPU build) |
| `torchvision` | `0.29.2+cpu` | **Verified PASS** | Pretrained backbones & image transformations |
| `onnx` | `1.23.2` | **Verified PASS** | Open Neural Network Exchange standard |
| `onnxruntime` | `1.31.1` | **Verified PASS** | CPU execution provider (`CPUExecutionProvider`) |
| `opencv-python-headless`| `5.0.0.93` | **Verified PASS** | Computer vision & image preprocessing |
| `numpy` | `2.5.4` | **Verified PASS** | High-performance numerical arrays |
| `pandas` | `2.3.3` | **Verified PASS** | Metadata & dataset manifest management |
| `scikit-learn` | `1.9.1` | **Verified PASS** | Evaluation metrics (F1, precision, recall, confusion matrix) |
| `Pillow` | `12.3.0` | **Verified PASS** | Image decoding and resizing |
| `matplotlib` | `3.11.2` | **Verified PASS** | Visualization and report plotting |
| `tqdm` | `4.70.1` | **Verified PASS** | Progress display |
| `PyYAML` | `6.0.3` | **Verified PASS** | YAML configuration parsing |

---

## 5. Compatibility & Execution Smoke Tests

| Test Case | Command Executed | Result | Notes |
|---|---|---|---|
| **CPU Instruction Flags** | `lscpu \| grep -E 'Model name\|Flags'` | **PASS** | Confirmed AVX, no AVX2 |
| **PyTorch CPU Tensor** | `python scripts/check_env.py` | **PASS** | 2x3x224x224 tensor mean test passed (3 threads) |
| **EfficientNet-B0 Forward Pass**| `tests/test_ml_pipeline.py` | **PASS** | Logits generated with shape `(2, 3)` |
| **OpenCV Image Decode & Resize**| `cv2.imread() + cv2.resize()` | **PASS** | Successfully decoded 4000x3000 image to 224x224 |
| **ONNX Model Export** | `torch.onnx.export(..., dynamo=False)`| **PASS** | 15.29 MB FP32 ONNX model generated |
| **ONNX INT8 Quantization** | `onnxruntime.quantization.quantize_dynamic` | **PASS** | 4.16 MB INT8 ONNX model generated |
| **ONNX Runtime Inference** | `ort.InferenceSession.run()` | **PASS** | FP32 latency: **14.21 ms**, INT8 latency: **58.79 ms** |
