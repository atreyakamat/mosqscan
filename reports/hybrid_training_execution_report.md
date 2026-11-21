# Vectora AI — Hybrid Model Training Execution and Benchmark Report

**Target Platform:** Intel Core i7-2600 @ 3.40GHz (Sandy Bridge, 4 cores / 8 threads, AVX, 16 GB DDR3 RAM)  
**Host Operating System:** Omarchy Linux (Kernel 6.x, x86_64)  
**Deliverable:** Mode B Hybrid Training Benchmark and Hardware Coexistence Report  
**Compliance Standard:** ASD-STE100 Simplified Technical English  
**Date:** 2026-11-13  
**Status:** Executed & Verified  

---

## 1. Executive Summary

This report documents the execution of Mode B hybrid model training (`scripts/run_hybrid_training.sh`) on the development host while concurrently serving production inference.
Antigravity evaluated the hybrid mosquito classifier combining 44 physical original photographs and 2,245 verified precomputed augmentations.
All 215 unconfirmed augmentations and 180 ambiguous sibling-discordant augmentations were strictly excluded.

### Benchmark Highlights:
1. **Production Server Availability:**
   - Active production FastAPI ONNX inference maintained **$100\%$ availability** throughout the 28.5-minute training run.
   - Total background health checks: **336 requests** with **zero dropped requests** and **zero timeouts**.
   - Median server latency during training was **89.00 ms** (P95: **114.00 ms**).
2. **CPU & Memory Ceilings:**
   - PyTorch CPU execution threads were strictly capped at **3 threads**, leaving 5 threads for host OS and container workloads.
   - Peak process memory reached **3,130.4 MB** ($19.7\%$ of host RAM).
   - Stopping Ollama before training immediately freed **3.65 GiB of RAM**, increasing available host memory to **6.95 GB** before training began.
3. **Out-of-Fold Generalization:**
   - **Primary Unweighted Model:** Pooled Macro-F1 = **$0.7611$**, Accuracy = **$79.55\%$** ($35/44$), Anopheles Recall = **$77.78\%$** ($7/9$).
   - **Ablation Class-Weighted Model:** Pooled Macro-F1 = **$0.7432$**, Accuracy = **$77.27\%$** ($34/44$), Anopheles Recall = **$88.89\%$** ($8/9$).
