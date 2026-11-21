#!/usr/bin/env python3
"""
Vectora AI 3.0: ONNX FP32 Export, INT8 Dynamic Quantization,
and Numerical Comparison on All 44 Original Biological Specimens.
ASD-STE100 Compliant Implementation.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from typing import Dict, List, Any

import numpy as np
import pandas as pd
from PIL import Image
import torch
import torch.nn as nn
from torchvision import transforms
from torchvision.models import efficientnet_b0
import onnx
import onnxruntime as ort
from onnxruntime.quantization import quantize_dynamic, QuantType

PROJECT_ROOT = "/home/nimr/Projects/mosqscan"
METADATA_DIR = os.path.join(PROJECT_ROOT, "data/metadata")
MODELS_DIR = os.path.join(PROJECT_ROOT, "models/v3")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")

CLASSES = ["aedes", "anopheles", "culex"]
CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}
IDX_TO_CLASS = {i: c for i, c in enumerate(CLASSES)}

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def main():
    print("=" * 70)
    print("VECTORA AI 3.0: ONNX EXPORT AND NUMERICAL COMPARISON")
    print("=" * 70)
    
    pt_path = os.path.join(MODELS_DIR, "vectora_v3_best.pt")
    if not os.path.exists(pt_path):
        raise FileNotFoundError(f"Missing weights: {pt_path}")
        
    # 1. Load Trained Model
    model = efficientnet_b0()
    in_feat = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_feat, 3)
    model.load_state_dict(torch.load(pt_path, weights_only=True))
    model.eval()
    print(f"Loaded trained PyTorch weights from: {pt_path}")
    
    # 2. Export FP32 ONNX
    fp32_onnx_path = os.path.join(MODELS_DIR, "vectora_v3_fp32.onnx")
    dummy_input = torch.randn(1, 3, 224, 224)
    torch.onnx.export(
        model,
        dummy_input,
        fp32_onnx_path,
        export_params=True,
        opset_version=17,
        do_constant_folding=True,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={"input": {0: "batch_size"}, "output": {0: "batch_size"}},
        dynamo=False,
    )
    onnx_m = onnx.load(fp32_onnx_path)
    onnx.checker.check_model(onnx_m)
    fp32_hash = sha256_file(fp32_onnx_path)
    fp32_size = os.path.getsize(fp32_onnx_path)
    print(f"FP32 ONNX Exported: {fp32_onnx_path}")
    print(f"  Size: {fp32_size} bytes ({round(fp32_size / (1024*1024), 2)} MB)")
    print(f"  SHA-256: {fp32_hash}")
    
    # 3. Dynamic INT8 Quantization
    int8_onnx_path = os.path.join(MODELS_DIR, "vectora_v3_int8.onnx")
    quantize_dynamic(
        model_input=fp32_onnx_path,
        model_output=int8_onnx_path,
        weight_type=QuantType.QInt8,
    )
    int8_m = onnx.load(int8_onnx_path)
    onnx.checker.check_model(int8_m)
    int8_hash = sha256_file(int8_onnx_path)
    int8_size = os.path.getsize(int8_onnx_path)
    print(f"INT8 ONNX Quantized: {int8_onnx_path}")
    print(f"  Size: {int8_size} bytes ({round(int8_size / (1024*1024), 2)} MB)")
    print(f"  Compression Ratio: {round(fp32_size / int8_size, 2)}x")
    print(f"  SHA-256: {int8_hash}")
    
    # 4. Load ONNX Runtime Sessions
    so = ort.SessionOptions()
    so.intra_op_num_threads = 4
    so.inter_op_num_threads = 1
    session_fp32 = ort.InferenceSession(fp32_onnx_path, so, providers=["CPUExecutionProvider"])
    session_int8 = ort.InferenceSession(int8_onnx_path, so, providers=["CPUExecutionProvider"])
    
    # 5. Numerical Evaluation on All 44 Original Specimens
    manifest_df = pd.read_json(os.path.join(METADATA_DIR, "dataset_manifest.json"))
    orig_df = manifest_df[manifest_df["dataset_type"] == "original"].copy()
    
    val_trans = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
    ])
    
    detailed_results = []
    prob_diffs = []
    disagreements = 0
    fp32_latencies, int8_latencies = [], []
    
    print("\nRunning inference on 44 original biological specimens...")
    for _, row in orig_df.iterrows():
        img_path = row["file_path"]
        with Image.open(img_path) as im:
            t_img = val_trans(im.convert("RGB")).unsqueeze(0).numpy()
            
        # FP32 inference
        t0 = time.perf_counter()
        out_fp32 = session_fp32.run(None, {"input": t_img})[0]
        fp32_latencies.append((time.perf_counter() - t0) * 1000.0)
        exp_fp32 = np.exp(out_fp32 - np.max(out_fp32))
        probs_fp32 = (exp_fp32 / np.sum(exp_fp32))[0]
        pred_fp32 = int(np.argmax(probs_fp32))
        
        # INT8 inference
        t0 = time.perf_counter()
        out_int8 = session_int8.run(None, {"input": t_img})[0]
        int8_latencies.append((time.perf_counter() - t0) * 1000.0)
        exp_int8 = np.exp(out_int8 - np.max(out_int8))
        probs_int8 = (exp_int8 / np.sum(exp_int8))[0]
        pred_int8 = int(np.argmax(probs_int8))
        
        diff = float(np.max(np.abs(probs_fp32 - probs_int8)))
        prob_diffs.append(diff)
        if pred_fp32 != pred_int8:
            disagreements += 1
            
        detailed_results.append({
            "specimen_id": row["specimen_id"],
            "true_genus": row["genus"],
            "fp32_predicted": IDX_TO_CLASS[pred_fp32],
            "fp32_probabilities": {CLASSES[i]: round(float(probs_fp32[i]), 4) for i in range(3)},
            "int8_predicted": IDX_TO_CLASS[pred_int8],
            "int8_probabilities": {CLASSES[i]: round(float(probs_int8[i]), 4) for i in range(3)},
            "max_prob_diff": round(diff, 4),
            "disagreement": pred_fp32 != pred_int8,
        })
        
    num_comparison = {
        "winning_candidate": "effnet_b0_224",
        "image_size": 224,
        "fp32_model": {
            "path": fp32_onnx_path,
            "sha256": fp32_hash,
            "size_bytes": fp32_size,
            "median_latency_ms": round(float(np.median(fp32_latencies)), 2),
            "p95_latency_ms": round(float(np.percentile(fp32_latencies, 95)), 2),
        },
        "int8_model": {
            "path": int8_onnx_path,
            "sha256": int8_hash,
            "size_bytes": int8_size,
            "median_latency_ms": round(float(np.median(int8_latencies)), 2),
            "p95_latency_ms": round(float(np.percentile(int8_latencies, 95)), 2),
        },
        "mean_probability_diff": round(float(np.mean(prob_diffs)), 4),
        "max_probability_diff": round(float(np.max(prob_diffs)), 4),
        "total_specimens_evaluated": len(orig_df),
        "predicted_genus_disagreements": disagreements,
        "disagreement_rate": round(disagreements / len(orig_df), 4),
        "status": "EXPERIMENTAL_NOT_FIELD_VALIDATED",
        "detailed_results": detailed_results,
    }
    
    comp_json_path = os.path.join(REPORTS_DIR, "v3_onnx_comparison.json")
    with open(comp_json_path, "w") as f:
        json.dump(num_comparison, f, indent=2)
        
    print(f"\nSaved ONNX comparison report: {comp_json_path}")
    print(f"FP32 vs INT8 Mean Probability Drift: {num_comparison['mean_probability_diff']}")
    print(f"FP32 vs INT8 Max Probability Drift: {num_comparison['max_probability_diff']}")
    print(f"Genus Prediction Disagreements: {disagreements} / {len(orig_df)} ({num_comparison['disagreement_rate']*100}%)")
    print(f"FP32 Latency (Median / p95): {num_comparison['fp32_model']['median_latency_ms']}ms / {num_comparison['fp32_model']['p95_latency_ms']}ms")
    print(f"INT8 Latency (Median / p95): {num_comparison['int8_model']['median_latency_ms']}ms / {num_comparison['int8_model']['p95_latency_ms']}ms")
    print("=" * 70)
    print("VECTORA AI 3.0: EVALUATION COMPLETED SUCCESSFULLY")
    print("=" * 70)

if __name__ == "__main__":
    main()
