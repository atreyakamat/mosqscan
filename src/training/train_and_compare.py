#!/usr/bin/env python3
"""
Vectora AI 3.0: Classifier Cross-Validation, Comparison, Final Training & ONNX Export
ASD-STE100 Compliant Implementation with in-memory caching and unbuffered progress reporting.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import resource
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple, Any

# Suppress NNPACK / C++ warnings and ensure line-buffered immediate stdout
os.environ["TORCH_CPP_LOG_LEVEL"] = "ERROR"
os.environ["GLOG_minloglevel"] = "3"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

import numpy as np
import pandas as pd
from PIL import Image
from sklearn.metrics import classification_report, confusion_matrix, balanced_accuracy_score, f1_score
from sklearn.model_selection import StratifiedGroupKFold
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from torchvision.models import (
    efficientnet_b0, EfficientNet_B0_Weights,
    mobilenet_v3_large, MobileNet_V3_Large_Weights
)
import onnx
import onnxruntime as ort
from onnxruntime.quantization import quantize_dynamic, QuantType

# Set CPU threading
torch.set_num_threads(4)

CLASSES = ["aedes", "anopheles", "culex"]
CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}
IDX_TO_CLASS = {i: c for i, c in enumerate(CLASSES)}

PROJECT_ROOT = "/home/nimr/Projects/mosqscan"
METADATA_DIR = os.path.join(PROJECT_ROOT, "data/metadata")
MODELS_DIR = os.path.join(PROJECT_ROOT, "models/v3")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")

# In-memory image cache to avoid disk I/O and JPEG decoding bottlenecks
_IMAGE_CACHE: Dict[str, Image.Image] = {}

def get_cached_image(path: str) -> Image.Image:
    if path not in _IMAGE_CACHE:
        with Image.open(path) as im:
            _IMAGE_CACHE[path] = im.convert("RGB")
    return _IMAGE_CACHE[path]

def get_peak_ram_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def build_transforms(img_size: int, train: bool):
    if train:
        return transforms.Compose([
            transforms.Resize((img_size, img_size)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomRotation(degrees=10),
            transforms.ColorJitter(brightness=0.1, contrast=0.1, saturation=0.05),
            transforms.ToTensor(),
            transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ])
    return transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
    ])

class MosqDataset(Dataset):
    def __init__(self, df: pd.DataFrame, transform=None):
        self.df = df.reset_index(drop=True)
        self.transform = transform

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        img = get_cached_image(row["file_path"])
        if self.transform:
            img = self.transform(img)
        label = CLASS_TO_IDX[row["genus"].lower()]
        return img, label

def create_candidate_model(name: str):
    if name == "efficientnet_b0":
        m = efficientnet_b0(weights=EfficientNet_B0_Weights.DEFAULT)
        in_feat = m.classifier[1].in_features
        m.classifier[1] = nn.Linear(in_feat, 3)
        return m
    elif name == "mobilenet_v3_large":
        m = mobilenet_v3_large(weights=MobileNet_V3_Large_Weights.DEFAULT)
        in_feat = m.classifier[3].in_features
        m.classifier[3] = nn.Linear(in_feat, 3)
        return m
    else:
        raise ValueError(f"Unknown candidate {name}")

def unfreeze_top_layers(model, name: str):
    for p in model.parameters():
        p.requires_grad = False
    if name.startswith("efficientnet_b0"):
        for p in model.features[7].parameters():
            p.requires_grad = True
        for p in model.classifier.parameters():
            p.requires_grad = True
    elif name.startswith("mobilenet_v3"):
        for p in model.features[-1].parameters():
            p.requires_grad = True
        for p in model.classifier.parameters():
            p.requires_grad = True

def freeze_backbone(model, name: str):
    for p in model.parameters():
        p.requires_grad = False
    if name.startswith("efficientnet_b0"):
        for p in model.classifier.parameters():
            p.requires_grad = True
    elif name.startswith("mobilenet_v3"):
        for p in model.classifier.parameters():
            p.requires_grad = True

def compute_weights(df: pd.DataFrame) -> torch.Tensor:
    counts = df["genus"].str.lower().value_counts().to_dict()
    total = len(df)
    weights = []
    for c in CLASSES:
        cnt = counts.get(c, 1)
        weights.append(total / (3.0 * cnt))
    return torch.tensor(weights, dtype=torch.float32)

def evaluate_loader(model: nn.Module, loader: DataLoader) -> Dict[str, Any]:
    model.eval()
    y_true, y_pred = [], []
    with torch.no_grad():
        for imgs, labels in loader:
            logits = model(imgs)
            preds = logits.argmax(dim=1)
            y_true.extend(labels.tolist())
            y_pred.extend(preds.tolist())
            
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    bal_acc = float(balanced_accuracy_score(y_true, y_pred))
    acc = float(np.mean(np.array(y_true) == np.array(y_pred)))
    
    rep = classification_report(
        y_true, y_pred,
        labels=[0, 1, 2],
        target_names=CLASSES,
        output_dict=True,
        zero_division=0
    )
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1, 2]).tolist()
    
    return {
        "macro_f1": round(macro_f1, 4),
        "balanced_accuracy": round(bal_acc, 4),
        "accuracy": round(acc, 4),
        "per_class": {
            c: {
                "precision": round(rep[c]["precision"], 4),
                "recall": round(rep[c]["recall"], 4),
                "f1": round(rep[c]["f1-score"], 4),
                "support": rep[c]["support"],
            } for c in CLASSES
        },
        "confusion_matrix": cm,
    }

def benchmark_latency(model: nn.Module, img_size: int, num_runs: int = 10) -> Dict[str, float]:
    model.eval()
    dummy = torch.randn(1, 3, img_size, img_size)
    for _ in range(2):
        _ = model(dummy)
    latencies = []
    for _ in range(num_runs):
        t0 = time.perf_counter()
        with torch.no_grad():
            _ = model(dummy)
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)
    return {
        "median_ms": round(float(np.median(latencies)), 2),
        "p95_ms": round(float(np.percentile(latencies, 95)), 2),
    }

def train_single_fold(
    candidate_name: str,
    img_size: int,
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    use_class_weights: bool = True,
    batch_size: int = 8,
) -> Tuple[Dict[str, Any], nn.Module]:
    t0 = time.time()
    model = create_candidate_model(candidate_name)
    
    train_ds = MosqDataset(train_df, transform=build_transforms(img_size, train=True))
    val_ds = MosqDataset(val_df, transform=build_transforms(img_size, train=False))
    
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, drop_last=False)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)
    
    weights = compute_weights(train_df) if use_class_weights else None
    criterion = nn.CrossEntropyLoss(weight=weights)
    
    # Stage 1: Train Head Only (1 epoch)
    freeze_backbone(model, candidate_name)
    opt_head = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=0.001, weight_decay=1e-4
    )
    
    model.train()
    for imgs, labels in train_loader:
        opt_head.zero_grad()
        logits = model(imgs)
        loss = criterion(logits, labels)
        loss.backward()
        opt_head.step()
            
    # Stage 2: Unfreeze top layers and fine-tune (1 epoch)
    unfreeze_top_layers(model, candidate_name)
    opt_finetune = torch.optim.AdamW([
        {"params": [p for p in model.features.parameters() if p.requires_grad], "lr": 0.00002},
        {"params": [p for p in model.classifier.parameters() if p.requires_grad], "lr": 0.0002},
    ], weight_decay=1e-4)
    
    model.train()
    for imgs, labels in train_loader:
        opt_finetune.zero_grad()
        logits = model(imgs)
        loss = criterion(logits, labels)
        loss.backward()
        opt_finetune.step()
            
    eval_metrics = evaluate_loader(model, val_loader)
    latency = benchmark_latency(model, img_size)
    eval_metrics["latency"] = latency
    eval_metrics["training_time_s"] = round(time.time() - t0, 1)
    eval_metrics["peak_ram_mb"] = round(get_peak_ram_mb(), 1)
    
    return eval_metrics, model

def run_cross_validation():
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    # Load manifest and lineage
    manifest_df = pd.read_json(os.path.join(METADATA_DIR, "dataset_manifest.json"))
    lineage_df = pd.read_csv(os.path.join(METADATA_DIR, "augmentation_lineage.csv"))
    
    orig_df = manifest_df[manifest_df["dataset_type"] == "original"].copy()
    verified_aug_df = lineage_df[lineage_df["verification_status"] == "VERIFIED"].copy()
    
    verified_aug_df["file_path"] = verified_aug_df["augmented_image"].apply(
        lambda p: os.path.join(PROJECT_ROOT, p)
    )
    verified_aug_df["specimen_id"] = verified_aug_df["parent_specimen_id"]
    
    print("Pre-caching dataset images into memory...", flush=True)
    t_cache_0 = time.time()
    for p in orig_df["file_path"]:
        get_cached_image(p)
    # Pre-cache sampled augmentations (first 6 per specimen)
    sample_aug = verified_aug_df.groupby("specimen_id").head(6)
    for p in sample_aug["file_path"]:
        get_cached_image(p)
    print(f"Pre-cached {len(_IMAGE_CACHE)} images in {round(time.time() - t_cache_0, 2)}s", flush=True)
    
    candidates = [
        {"id": "effnet_b0_224", "base_model": "efficientnet_b0", "img_size": 224, "batch_size": 8},
        {"id": "effnet_b0_384", "base_model": "efficientnet_b0", "img_size": 384, "batch_size": 4},
        {"id": "mobilenet_v3_224", "base_model": "mobilenet_v3_large", "img_size": 224, "batch_size": 8},
    ]
    
    seeds = [42, 1337]
    cv_results = {}
    
    print("=" * 70, flush=True)
    print("VECTORA AI 3.0: COMMENCING 4-FOLD STRATIFIED GROUP CROSS-VALIDATION", flush=True)
    print(f"Total Original Specimens: {len(orig_df)}", flush=True)
    print(f"Total Verified Augmentations: {len(verified_aug_df)}", flush=True)
    print("=" * 70, flush=True)
    
    for cand in candidates:
        cand_id = cand["id"]
        base_model = cand["base_model"]
        img_size = cand["img_size"]
        bs = cand["batch_size"]
        
        print(f"\nEvaluating Candidate: {cand_id} (Size={img_size}x{img_size}, Batch={bs})...", flush=True)
        cand_folds = []
        
        for seed in seeds:
            sgkf = StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=seed)
            for fold, (train_idx, val_idx) in enumerate(sgkf.split(orig_df, orig_df["genus"], orig_df["specimen_id"])):
                val_orig = orig_df.iloc[val_idx]
                train_orig = orig_df.iloc[train_idx]
                
                # Training set: training original + verified augmentations belonging ONLY to training specimens
                train_specimen_ids = set(train_orig["specimen_id"])
                # Sample 2 verified augmentations per specimen for fast, balanced CV
                train_aug = verified_aug_df[verified_aug_df["specimen_id"].isin(train_specimen_ids)]
                train_aug_sampled = train_aug.groupby("specimen_id").head(2)
                
                fold_train_df = pd.concat([
                    train_orig[["file_path", "genus", "specimen_id"]],
                    train_aug_sampled[["file_path", "genus", "specimen_id"]]
                ], ignore_index=True)
                
                # Validation set: strictly original specimens in validation split (no augmentations)
                fold_val_df = val_orig[["file_path", "genus", "specimen_id"]].copy()
                
                metrics, _ = train_single_fold(
                    candidate_name=base_model,
                    img_size=img_size,
                    train_df=fold_train_df,
                    val_df=fold_val_df,
                    use_class_weights=True,
                    batch_size=bs,
                )
                metrics["seed"] = seed
                metrics["fold"] = fold
                cand_folds.append(metrics)
                print(f"  [Cand: {cand_id}] Seed {seed} Fold {fold}: Macro-F1={metrics['macro_f1']}, BalAcc={metrics['balanced_accuracy']}, AnophRecall={metrics['per_class']['anopheles']['recall']} ({metrics['training_time_s']}s)", flush=True)
                
        # Aggregate stats
        f1s = [f["macro_f1"] for f in cand_folds]
        baccs = [f["balanced_accuracy"] for f in cand_folds]
        accs = [f["accuracy"] for f in cand_folds]
        anoph_recalls = [f["per_class"]["anopheles"]["recall"] for f in cand_folds]
        latencies = [f["latency"]["median_ms"] for f in cand_folds]
        durations = [f["training_time_s"] for f in cand_folds]
        peak_rams = [f["peak_ram_mb"] for f in cand_folds]
        
        cv_results[cand_id] = {
            "candidate_id": cand_id,
            "base_model": base_model,
            "image_size": img_size,
            "mean_macro_f1": round(float(np.mean(f1s)), 4),
            "std_macro_f1": round(float(np.std(f1s)), 4),
            "mean_balanced_accuracy": round(float(np.mean(baccs)), 4),
            "std_balanced_accuracy": round(float(np.std(baccs)), 4),
            "mean_accuracy": round(float(np.mean(accs)), 4),
            "mean_anopheles_recall": round(float(np.mean(anoph_recalls)), 4),
            "mean_median_latency_ms": round(float(np.mean(latencies)), 2),
            "mean_training_time_s": round(float(np.mean(durations)), 1),
            "mean_peak_ram_mb": round(float(np.mean(peak_rams)), 1),
            "folds": cand_folds,
        }
        print(f"--> {cand_id} Summary: Macro-F1={cv_results[cand_id]['mean_macro_f1']}±{cv_results[cand_id]['std_macro_f1']}, BalAcc={cv_results[cand_id]['mean_balanced_accuracy']}, AnophelesRecall={cv_results[cand_id]['mean_anopheles_recall']}, Latency={cv_results[cand_id]['mean_median_latency_ms']}ms", flush=True)

    # Save CV results JSON
    cv_json_path = os.path.join(REPORTS_DIR, "v3_cv_results.json")
    with open(cv_json_path, "w") as f:
        json.dump(cv_results, f, indent=2)
    print(f"\nSaved cross-validation results to: {cv_json_path}", flush=True)
    
    # Select winning candidate based on cross-validation macro-F1 & Anopheles recall
    best_candidate_id = max(
        cv_results.keys(),
        key=lambda k: (cv_results[k]["mean_macro_f1"], cv_results[k]["mean_anopheles_recall"])
    )
    print(f"\nWINNING CANDIDATE SELECTED: {best_candidate_id}", flush=True)
    winning_cfg = next(c for c in candidates if c["id"] == best_candidate_id)
    
    # ----------------------------------------------------
    # Train Final Model on ALL Original + Verified Augmentations
    # ----------------------------------------------------
    print("\n" + "=" * 70, flush=True)
    print(f"TRAINING FINAL EXPERIMENTAL MODEL: {best_candidate_id} on ALL Specimens", flush=True)
    print("=" * 70, flush=True)
    
    # Sample up to 4 augmentations per specimen for final training
    final_aug_sampled = verified_aug_df.groupby("specimen_id").head(4)
    full_train_df = pd.concat([
        orig_df[["file_path", "genus", "specimen_id"]],
        final_aug_sampled[["file_path", "genus", "specimen_id"]]
    ], ignore_index=True)
    
    final_img_size = winning_cfg["img_size"]
    final_model = create_candidate_model(winning_cfg["base_model"])
    
    full_ds = MosqDataset(full_train_df, transform=build_transforms(final_img_size, train=True))
    full_loader = DataLoader(full_ds, batch_size=winning_cfg["batch_size"], shuffle=True)
    
    weights = compute_weights(full_train_df)
    criterion = nn.CrossEntropyLoss(weight=weights)
    
    # Stage 1: Head (2 epochs)
    freeze_backbone(final_model, winning_cfg["base_model"])
    opt_head = torch.optim.AdamW(
        [p for p in final_model.parameters() if p.requires_grad],
        lr=0.001, weight_decay=1e-4
    )
    for epoch in range(2):
        final_model.train()
        for imgs, labels in full_loader:
            opt_head.zero_grad()
            loss = criterion(final_model(imgs), labels)
            loss.backward()
            opt_head.step()
        print(f"  Final model head epoch {epoch+1}/2 complete", flush=True)
            
    # Stage 2: Top backbone fine-tune (2 epochs)
    unfreeze_top_layers(final_model, winning_cfg["base_model"])
    opt_full = torch.optim.AdamW([
        {"params": [p for p in final_model.features.parameters() if p.requires_grad], "lr": 0.00002},
        {"params": [p for p in final_model.classifier.parameters() if p.requires_grad], "lr": 0.0002},
    ], weight_decay=1e-4)
    for epoch in range(2):
        final_model.train()
        for imgs, labels in full_loader:
            opt_full.zero_grad()
            loss = criterion(final_model(imgs), labels)
            loss.backward()
            opt_full.step()
        print(f"  Final model fine-tune epoch {epoch+1}/2 complete", flush=True)
            
    # Save PyTorch checkpoint
    pt_path = os.path.join(MODELS_DIR, "vectora_v3_best.pt")
    torch.save(final_model.state_dict(), pt_path)
    print(f"Saved PyTorch weights: {pt_path} ({os.path.getsize(pt_path)} bytes)", flush=True)
    
    # ----------------------------------------------------
    # Export FP32 ONNX
    # ----------------------------------------------------
    final_model.eval()
    fp32_onnx_path = os.path.join(MODELS_DIR, "vectora_v3_fp32.onnx")
    dummy_input = torch.randn(1, 3, final_img_size, final_img_size)
    
    torch.onnx.export(
        final_model,
        dummy_input,
        fp32_onnx_path,
        export_params=True,
        opset_version=17,
        do_constant_folding=True,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={"input": {0: "batch_size"}, "output": {0: "batch_size"}},
    )
    onnx_model = onnx.load(fp32_onnx_path)
    onnx.checker.check_model(onnx_model)
    fp32_hash = sha256_file(fp32_onnx_path)
    fp32_size = os.path.getsize(fp32_onnx_path)
    print(f"Exported FP32 ONNX: {fp32_onnx_path} ({fp32_size} bytes, SHA-256: {fp32_hash})", flush=True)
    
    # ----------------------------------------------------
    # Export INT8 Quantized ONNX
    # ----------------------------------------------------
    int8_onnx_path = os.path.join(MODELS_DIR, "vectora_v3_int8.onnx")
    quantize_dynamic(
        model_input=fp32_onnx_path,
        model_output=int8_onnx_path,
        weight_type=QuantType.QInt8,
    )
    int8_hash = sha256_file(int8_onnx_path)
    int8_size = os.path.getsize(int8_onnx_path)
    print(f"Exported INT8 ONNX: {int8_onnx_path} ({int8_size} bytes, SHA-256: {int8_hash})", flush=True)
    
    # ----------------------------------------------------
    # Numerical Comparison: FP32 vs INT8 on 44 Original Specimens
    # ----------------------------------------------------
    so = ort.SessionOptions()
    so.intra_op_num_threads = 4
    so.inter_op_num_threads = 1
    session_fp32 = ort.InferenceSession(fp32_onnx_path, so, providers=["CPUExecutionProvider"])
    session_int8 = ort.InferenceSession(int8_onnx_path, so, providers=["CPUExecutionProvider"])
    
    val_trans = build_transforms(final_img_size, train=False)
    
    prob_diffs = []
    disagreements = 0
    detailed_specimen_results = []
    
    fp32_latencies, int8_latencies = [], []
    
    for idx, row in orig_df.iterrows():
        pil_im = get_cached_image(row["file_path"])
        t_img = val_trans(pil_im).unsqueeze(0).numpy()
            
        # FP32
        t0 = time.perf_counter()
        out_fp32 = session_fp32.run(None, {"input": t_img})[0]
        fp32_latencies.append((time.perf_counter() - t0) * 1000.0)
        exp_fp32 = np.exp(out_fp32 - np.max(out_fp32))
        probs_fp32 = (exp_fp32 / np.sum(exp_fp32))[0]
        pred_fp32 = int(np.argmax(probs_fp32))
        
        # INT8
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
            
        detailed_specimen_results.append({
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
        "winning_candidate": best_candidate_id,
        "image_size": final_img_size,
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
        "detailed_results": detailed_specimen_results,
    }
    
    comp_json_path = os.path.join(REPORTS_DIR, "v3_onnx_comparison.json")
    with open(comp_json_path, "w") as f:
        json.dump(num_comparison, f, indent=2)
    print(f"\nSaved ONNX comparison to: {comp_json_path}", flush=True)
    print(f"FP32 vs INT8 Mean Prob Diff: {num_comparison['mean_probability_diff']}, Max: {num_comparison['max_probability_diff']}, Disagreements: {disagreements}/{len(orig_df)}", flush=True)
    print("=" * 70, flush=True)
    print("VECTORA AI 3.0: TRAINING AND EXPORT COMPLETED SUCCESSFULLY", flush=True)
    print("=" * 70, flush=True)

if __name__ == "__main__":
    run_cross_validation()
