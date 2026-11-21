#!/usr/bin/env python3
"""
Controlled Performance Benchmarking on Intel Core i7-2600.
ASD-STE100 Compliant Implementation.
"""
from __future__ import annotations

import json
import os
import resource
import time
import numpy as np
import torch
import torch.nn as nn
from torchvision.models import efficientnet_b0
import onnxruntime as ort

def get_peak_ram_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0

def benchmark_onnx(model_path: str, threads: int, warmup: int = 10, runs: int = 100):
    so = ort.SessionOptions()
    so.intra_op_num_threads = threads
    so.inter_op_num_threads = 1
    so.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    
    session = ort.InferenceSession(model_path, so, providers=["CPUExecutionProvider"])
    dummy = np.random.randn(1, 3, 224, 224).astype(np.float32)
    
    # Warmup
    for _ in range(warmup):
        _ = session.run(None, {"input": dummy})
        
    latencies = []
    for _ in range(runs):
        t0 = time.perf_counter()
        _ = session.run(None, {"input": dummy})
        latencies.append((time.perf_counter() - t0) * 1000.0)
        
    return {
        "threads": threads,
        "warmup_runs": warmup,
        "benchmark_runs": runs,
        "median_ms": round(float(np.median(latencies)), 2),
        "mean_ms": round(float(np.mean(latencies)), 2),
        "p95_ms": round(float(np.percentile(latencies, 95)), 2),
        "min_ms": round(float(np.min(latencies)), 2),
        "max_ms": round(float(np.max(latencies)), 2),
        "std_ms": round(float(np.std(latencies)), 2),
        "peak_ram_mb": round(get_peak_ram_mb(), 2),
    }

def benchmark_pytorch(weights_path: str, threads: int, warmup: int = 10, runs: int = 100):
    torch.set_num_threads(threads)
    model = efficientnet_b0()
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, 3)
    model.load_state_dict(torch.load(weights_path, weights_only=True))
    model.eval()
    
    dummy = torch.randn(1, 3, 224, 224)
    with torch.no_grad():
        for _ in range(warmup):
            _ = model(dummy)
            
        latencies = []
        for _ in range(runs):
            t0 = time.perf_counter()
            _ = model(dummy)
            latencies.append((time.perf_counter() - t0) * 1000.0)
            
    return {
        "runtime": "PyTorch (Python Interpreter)",
        "threads": threads,
        "median_ms": round(float(np.median(latencies)), 2),
        "p95_ms": round(float(np.percentile(latencies, 95)), 2),
        "min_ms": round(float(np.min(latencies)), 2),
        "max_ms": round(float(np.max(latencies)), 2),
    }

def main():
    print("=" * 70)
    print("VECTORA AI 3.0: CONTROLLED PERFORMANCE BENCHMARK (i7-2600 CPU)")
    print("=" * 70)
    
    onnx_path = "models/vectora_v3_fp32.onnx"
    pt_path = "models/v3/vectora_v3_best.pt"
    
    results = {}
    
    for t in [1, 2, 4]:
        res = benchmark_onnx(onnx_path, threads=t, warmup=10, runs=100)
        results[f"onnx_threads_{t}"] = res
        print(f"ONNX Runtime (Threads={t}): Median={res['median_ms']}ms, p95={res['p95_ms']}ms, Min={res['min_ms']}ms, Max={res['max_ms']}ms, RAM={res['peak_ram_mb']}MB")
        
    py_res = benchmark_pytorch(pt_path, threads=4, warmup=10, runs=50)
    results["pytorch_python"] = py_res
    print(f"\nPyTorch Python nn.Module (Threads=4): Median={py_res['median_ms']}ms, p95={py_res['p95_ms']}ms, Min={py_res['min_ms']}ms, Max={py_res['max_ms']}ms")
    
    diff_ratio = py_res["median_ms"] / results["onnx_threads_4"]["median_ms"]
    print(f"\nOptimization Factor (ONNX vs PyTorch): ONNX is {round(diff_ratio, 2)}x faster")
    
    with open("reports/v3_performance_benchmark.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nSaved benchmark results to reports/v3_performance_benchmark.json")

if __name__ == "__main__":
    main()