4. **Active Model Immutability:**
   - Active production model [`models/vectora_v3_fp32.onnx`](file:///home/nimr/Projects/mosqscan/models/vectora_v3_fp32.onnx) was verified before and after training.
   - SHA-256 checksum remained identical: `c3a3656f746a1bb2e7ac428e44670d89cf51f0d0f923ad3aa15420e8a4592cfa`.

---

## 2. Training Execution and Computational Throughput

Table 1 records the execution timing and throughput across all cross-validation folds.

### Table 1: Training Execution and Throughput Matrix

| Phase / Fold | Epochs | Training Images | Duration (s) | Image Throughput | Peak Process RAM | Checkpoint Hash (SHA-256) |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Primary Fold 1** | 1 Head + 1 Fine | 1,684 | 219.0 s | 15.4 img/s | 3,098 MB | `9559bb29c0a6b73ebf0367eb7826359bebe3ba03cb117ea7ea79815c48b26c2e` |
| **Primary Fold 2** | 1 Head + 1 Fine | 1,732 | 199.5 s | 17.4 img/s | 3,115 MB | `0e9cb20387b32810fb5cfc66c30f40df8374d6c41b8c0d1e1fa63bc64b971c26` |
| **Primary Fold 3** | 1 Head + 1 Fine | 1,741 | 194.3 s | 17.9 img/s | 3,124 MB | `b9f5647565985ae08ef61cb56bb76d75508b534d0263f350cbe43b4685ff8614` |
| **Primary Fold 4** | 1 Head + 1 Fine | 1,710 | 192.2 s | 17.8 img/s | 3,128 MB | `d0fbc705a61fc08c7908b8b082ae0d65a88c3a1e2850901e687e14dbe10ec7ce` |
| **Ablation Fold 1**| 1 Head + 1 Fine | 1,684 | 194.3 s | 17.3 img/s | 3,128 MB | `532e013a778c13b28b7470f5e1a3bcda4ecf90117fc040715aa31fe829672eb1` |
| **Ablation Fold 2**| 1 Head + 1 Fine | 1,732 | 254.1 s | 13.6 img/s | 3,130 MB | `99d9b626f228b3234d7fb37caeb591a134a6ca024b4249a4f6d482cf187ea131` |
| **Ablation Fold 3**| 1 Head + 1 Fine | 1,741 | 232.2 s | 15.0 img/s | 3,130 MB | `e24391ea114feebfd67c9c0b1ef380b263e7c85aa882c42b5839257e8aa6878b` |
| **Ablation Fold 4**| 1 Head + 1 Fine | 1,710 | 206.1 s | 16.6 img/s | 3,130 MB | `d95856755490ff4908920199e69315dff722fe1fa8a7c29759e0a0ee449bc2b8` |

- **Primary Run Total Time:** 805.3 s (13.4 minutes)
- **Ablation Run Total Time:** 887.0 s (14.8 minutes)
- **Total Training Duration:** 1,712 seconds (28.5 minutes)

---

## 3. Production API Latency and Coexistence Benchmark

Table 2 compares host API health before, during, and after the hybrid training run.

### Table 2: Production API Latency Across Training Phases

| Latency Metric | Baseline (Pre-Training) | Concurrent (During Training) | Post-Training (Recovery) |
| :--- | :---: | :---: | :---: |
| **Sample Count** | 20 requests | **336 requests** (5s intervals) | 20 requests |
| **Failed Requests** | 0 ($0.0\%$) | **0 ($0.0\%$)** | 0 ($0.0\%$) |
| **Uptime Status** | $100\%$ Healthy | **$100\%$ Healthy** | $100\%$ Healthy |
| **Median Latency** | **65.93 ms** | **89.00 ms** | **63.19 ms** |
| **Mean Latency** | **70.94 ms** | **91.83 ms** | **66.99 ms** |
| **95th Percentile (P95)** | **104.34 ms** | **114.00 ms** | **85.09 ms** |
| **Minimum Latency** | 59.13 ms | 68.00 ms | 59.14 ms |
| **Maximum Spike** | 104.34 ms | 222.00 ms | 85.09 ms |

```
Production API Latency Distribution During Peak CPU Training:
[  0 -  75 ms ]  #################### (38%)
[ 76 - 100 ms ]  ############################## (47%)
[101 - 125 ms ]  ######## (12%)
[126 - 150 ms ]  # (2%)
[   > 150 ms  ]  # (1%)
Total Valid Samples: 336 / 336 (0 Failures)
```

---

## 4. Hardware Safety and Resource Profiling

1. **CPU Allocation Safety:**
   The training process utilized an average of $260\%$ to $285\%$ CPU (out of $800\%$ available across 8 threads). The CPU limit of 3 threads prevented host process starvation and allowed the FastAPI backend and Next.js frontend to remain fully responsive.
2. **RAM Stability:**
   The RAM preloading strategy cached all 2,289 PIL RGB images in memory within 11.3 seconds, using approximately 1.8 GB. Total resident memory peaked at 3,130.4 MB, leaving over 4 GB of free RAM for host OS buffers and Redis/PostgreSQL containers.
3. **Storage and File System Integrity:**
   All candidate checkpoints were written exclusively to [`models/research/`](file:///home/nimr/Projects/mosqscan/models/research). No production paths were touched.

---

## 5. Verification Checklist

- [x] All 5 original Docker containers remained healthy throughout training.
- [x] Ollama stopped cleanly before training and freed 3.65 GiB of RAM.
- [x] PyTorch CPU threads strictly capped at 3.
- [x] In-memory image cache eliminated disk I/O bottlenecks.
- [x] Production API health checks succeeded with 0 failures across 336 requests.
- [x] All 8 fold checkpoints and predictions preserved in `models/research/` and `reports/research/`.
- [x] SHA-256 of `models/vectora_v3_fp32.onnx` remained strictly unmodified (`c3a3656f746a1bb2e7ac428e44670d89cf51f0d0f923ad3aa15420e8a4592cfa`).
- [x] No candidate models were promoted to production.
