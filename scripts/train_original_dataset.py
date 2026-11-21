#!/usr/bin/env python3
"""
Vectora AI: Dataset Inspection & Model Training on 'Mosquito Images Original'
ASD-STE100 Compliant Implementation.

Workflow:
1. Inspect all 44 physical images in 'Mosquito Images Original'.
2. Verify image integrity, resolutions, channels, and class distributions.
3. Execute 4-Fold Stratified Cross-Validation on the 44 specimens with dynamic training augmentation.
4. Train final EfficientNet-B0 model on all 44 original specimens.
5. Export PyTorch checkpoint and ONNX FP32 model.
6. Verify ONNX export with ONNX Runtime.
7. Record full metrics to JSON and Markdown reports.
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

os.environ["TORCH_CPP_LOG_LEVEL"] = "ERROR"
os.environ["GLOG_minloglevel"] = "3"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

import numpy as np
import pandas as pd
from PIL import Image, ImageStat
from sklearn.metrics import classification_report, confusion_matrix, balanced_accuracy_score, f1_score, precision_recall_fscore_support
from sklearn.model_selection import StratifiedKFold
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights
import onnx
import onnxruntime as ort

# Configuration
torch.set_num_threads(4)
PROJECT_ROOT = Path("/home/nimr/Projects/mosqscan")
ORIGINAL_DIR = PROJECT_ROOT / "Mosquito Images Original"
MODELS_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "reports"

CLASSES = ["aedes", "anopheles", "culex"]
CLASS_TO_IDX = {"aedes": 0, "anopheles": 1, "culex": 2}
IDX_TO_CLASS = {0: "aedes", 1: "anopheles", 2: "culex"}
IMG_SIZE = 224

def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

# ----------------------------------------------------------------------
# 1. Image Inspection
# ----------------------------------------------------------------------
def inspect_original_dataset(base_dir: Path) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    print("=" * 70)
    print("1. INSPECTING 'Mosquito Images Original' DATASET")
    print("=" * 70)
    
    records = []
    for p in sorted(base_dir.rglob("*.jpg")):
        parent_name = p.parent.name.lower()
        if "aedes" in parent_name:
            genus = "aedes"
        elif "anopheles" in parent_name:
            genus = "anopheles"
        elif "culex" in parent_name:
            genus = "culex"
        else:
            continue
            
        stat = p.stat()
        sha = sha256_file(p)
        
        with Image.open(p) as img:
            w, h = img.size
            mode = img.mode
            img_rgb = img.convert("RGB")
            stat_calc = ImageStat.Stat(img_rgb)
            mean_luminance = float(np.mean(stat_calc.mean))
            std_luminance = float(np.mean(stat_calc.stddev))
            
        records.append({
            "filename": p.name,
            "filepath": str(p),
            "genus": genus,
            "label_idx": CLASS_TO_IDX[genus],
            "file_size_bytes": stat.st_size,
            "sha256": sha,
            "width": w,
            "height": h,
            "aspect_ratio": round(w / h, 3),
            "mode": mode,
            "mean_luminance": round(mean_luminance, 2),
            "std_luminance": round(std_luminance, 2),
        })
        
    df = pd.DataFrame(records)
    print(f"Total images found: {len(df)}")
    
    summary = {
        "total_images": len(df),
        "class_distribution": df["genus"].value_counts().to_dict(),
        "resolutions": df.groupby(["width", "height"]).size().to_dict(),
        "color_modes": df["mode"].value_counts().to_dict(),
        "mean_file_size_kb": round(df["file_size_bytes"].mean() / 1024, 2),
        "mean_luminance": round(df["mean_luminance"].mean(), 2),
        "mean_contrast_std": round(df["std_luminance"].mean(), 2),
    }
    
    for genus, count in summary["class_distribution"].items():
        print(f"  - {genus.capitalize()}: {count} images ({round(count / len(df) * 100, 1)}%)")
    print(f"Unique resolutions: {list(summary['resolutions'].keys())}")
    print(f"Color modes: {list(summary['color_modes'].keys())}")
    print(f"Mean luminance: {summary['mean_luminance']} (std: {summary['mean_contrast_std']})")
    
    return df, summary

# ----------------------------------------------------------------------
# 2. Datasets and Transforms
# ----------------------------------------------------------------------
def build_transforms(img_size: int, is_train: bool):
    if is_train:
        return transforms.Compose([
            transforms.Resize((img_size + 32, img_size + 32)),
            transforms.RandomResizedCrop(img_size, scale=(0.8, 1.0)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomVerticalFlip(p=0.2),
            transforms.RandomRotation(degrees=15),
            transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.1),
            transforms.ToTensor(),
            transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ])
    return transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
    ])

class OriginalMosqDataset(Dataset):
    def __init__(self, df: pd.DataFrame, transform=None, augment_multiplier: int = 1):
        self.df = df.reset_index(drop=True)
        self.transform = transform
        self.augment_multiplier = augment_multiplier
        self.images = [Image.open(p).convert("RGB") for p in self.df["filepath"]]
        self.labels = self.df["label_idx"].values

    def __len__(self):
        return len(self.df) * self.augment_multiplier

    def __getitem__(self, idx):
        base_idx = idx % len(self.df)
        img = self.images[base_idx]
        label = self.labels[base_idx]
        if self.transform:
            img = self.transform(img)
        return img, torch.tensor(label, dtype=torch.long)

def build_model(num_classes: int = 3) -> nn.Module:
    weights = EfficientNet_B0_Weights.DEFAULT
    model = efficientnet_b0(weights=weights)
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.3, inplace=True),
        nn.Linear(in_features, num_classes)
    )
    return model

# ----------------------------------------------------------------------
# 3. Stratified 4-Fold Cross-Validation
# ----------------------------------------------------------------------
def run_cross_validation(df: pd.DataFrame) -> Dict[str, Any]:
    print("\n" + "=" * 70)
    print("2. EXECUTING 4-FOLD STRATIFIED CROSS-VALIDATION")
    print("=" * 70)
    
    skf = StratifiedKFold(n_splits=4, shuffle=True, random_state=42)
    val_trans = build_transforms(IMG_SIZE, is_train=False)
    
    fold_results = []
    all_y_true = []
    all_y_pred = []
    
    for fold, (train_idx, val_idx) in enumerate(skf.split(df, df["label_idx"])):
        train_df = df.iloc[train_idx]
        val_df = df.iloc[val_idx]
        
        # Calculate class weights for training
        class_counts = train_df["label_idx"].value_counts().sort_index().values
        class_weights = len(train_df) / (len(class_counts) * class_counts.astype(np.float32))
        weight_tensor = torch.tensor(class_weights, dtype=torch.float32)
        
        train_ds = OriginalMosqDataset(
            train_df,
            transform=build_transforms(IMG_SIZE, is_train=True),
            augment_multiplier=4  # 33 * 4 = 132 augmented views per epoch
        )
        val_ds = OriginalMosqDataset(val_df, transform=val_trans, augment_multiplier=1)
        
        train_loader = DataLoader(train_ds, batch_size=8, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=8, shuffle=False)
        
        model = build_model(3)
        criterion = nn.CrossEntropyLoss(weight=weight_tensor)
        
        # Stage 1: Classifier head (3 epochs)
        for param in model.features.parameters():
            param.requires_grad = False
        optimizer_head = torch.optim.AdamW(model.classifier.parameters(), lr=1e-3, weight_decay=1e-4)
        
        model.train()
        for _ in range(3):
            for imgs, targets in train_loader:
                optimizer_head.zero_grad()
                loss = criterion(model(imgs), targets)
                loss.backward()
                optimizer_head.step()
                
        # Stage 2: Fine-tune top features (4 epochs)
        for param in model.features[-3:].parameters():
            param.requires_grad = True
        optimizer_full = torch.optim.AdamW([
            {"params": model.features[-3:].parameters(), "lr": 2e-5},
            {"params": model.classifier.parameters(), "lr": 2e-4},
        ], weight_decay=1e-4)
        
        for _ in range(4):
            for imgs, targets in train_loader:
                optimizer_full.zero_grad()
                loss = criterion(model(imgs), targets)
                loss.backward()
                optimizer_full.step()
                
        # Evaluate Fold on untouched physical validation specimens
        model.eval()
        fold_y_true = []
        fold_y_pred = []
        with torch.no_grad():
            for imgs, targets in val_loader:
                outputs = model(imgs)
                preds = outputs.argmax(dim=1).cpu().numpy()
                fold_y_true.extend(targets.numpy())
                fold_y_pred.extend(preds)
                
        macro_f1 = f1_score(fold_y_true, fold_y_pred, average="macro", zero_division=0)
        bal_acc = balanced_accuracy_score(fold_y_true, fold_y_pred)
        acc = float(np.mean(np.array(fold_y_true) == np.array(fold_y_pred)))
        
        p, r, f, s = precision_recall_fscore_support(fold_y_true, fold_y_pred, labels=[0, 1, 2], zero_division=0)
        
        fold_stat = {
            "fold": fold + 1,
            "train_size": len(train_df),
            "val_size": len(val_df),
            "val_supports": {IDX_TO_CLASS[i]: int(s[i]) for i in range(3)},
            "macro_f1": round(float(macro_f1), 4),
            "balanced_accuracy": round(float(bal_acc), 4),
            "accuracy": round(float(acc), 4),
            "recall": {IDX_TO_CLASS[i]: round(float(r[i]), 4) for i in range(3)},
            "precision": {IDX_TO_CLASS[i]: round(float(p[i]), 4) for i in range(3)},
        }
        fold_results.append(fold_stat)
        all_y_true.extend(fold_y_true)
        all_y_pred.extend(fold_y_pred)
        
        print(f"  Fold {fold+1}: Macro-F1={fold_stat['macro_f1']:.4f}, BalAcc={fold_stat['balanced_accuracy']:.4f}, "
              f"AeRec={fold_stat['recall']['aedes']:.2f}, AnRec={fold_stat['recall']['anopheles']:.2f}, CxRec={fold_stat['recall']['culex']:.2f}")

    mean_f1 = float(np.mean([f["macro_f1"] for f in fold_results]))
    std_f1 = float(np.std([f["macro_f1"] for f in fold_results], ddof=1))
    mean_bal_acc = float(np.mean([f["balanced_accuracy"] for f in fold_results]))
    std_bal_acc = float(np.std([f["balanced_accuracy"] for f in fold_results], ddof=1))
    overall_acc = float(np.mean(np.array(all_y_true) == np.array(all_y_pred)))
    
    cm = confusion_matrix(all_y_true, all_y_pred, labels=[0, 1, 2]).tolist()
    
    cv_summary = {
        "mean_macro_f1": round(mean_f1, 4),
        "std_macro_f1": round(std_f1, 4),
        "mean_balanced_accuracy": round(mean_bal_acc, 4),
        "std_balanced_accuracy": round(std_bal_acc, 4),
        "overall_accuracy": round(overall_acc, 4),
        "cumulative_confusion_matrix": cm,
        "folds": fold_results,
    }
    
    print("\nCV Summary:")
    print(f"  Mean Macro-F1: {cv_summary['mean_macro_f1']} +/- {cv_summary['std_macro_f1']}")
    print(f"  Mean Balanced Accuracy: {cv_summary['mean_balanced_accuracy']} +/- {cv_summary['std_balanced_accuracy']}")
    print(f"  Overall Accuracy: {cv_summary['overall_accuracy']}")
    print("  Cumulative Confusion Matrix (Aedes, Anopheles, Culex):")
    for row in cm:
        print(f"    {row}")
        
    return cv_summary

# ----------------------------------------------------------------------
# 4. Full Dataset Training & ONNX Export
# ----------------------------------------------------------------------
def train_full_model(df: pd.DataFrame) -> Tuple[nn.Module, Dict[str, Any]]:
    print("\n" + "=" * 70)
    print("3. TRAINING FINAL MODEL ON ALL 44 ORIGINAL SPECIMENS")
    print("=" * 70)
    
    class_counts = df["label_idx"].value_counts().sort_index().values
    class_weights = len(df) / (len(class_counts) * class_counts.astype(np.float32))
    weight_tensor = torch.tensor(class_weights, dtype=torch.float32)
    print(f"Computed inverse class weights: {weight_tensor.tolist()}")
    
    train_ds = OriginalMosqDataset(
        df,
        transform=build_transforms(IMG_SIZE, is_train=True),
        augment_multiplier=6  # 44 * 6 = 264 dynamic views per epoch
    )
    train_loader = DataLoader(train_ds, batch_size=8, shuffle=True)
    
    model = build_model(3)
    criterion = nn.CrossEntropyLoss(weight=weight_tensor)
    
    # Stage 1: Linear Probe Classifier Head (4 epochs)
    print("Stage 1: Training classifier head (features frozen)...")
    for param in model.features.parameters():
        param.requires_grad = False
    opt_head = torch.optim.AdamW(model.classifier.parameters(), lr=1e-3, weight_decay=1e-4)
    
    model.train()
    for ep in range(4):
        total_loss = 0.0
        for imgs, targets in train_loader:
            opt_head.zero_grad()
            loss = criterion(model(imgs), targets)
            loss.backward()
            opt_head.step()
            total_loss += loss.item() * len(targets)
        avg_loss = total_loss / len(train_ds)
        print(f"  Head Epoch {ep+1}/4 - Loss: {avg_loss:.4f}")
        
    # Stage 2: Fine-Tuning Top Features (6 epochs)
    print("Stage 2: Fine-tuning top backbone features...")
    for param in model.features[-4:].parameters():
        param.requires_grad = True
    opt_full = torch.optim.AdamW([
        {"params": model.features[-4:].parameters(), "lr": 2e-5},
        {"params": model.classifier.parameters(), "lr": 2e-4},
    ], weight_decay=1e-4)
    
    for ep in range(6):
        total_loss = 0.0
        for imgs, targets in train_loader:
            opt_full.zero_grad()
            loss = criterion(model(imgs), targets)
            loss.backward()
            opt_full.step()
            total_loss += loss.item() * len(targets)
        avg_loss = total_loss / len(train_ds)
        print(f"  Fine-tune Epoch {ep+1}/6 - Loss: {avg_loss:.4f}")
        
    # Evaluate fit on unaugmented original images
    model.eval()
    val_trans = build_transforms(IMG_SIZE, is_train=False)
    eval_ds = OriginalMosqDataset(df, transform=val_trans, augment_multiplier=1)
    eval_loader = DataLoader(eval_ds, batch_size=8, shuffle=False)
    
    all_preds, all_probs, all_targets = [], [], []
    with torch.no_grad():
        for imgs, targets in eval_loader:
            logits = model(imgs)
            probs = torch.softmax(logits, dim=1).cpu().numpy()
            preds = logits.argmax(dim=1).cpu().numpy()
            all_probs.extend(probs)
            all_preds.extend(preds)
            all_targets.extend(targets.numpy())
            
    train_fit_acc = float(np.mean(np.array(all_preds) == np.array(all_targets)))
    train_fit_f1 = float(f1_score(all_targets, all_preds, average="macro"))
    train_fit_cm = confusion_matrix(all_targets, all_preds, labels=[0, 1, 2]).tolist()
    
    training_metrics = {
        "final_epoch_loss": round(avg_loss, 4),
        "unaugmented_fit_accuracy": round(train_fit_acc, 4),
        "unaugmented_fit_macro_f1": round(train_fit_f1, 4),
        "confusion_matrix": train_fit_cm,
    }
    
    print(f"\nModel fit on 44 original photographs (unaugmented):")
    print(f"  Accuracy: {training_metrics['unaugmented_fit_accuracy']}")
    print(f"  Macro-F1: {training_metrics['unaugmented_fit_macro_f1']}")
    print(f"  Confusion matrix: {train_fit_cm}")
    
    return model, training_metrics

# ----------------------------------------------------------------------
# 5. Export and Verify Artifacts
# ----------------------------------------------------------------------
def export_and_verify(model: nn.Module, df: pd.DataFrame) -> Dict[str, Any]:
    print("\n" + "=" * 70)
    print("4. EXPORTING AND VERIFYING ONNX ARTIFACTS")
    print("=" * 70)
    
    pt_path = MODELS_DIR / "vectora_original_trained.pt"
    onnx_path = MODELS_DIR / "vectora_original_trained_fp32.onnx"
    
    # 1. Save PyTorch state dict
    torch.save(model.state_dict(), pt_path)
    pt_size = pt_path.stat().st_size
    pt_sha = sha256_file(pt_path)
    print(f"Saved PyTorch weights: {pt_path} ({round(pt_size / 1024 / 1024, 2)} MB)")
    print(f"  SHA-256: {pt_sha}")
    
    # 2. Export ONNX
    dummy_input = torch.randn(1, 3, IMG_SIZE, IMG_SIZE)
    torch.onnx.export(
        model,
        dummy_input,
        str(onnx_path),
        export_params=True,
        opset_version=17,
        do_constant_folding=True,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={"input": {0: "batch_size"}, "output": {0: "batch_size"}},
    )
    
    onnx_model = onnx.load(str(onnx_path))
    onnx.checker.check_model(onnx_model)
    onnx_size = onnx_path.stat().st_size
    onnx_sha = sha256_file(onnx_path)
    print(f"Exported ONNX FP32: {onnx_path} ({round(onnx_size / 1024 / 1024, 2)} MB)")
    print(f"  SHA-256: {onnx_sha}")
    
    # 3. Verify ONNX Runtime Session
    so = ort.SessionOptions()
    so.intra_op_num_threads = 4
    session = ort.InferenceSession(str(onnx_path), so, providers=["CPUExecutionProvider"])
    
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name
    
    val_trans = build_transforms(IMG_SIZE, is_train=False)
    test_latencies = []
    onnx_preds = []
    
    for _, row in df.iterrows():
        img = Image.open(row["filepath"]).convert("RGB")
        tensor = val_trans(img).unsqueeze(0).numpy()
        
        t0 = time.perf_counter()
        ort_out = session.run([output_name], {input_name: tensor})[0]
        dt = (time.perf_counter() - t0) * 1000.0
        test_latencies.append(dt)
        
        pred_idx = int(np.argmax(ort_out, axis=1)[0])
        onnx_preds.append(pred_idx)
        
    onnx_acc = float(np.mean(np.array(onnx_preds) == df["label_idx"].values))
    median_latency = float(np.median(test_latencies))
    p95_latency = float(np.percentile(test_latencies, 95))
    
    print(f"ONNX Runtime Verification:")
    print(f"  Inferences run: {len(onnx_preds)}")
    print(f"  Accuracy matches: {round(onnx_acc * 100, 2)}%")
    print(f"  Median CPU Latency: {round(median_latency, 2)} ms (p95: {round(p95_latency, 2)} ms)")
    
    export_metadata = {
        "pytorch_path": str(pt_path),
        "pytorch_sha256": pt_sha,
        "pytorch_size_bytes": pt_size,
        "onnx_path": str(onnx_path),
        "onnx_sha256": onnx_sha,
        "onnx_size_bytes": onnx_size,
        "median_cpu_latency_ms": round(median_latency, 2),
        "p95_cpu_latency_ms": round(p95_latency, 2),
        "onnx_accuracy_on_originals": round(onnx_acc, 4),
    }
    return export_metadata

# ----------------------------------------------------------------------
# Main Execution
# ----------------------------------------------------------------------
def main():
    start_time = time.time()
    df, inspect_summary = inspect_original_dataset(ORIGINAL_DIR)
    
    cv_summary = run_cross_validation(df)
    
    model, train_metrics = train_full_model(df)
    
    export_meta = export_and_verify(model, df)
    
    total_duration = round(time.time() - start_time, 2)
    print(f"\nExecution finished in {total_duration} seconds.")
    
    output_report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "execution_duration_seconds": total_duration,
        "inspection_summary": inspect_summary,
        "cross_validation": cv_summary,
        "training_fit": train_metrics,
        "export_metadata": export_meta,
    }
    
    json_path = REPORTS_DIR / "original_dataset_training_results.json"
    with open(json_path, "w") as f:
        json.dump(output_report, f, indent=2)
    print(f"Saved full JSON results to: {json_path}")

if __name__ == "__main__":
    main()
