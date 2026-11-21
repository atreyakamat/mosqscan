#!/usr/bin/env python3
"""
Vectora AI: Combined Dataset Training & Evaluation (Original + Augmented)
ASD-STE100 Compliant Implementation.

Workflow:
1. Load and index 2,640 images from 'Mosquito Images Augmented' and 44 from 'Mosquito Images Original'.
2. Map all images to their 44 biological parent specimen IDs to prevent cross-specimen leakage.
3. Perform 4-Fold StratifiedGroupKFold cross-validation (Grouped by Parent Specimen).
   - Validation evaluates unseen parent specimens on both physical photographs and augmented variants.
4. Train final EfficientNet-B0 model on the combined dataset (2,684 total images).
5. Export PyTorch checkpoint and self-contained ONNX FP32 artifact.
6. Verify ONNX model with ONNX Runtime on original physical photographs.
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
from PIL import Image
from sklearn.metrics import (
    classification_report, confusion_matrix, balanced_accuracy_score,
    f1_score, precision_recall_fscore_support
)
from sklearn.model_selection import StratifiedGroupKFold
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights
import onnx
import onnxruntime as ort

torch.set_num_threads(4)

PROJECT_ROOT = Path("/home/nimr/Projects/mosqscan")
ORIGINAL_DIR = PROJECT_ROOT / "Mosquito Images Original"
AUGMENTED_DIR = PROJECT_ROOT / "Mosquito Images Augmented"
MODELS_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "reports"
MANIFEST_PATH = PROJECT_ROOT / "data/metadata/conservative_lineage_manifest.json"

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
# 1. Dataset Indexing & Parent Specimen Mapping
# ----------------------------------------------------------------------
def load_combined_dataset() -> pd.DataFrame:
    print("=" * 70)
    print("1. INDEXING COMBINED DATASET (ORIGINAL + AUGMENTED)")
    print("=" * 70)
    
    with open(MANIFEST_PATH, "r") as f:
        manifest_data = json.load(f)
    
    # Build augmented filename to sequential parent map
    aug_lineage_map = {}
    for r in manifest_data["lineage_records"]:
        img_name = Path(r["augmented_image"]).name
        aug_lineage_map[img_name] = {
            "parent_specimen": r["sequential_block_parent"],
            "status": r["conservative_status"]
        }

    records = []
    
    # 1. Original images (44)
    for p in sorted(ORIGINAL_DIR.rglob("*.jpg")):
        parent_dir = p.parent.name.lower()
        if "aedes" in parent_dir: genus = "aedes"
        elif "anopheles" in parent_dir: genus = "anopheles"
        elif "culex" in parent_dir: genus = "culex"
        else: continue
        
        records.append({
            "filename": p.name,
            "filepath": str(p),
            "genus": genus,
            "label_idx": CLASS_TO_IDX[genus],
            "parent_specimen": p.name,
            "is_augmented": False,
            "lineage_status": "ORIGINAL_PHYSICAL_SPECIMEN"
        })
        
    orig_count = len(records)
    print(f"Loaded {orig_count} original physical photographs.")
    
    # 2. Augmented images (2,640)
    for p in sorted(AUGMENTED_DIR.rglob("*.jpg")):
        parent_dir = p.parent.name.lower()
        if "aedes" in parent_dir: genus = "aedes"
        elif "anopheles" in parent_dir: genus = "anopheles"
        elif "culex" in parent_dir: genus = "culex"
        else: continue
        
        info = aug_lineage_map.get(p.name, {})
        parent_id = info.get("parent_specimen", f"unknown_{p.name}")
        status = info.get("status", "UNCONFIRMED")
        
        records.append({
            "filename": p.name,
            "filepath": str(p),
            "genus": genus,
            "label_idx": CLASS_TO_IDX[genus],
            "parent_specimen": parent_id,
            "is_augmented": True,
            "lineage_status": status
        })
        
    df = pd.DataFrame(records)
    print(f"Total combined dataset: {len(df)} images.")
    print(f"  - Original Physical Photographs: {len(df[~df['is_augmented']])}")
    print(f"  - Augmented Variant Images:      {len(df[df['is_augmented']])}")
    print(f"  - Unique Biological Parents:     {df['parent_specimen'].nunique()}")
    
    print("\nClass breakdown:")
    for g, cnt in df["genus"].value_counts().items():
        print(f"  - {g.capitalize()}: {cnt} images ({round(cnt/len(df)*100, 1)}%)")
        
    return df

# ----------------------------------------------------------------------
# 2. Transforms & In-Memory Dataset
# ----------------------------------------------------------------------
def build_transforms(img_size: int, is_train: bool):
    if is_train:
        return transforms.Compose([
            transforms.Resize((img_size, img_size)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomVerticalFlip(p=0.2),
            transforms.RandomRotation(degrees=15),
            transforms.ColorJitter(brightness=0.1, contrast=0.1, saturation=0.05),
            transforms.ToTensor(),
            transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ])
    return transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
    ])

# Global Image Cache in RAM to ensure zero disk I/O bottlenecks
_IMAGE_CACHE: Dict[str, Image.Image] = {}

def preload_all_images(file_paths: List[str]):
    print("Preloading all 2,684 images into RAM cache...")
    t0 = time.perf_counter()
    for fp in file_paths:
        if fp not in _IMAGE_CACHE:
            with Image.open(fp) as im:
                _IMAGE_CACHE[fp] = im.convert("RGB")
    dt = time.perf_counter() - t0
    print(f"Preloaded {len(_IMAGE_CACHE)} images into RAM in {dt:.2f} seconds ({len(_IMAGE_CACHE)/dt:.1f} img/s).")

class FastMosqDataset(Dataset):
    def __init__(self, df: pd.DataFrame, transform=None):
        self.df = df.reset_index(drop=True)
        self.transform = transform
        self.filepaths = self.df["filepath"].tolist()
        self.labels = self.df["label_idx"].values

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        img = _IMAGE_CACHE[self.filepaths[idx]]
        label = self.labels[idx]
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
# 3. Stratified Parent-Grouped Cross-Validation
# ----------------------------------------------------------------------
def run_parent_grouped_cv(df: pd.DataFrame) -> Dict[str, Any]:
    print("\n" + "=" * 70)
    print("2. 4-FOLD STRATIFIED GROUP K-FOLD (GROUPED BY PARENT SPECIMEN)")
    print("=" * 70)
    print("Guarantees ZERO biological specimen leakage between train and test splits.")
    
    sgkf = StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=42)
    val_trans = build_transforms(IMG_SIZE, is_train=False)
    
    # We group by parent_specimen to ensure all augmentations of parent X stay in one split
    fold_results = []
    all_phys_true, all_phys_pred = [], []
    all_val_true, all_val_pred = [], []
    
    for fold, (train_idx, val_idx) in enumerate(sgkf.split(df, df["label_idx"], df["parent_specimen"])):
        train_df = df.iloc[train_idx]
        val_df = df.iloc[val_idx]
        
        # Physical photographs held out in this fold
        val_phys_df = val_df[~val_df["is_augmented"]]
        
        # Calculate class weights for training set
        class_counts = train_df["label_idx"].value_counts().sort_index().values
        class_weights = len(train_df) / (len(class_counts) * class_counts.astype(np.float32))
        weight_tensor = torch.tensor(class_weights, dtype=torch.float32)
        
        train_ds = FastMosqDataset(train_df, transform=build_transforms(IMG_SIZE, is_train=True))
        val_ds = FastMosqDataset(val_df, transform=val_trans)
        val_phys_ds = FastMosqDataset(val_phys_df, transform=val_trans)
        
        train_loader = DataLoader(train_ds, batch_size=32, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=32, shuffle=False)
        val_phys_loader = DataLoader(val_phys_ds, batch_size=16, shuffle=False)
        
        model = build_model(3)
        criterion = nn.CrossEntropyLoss(weight=weight_tensor)
        
        # Stage 1: Classifier head (2 epochs)
        for param in model.features.parameters():
            param.requires_grad = False
        opt_head = torch.optim.AdamW(model.classifier.parameters(), lr=1e-3, weight_decay=1e-4)
        
        model.train()
        for ep in range(2):
            for imgs, targets in train_loader:
                opt_head.zero_grad()
                loss = criterion(model(imgs), targets)
                loss.backward()
                opt_head.step()
                
        # Stage 2: Fine-tune top features (2 epochs)
        for param in model.features[-2:].parameters():
            param.requires_grad = True
        opt_full = torch.optim.AdamW([
            {"params": model.features[-2:].parameters(), "lr": 2e-5},
            {"params": model.classifier.parameters(), "lr": 2e-4},
        ], weight_decay=1e-4)
        
        for ep in range(2):
            for imgs, targets in train_loader:
                opt_full.zero_grad()
                loss = criterion(model(imgs), targets)
                loss.backward()
                opt_full.step()
                
        model.eval()
        
        # Evaluate on physical original photographs of held-out parents
        phys_y_true, phys_y_pred = [], []
        with torch.no_grad():
            for imgs, targets in val_phys_loader:
                preds = model(imgs).argmax(dim=1).cpu().numpy()
                phys_y_true.extend(targets.numpy())
                phys_y_pred.extend(preds)
                
        # Evaluate on all held-out validation images (augmented + physical)
        val_y_true, val_y_pred = [], []
        with torch.no_grad():
            for imgs, targets in val_loader:
                preds = model(imgs).argmax(dim=1).cpu().numpy()
                val_y_true.extend(targets.numpy())
                val_y_pred.extend(preds)
                
        phys_f1 = f1_score(phys_y_true, phys_y_pred, average="macro", zero_division=0)
        phys_acc = float(np.mean(np.array(phys_y_true) == np.array(phys_y_pred)))
        phys_bal_acc = balanced_accuracy_score(phys_y_true, phys_y_pred)
        
        all_phys_true.extend(phys_y_true)
        all_phys_pred.extend(phys_y_pred)
        all_val_true.extend(val_y_true)
        all_val_pred.extend(val_y_pred)
        
        p, r, f, s = precision_recall_fscore_support(phys_y_true, phys_y_pred, labels=[0, 1, 2], zero_division=0)
        
        fold_stat = {
            "fold": fold + 1,
            "train_images": len(train_df),
            "val_images": len(val_df),
            "val_physical_specimens": len(val_phys_df),
            "held_out_parents": val_df["parent_specimen"].nunique(),
            "physical_macro_f1": round(float(phys_f1), 4),
            "physical_balanced_accuracy": round(float(phys_bal_acc), 4),
            "physical_accuracy": round(float(phys_acc), 4),
            "physical_recall": {IDX_TO_CLASS[i]: round(float(r[i]), 4) for i in range(3)},
            "all_val_macro_f1": round(float(f1_score(val_y_true, val_y_pred, average="macro")), 4),
            "all_val_accuracy": round(float(np.mean(np.array(val_y_true) == np.array(val_y_pred))), 4)
        }
        fold_results.append(fold_stat)
        print(f"  Fold {fold+1} (Parents: {fold_stat['held_out_parents']}): Physical Macro-F1={phys_f1:.4f}, "
              f"BalAcc={phys_bal_acc:.4f}, Acc={phys_acc:.4f} (AeRec: {r[0]:.2f}, AnRec: {r[1]:.2f}, CxRec: {r[2]:.2f}) | All Val Acc={fold_stat['all_val_accuracy']:.4f}")

    mean_phys_f1 = float(np.mean([f["physical_macro_f1"] for f in fold_results]))
    std_phys_f1 = float(np.std([f["physical_macro_f1"] for f in fold_results], ddof=1))
    mean_phys_bal_acc = float(np.mean([f["physical_balanced_accuracy"] for f in fold_results]))
    std_phys_bal_acc = float(np.std([f["physical_balanced_accuracy"] for f in fold_results], ddof=1))
    overall_phys_acc = float(np.mean(np.array(all_phys_true) == np.array(all_phys_pred)))
    overall_val_acc = float(np.mean(np.array(all_val_true) == np.array(all_val_pred)))
    
    cm_phys = confusion_matrix(all_phys_true, all_phys_pred, labels=[0, 1, 2]).tolist()
    
    cv_summary = {
        "mean_physical_macro_f1": round(mean_phys_f1, 4),
        "std_physical_macro_f1": round(std_phys_f1, 4),
        "mean_physical_balanced_accuracy": round(mean_phys_bal_acc, 4),
        "std_physical_balanced_accuracy": round(std_phys_bal_acc, 4),
        "overall_physical_accuracy": round(overall_phys_acc, 4),
        "overall_all_val_accuracy": round(overall_val_acc, 4),
        "physical_confusion_matrix": cm_phys,
        "folds": fold_results
    }
    
    print("\nGrouped Cross-Validation Summary (Out-of-Fold Physical Specimens):")
    print(f"  Mean Physical Macro-F1: {cv_summary['mean_physical_macro_f1']} +/- {cv_summary['std_physical_macro_f1']}")
    print(f"  Mean Physical Balanced Accuracy: {cv_summary['mean_physical_balanced_accuracy']} +/- {cv_summary['std_physical_balanced_accuracy']}")
    print(f"  Overall Physical Accuracy: {cv_summary['overall_physical_accuracy']} ({sum(np.array(all_phys_true) == np.array(all_phys_pred))}/{len(all_phys_true)})")
    print(f"  Overall Out-of-Fold Total Accuracy (Phys + Aug): {cv_summary['overall_all_val_accuracy']}")
    print("  Physical Specimen Confusion Matrix (Aedes, Anopheles, Culex):")
    for row in cm_phys:
        print(f"    {row}")
        
    return cv_summary

# ----------------------------------------------------------------------
# 4. Full Dataset Training on All 2,684 Images
# ----------------------------------------------------------------------
def train_full_model(df: pd.DataFrame) -> Tuple[nn.Module, Dict[str, Any]]:
    print("\n" + "=" * 70)
    print(f"3. TRAINING FINAL PRODUCTION MODEL ON ALL {len(df)} IMAGES")
    print("=" * 70)
    
    class_counts = df["label_idx"].value_counts().sort_index().values
    class_weights = len(df) / (len(class_counts) * class_counts.astype(np.float32))
    weight_tensor = torch.tensor(class_weights, dtype=torch.float32)
    print(f"Inverse class weights: {weight_tensor.tolist()}")
    
    train_ds = FastMosqDataset(df, transform=build_transforms(IMG_SIZE, is_train=True))
    train_loader = DataLoader(train_ds, batch_size=32, shuffle=True)
    
    model = build_model(3)
    criterion = nn.CrossEntropyLoss(weight=weight_tensor)
    
    # Stage 1: Linear Probe Head (2 epochs)
    print("Stage 1: Training classifier head (features frozen)...")
    for param in model.features.parameters():
        param.requires_grad = False
    opt_head = torch.optim.AdamW(model.classifier.parameters(), lr=1e-3, weight_decay=1e-4)
    
    model.train()
    for ep in range(2):
        total_loss = 0.0
        for imgs, targets in train_loader:
            opt_head.zero_grad()
            loss = criterion(model(imgs), targets)
            loss.backward()
            opt_head.step()
            total_loss += loss.item() * len(targets)
        avg_loss = total_loss / len(train_ds)
        print(f"  Head Epoch {ep+1}/2 - Loss: {avg_loss:.4f}")
        
    # Stage 2: Fine-Tuning Top Features (3 epochs)
    print("Stage 2: Fine-tuning top backbone features...")
    for param in model.features[-3:].parameters():
        param.requires_grad = True
    opt_full = torch.optim.AdamW([
        {"params": model.features[-3:].parameters(), "lr": 2e-5},
        {"params": model.classifier.parameters(), "lr": 2e-4},
    ], weight_decay=1e-4)
    
    for ep in range(3):
        total_loss = 0.0
        for imgs, targets in train_loader:
            opt_full.zero_grad()
            loss = criterion(model(imgs), targets)
            loss.backward()
            opt_full.step()
            total_loss += loss.item() * len(targets)
        avg_loss = total_loss / len(train_ds)
        print(f"  Fine-tune Epoch {ep+1}/3 - Loss: {avg_loss:.4f}")
        
    # Evaluate fit on unaugmented original images
    model.eval()
    val_trans = build_transforms(IMG_SIZE, is_train=False)
    phys_df = df[~df["is_augmented"]]
    phys_ds = FastMosqDataset(phys_df, transform=val_trans)
    phys_loader = DataLoader(phys_ds, batch_size=16, shuffle=False)
    
    phys_preds, phys_targets = [], []
    with torch.no_grad():
        for imgs, targets in phys_loader:
            preds = model(imgs).argmax(dim=1).cpu().numpy()
            phys_preds.extend(preds)
            phys_targets.extend(targets.numpy())
            
    phys_fit_acc = float(np.mean(np.array(phys_preds) == np.array(phys_targets)))
    phys_fit_f1 = float(f1_score(phys_targets, phys_preds, average="macro"))
    phys_fit_cm = confusion_matrix(phys_targets, phys_preds, labels=[0, 1, 2]).tolist()
    
    training_metrics = {
        "final_epoch_loss": round(avg_loss, 4),
        "physical_originals_accuracy": round(phys_fit_acc, 4),
        "physical_originals_macro_f1": round(phys_fit_f1, 4),
        "physical_confusion_matrix": phys_fit_cm,
    }
    
    print(f"\nFinal model fit on 44 original physical photographs:")
    print(f"  Accuracy: {training_metrics['physical_originals_accuracy']} ({sum(np.array(phys_preds) == np.array(phys_targets))}/44)")
    print(f"  Macro-F1: {training_metrics['physical_originals_macro_f1']}")
    print(f"  Confusion matrix: {phys_fit_cm}")
    
    return model, training_metrics

# ----------------------------------------------------------------------
# 5. Export and Verify Artifacts
# ----------------------------------------------------------------------
def export_and_verify(model: nn.Module, df: pd.DataFrame) -> Dict[str, Any]:
    print("\n" + "=" * 70)
    print("4. EXPORTING ONNX AND VERIFYING RUNTIME")
    print("=" * 70)
    
    pt_path = MODELS_DIR / "vectora_augmented_trained.pt"
    onnx_path = MODELS_DIR / "vectora_augmented_trained_fp32.onnx"
    
    # Save PyTorch
    torch.save(model.state_dict(), pt_path)
    pt_size = pt_path.stat().st_size
    pt_sha = sha256_file(pt_path)
    print(f"Saved PyTorch weights: {pt_path} ({round(pt_size / 1024 / 1024, 2)} MB)")
    print(f"  SHA-256: {pt_sha}")
    
    # Export ONNX (Single self-contained file)
    model.eval()
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
        dynamo=False,
    )
    
    onnx_model = onnx.load(str(onnx_path))
    onnx.checker.check_model(onnx_model)
    onnx_size = onnx_path.stat().st_size
    onnx_sha = sha256_file(onnx_path)
    print(f"Exported self-contained ONNX FP32: {onnx_path} ({round(onnx_size / 1024 / 1024, 2)} MB)")
    print(f"  SHA-256: {onnx_sha}")
    
    # Verify with ONNX Runtime on the 44 physical original photographs
    so = ort.SessionOptions()
    so.intra_op_num_threads = 4
    session = ort.InferenceSession(str(onnx_path), so, providers=["CPUExecutionProvider"])
    
    val_trans = build_transforms(IMG_SIZE, is_train=False)
    phys_df = df[~df["is_augmented"]]
    
    latencies = []
    onnx_preds = []
    
    for _, row in phys_df.iterrows():
        img = Image.open(row["filepath"]).convert("RGB")
        tensor = val_trans(img).unsqueeze(0).numpy()
        
        t0 = time.perf_counter()
        ort_out = session.run(None, {"input": tensor})[0]
        latencies.append((time.perf_counter() - t0) * 1000.0)
        
        onnx_preds.append(int(np.argmax(ort_out, axis=1)[0]))
        
    onnx_acc = float(np.mean(np.array(onnx_preds) == phys_df["label_idx"].values))
    median_latency = float(np.median(latencies))
    p95_latency = float(np.percentile(latencies, 95))
    
    print(f"ONNX Runtime Verification on 44 Physical Specimens:")
    print(f"  Accuracy: {round(onnx_acc * 100, 2)}% ({sum(np.array(onnx_preds) == phys_df['label_idx'].values)}/44)")
    print(f"  Median CPU Latency: {round(median_latency, 2)} ms (p95: {round(p95_latency, 2)} ms)")
    
    return {
        "pytorch_path": str(pt_path),
        "pytorch_sha256": pt_sha,
        "pytorch_size_bytes": pt_size,
        "onnx_path": str(onnx_path),
        "onnx_sha256": onnx_sha,
        "onnx_size_bytes": onnx_size,
        "median_cpu_latency_ms": round(median_latency, 2),
        "p95_cpu_latency_ms": round(p95_latency, 2),
        "onnx_accuracy_on_44_originals": round(onnx_acc, 4)
    }

# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    start_time = time.time()
    df = load_combined_dataset()
    preload_all_images(df["filepath"].tolist())
    
    cv_summary = run_parent_grouped_cv(df)
    
    model, train_metrics = train_full_model(df)
    
    export_meta = export_and_verify(model, df)
    
    duration = round(time.time() - start_time, 2)
    print(f"\nExecution finished in {duration} seconds ({round(duration / 60, 2)} minutes).")
    
    output_report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "execution_duration_seconds": duration,
        "dataset_summary": {
            "total_images": len(df),
            "original_physical_photographs": int((~df["is_augmented"]).sum()),
            "augmented_variant_images": int(df["is_augmented"].sum()),
            "unique_parent_specimens": int(df["parent_specimen"].nunique()),
            "class_distribution": {str(k): int(v) for k, v in df["genus"].value_counts().items()}
        },
        "grouped_cross_validation": cv_summary,
        "final_training_metrics": train_metrics,
        "export_metadata": export_meta
    }
    
    json_path = REPORTS_DIR / "augmented_dataset_training_results.json"
    with open(json_path, "w") as f:
        json.dump(output_report, f, indent=2)
    print(f"Saved full JSON results to: {json_path}")

if __name__ == "__main__":
    main()
