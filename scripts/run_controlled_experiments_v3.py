#!/usr/bin/env python3
"""
Vectora AI: Controlled Combined Dataset Experiments (Exp A, Exp B, Exp C)
ASD-STE100 Compliant Implementation.

Hardware Constraints:
- Intel Core i7-2600 (4 cores / 8 threads, AVX, no AVX2), 16 GB RAM.
- CPU threads: 3.
- Batch size: 4.
- Workers: 0 (in-memory cache).
- Image size: 224x224.

Experiments:
- Exp A: Original images with online dynamic augmentation.
- Exp B: Original images plus verified precomputed augmentations (unweighted).
- Exp C: Combined training with class-weighted loss and online augmentation.

Safety Guarantees:
- Partitions grouped strictly by original physical specimen ID (44 biological parents).
- 215 unconfirmed augmentations and 180 ambiguous sibling mismatches are strictly excluded.
- Validation and test specimens are 100% untouched physical photographs (zero augmentations).
- Active server model (vectora_v3_fp32.onnx) is preserved untouched.
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
import urllib.request
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

# Set CPU threading constraint to 3
torch.set_num_threads(3)

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
BATCH_SIZE = 4

def get_peak_ram_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0

def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def check_host_server_latency() -> float:
    try:
        t0 = time.perf_counter()
        req = urllib.request.Request("http://localhost:8000/api/v1/models/health")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            dt = (time.perf_counter() - t0) * 1000.0
            if resp.status == 200:
                return round(dt, 2)
        return -1.0
    except Exception:
        return -1.0

# ----------------------------------------------------------------------
# 1. Dataset Indexing & Strict Exclusion of Unconfirmed Augmentations
# ----------------------------------------------------------------------
_IMAGE_CACHE: Dict[str, Image.Image] = {}

def get_cached_image(path: str) -> Image.Image:
    if path not in _IMAGE_CACHE:
        with Image.open(path) as im:
            _IMAGE_CACHE[path] = im.convert("RGB")
    return _IMAGE_CACHE[path]

def load_and_audit_dataset() -> Tuple[pd.DataFrame, Dict[str, Any]]:
    print("=" * 70)
    print("1. LOADING AND AUDITING DATASET (STRICT EXCLUSION)")
    print("=" * 70)
    
    with open(MANIFEST_PATH, "r") as f:
        manifest_data = json.load(f)
        
    lineage_records = manifest_data["lineage_records"]
    
    # Audit counts
    total_augmented = len(lineage_records)
    verified_map = {}
    excluded_counts = {"UNCONFIRMED_LOW_CONFIDENCE": 0, "AMBIGUOUS_SIBLING_DISCORDANT": 0}
    
    for r in lineage_records:
        status = r["conservative_status"]
        img_name = Path(r["augmented_image"]).name
        if status == "VERIFIED_BLOCK_CONCORDANT":
            verified_map[img_name] = r["sequential_block_parent"]
        else:
            if status in excluded_counts:
                excluded_counts[status] += 1
            else:
                excluded_counts[status] = 1
                
    print(f"Total precomputed augmented images: {total_augmented}")
    print(f"  - Verified Block-Concordant (Included): {len(verified_map)}")
    print(f"  - Excluded (Unconfirmed Low Confidence): {excluded_counts['UNCONFIRMED_LOW_CONFIDENCE']}")
    print(f"  - Excluded (Ambiguous Sibling Discordant): {excluded_counts['AMBIGUOUS_SIBLING_DISCORDANT']}")
    
    # Load 44 original photographs
    records = []
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
            "status": "ORIGINAL_PHYSICAL_SPECIMEN"
        })
    print(f"Loaded {len(records)} original physical photographs.")
    
    # Add verified augmented images only
    aug_included_count = 0
    for p in sorted(AUGMENTED_DIR.rglob("*.jpg")):
        if p.name in verified_map:
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
                "parent_specimen": verified_map[p.name],
                "is_augmented": True,
                "status": "VERIFIED_PRECOMPUTED_AUGMENTATION"
            })
            aug_included_count += 1
            
    df = pd.DataFrame(records)
    print(f"Total verified dataset: {len(df)} images.")
    print(f"  - Physical Specimens: 44")
    print(f"  - Precomputed Verified Augmentations: {aug_included_count}")
    print(f"  - Unique Biological Parents: {df['parent_specimen'].nunique()}")
    
    # Preload all into memory cache
    print("Preloading all verified images into RAM cache...")
    t0 = time.perf_counter()
    for fp in df["filepath"]:
        get_cached_image(fp)
    print(f"Preloaded {len(_IMAGE_CACHE)} images into RAM in {round(time.perf_counter() - t0, 2)}s.")
    
    audit_summary = {
        "original_photographs": 44,
        "total_augmented_images": total_augmented,
        "verified_augmented_included": aug_included_count,
        "unconfirmed_excluded": excluded_counts["UNCONFIRMED_LOW_CONFIDENCE"],
        "ambiguous_excluded": excluded_counts["AMBIGUOUS_SIBLING_DISCORDANT"],
        "total_verified_pool": len(df),
        "unique_biological_parents": 44,
        "verified_class_distribution": {k: int(v) for k, v in df["genus"].value_counts().items()},
    }
    return df, audit_summary

# ----------------------------------------------------------------------
# 2. Datasets, Transforms & Model
# ----------------------------------------------------------------------
def build_transforms(img_size: int, is_train: bool, online_augment: bool = False):
    if is_train and online_augment:
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

class MosqExpDataset(Dataset):
    def __init__(self, df: pd.DataFrame, transform=None, multiplier: int = 1):
        self.df = df.reset_index(drop=True)
        self.transform = transform
        self.multiplier = multiplier
        self.filepaths = self.df["filepath"].tolist()
        self.labels = self.df["label_idx"].values

    def __len__(self):
        return len(self.df) * self.multiplier

    def __getitem__(self, idx):
        base_idx = idx % len(self.df)
        img = get_cached_image(self.filepaths[base_idx])
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
# 3. Controlled Experiment Runner
# ----------------------------------------------------------------------
def run_controlled_experiment(
    exp_name: str,
    exp_desc: str,
    df: pd.DataFrame,
    partitions: List[Tuple[pd.DataFrame, pd.DataFrame]],
    use_precomputed_aug: bool,
    use_online_aug: bool,
    use_class_weighting: bool,
    online_multiplier: int = 1,
    epochs_head: int = 2,
    epochs_fine: int = 2,
) -> Dict[str, Any]:
    print("\n" + "=" * 70)
    print(f"RUNNING {exp_name.upper()}: {exp_desc}")
    print("=" * 70)
    
    val_trans = build_transforms(IMG_SIZE, is_train=False, online_augment=False)
    fold_stats = []
    all_y_true = []
    all_y_pred = []
    
    t_start = time.perf_counter()
    server_latencies = []
    
    for fold_idx, (train_full_df, val_phys_df) in enumerate(partitions):
        fold_t0 = time.perf_counter()
        
        # Filter training set based on experiment type
        if use_precomputed_aug:
            train_df = train_full_df.copy()
        else:
            train_df = train_full_df[~train_full_df["is_augmented"]].copy()
            
        # Class weighting
        if use_class_weighting:
            class_counts = train_df["label_idx"].value_counts().sort_index().values
            class_weights = len(train_df) / (len(class_counts) * class_counts.astype(np.float32))
            weight_tensor = torch.tensor(class_weights, dtype=torch.float32)
        else:
            weight_tensor = None
            
        train_trans = build_transforms(IMG_SIZE, is_train=True, online_augment=use_online_aug)
        train_ds = MosqExpDataset(train_df, transform=train_trans, multiplier=online_multiplier)
        val_ds = MosqExpDataset(val_phys_df, transform=val_trans, multiplier=1)
        
        train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
        val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
        
        model = build_model(3)
        criterion = nn.CrossEntropyLoss(weight=weight_tensor)
        
        # Check host server latency during training
        lat = check_host_server_latency()
        if lat > 0:
            server_latencies.append(lat)
            
        # Stage 1: Linear Probe Head
        for param in model.features.parameters():
            param.requires_grad = False
        opt_head = torch.optim.AdamW(model.classifier.parameters(), lr=1e-3, weight_decay=1e-4)
        
        model.train()
        for ep in range(epochs_head):
            for imgs, targets in train_loader:
                opt_head.zero_grad()
                loss = criterion(model(imgs), targets)
                loss.backward()
                opt_head.step()
                
        # Stage 2: Fine-Tuning Top 2 Blocks
        for param in model.features[-2:].parameters():
            param.requires_grad = True
        opt_full = torch.optim.AdamW([
            {"params": model.features[-2:].parameters(), "lr": 2e-5},
            {"params": model.classifier.parameters(), "lr": 2e-4},
        ], weight_decay=1e-4)
        
        for ep in range(epochs_fine):
            for imgs, targets in train_loader:
                opt_full.zero_grad()
                loss = criterion(model(imgs), targets)
                loss.backward()
                opt_full.step()
                
        # Evaluate on untouched physical validation specimens
        model.eval()
        fold_y_true = []
        fold_y_pred = []
        val_losses = []
        
        eval_criterion = nn.CrossEntropyLoss()
        with torch.no_grad():
            for imgs, targets in val_loader:
                outputs = model(imgs)
                v_loss = eval_criterion(outputs, targets)
                val_losses.append(v_loss.item())
                preds = outputs.argmax(dim=1).cpu().numpy()
                fold_y_true.extend(targets.numpy())
                fold_y_pred.extend(preds)
                
        macro_f1 = f1_score(fold_y_true, fold_y_pred, average="macro", zero_division=0)
        bal_acc = balanced_accuracy_score(fold_y_true, fold_y_pred)
        acc = float(np.mean(np.array(fold_y_true) == np.array(fold_y_pred)))
        mean_val_loss = float(np.mean(val_losses))
        
        all_y_true.extend(fold_y_true)
        all_y_pred.extend(fold_y_pred)
        
        p, r, f, s = precision_recall_fscore_support(fold_y_true, fold_y_pred, labels=[0, 1, 2], zero_division=0)
        fold_duration = round(time.perf_counter() - fold_t0, 1)
        
        stat = {
            "fold": fold_idx + 1,
            "train_images": len(train_df) * online_multiplier,
            "train_specimens": train_df["parent_specimen"].nunique(),
            "val_specimens": len(val_phys_df),
            "macro_f1": round(float(macro_f1), 4),
            "balanced_accuracy": round(float(bal_acc), 4),
            "accuracy": round(float(acc), 4),
            "val_loss": round(mean_val_loss, 4),
            "aedes_recall": round(float(r[0]), 4),
            "anopheles_recall": round(float(r[1]), 4),
            "culex_recall": round(float(r[2]), 4),
            "fold_duration_seconds": fold_duration,
        }
        fold_stats.append(stat)
        print(f"  Fold {fold_idx+1} ({fold_duration}s): Macro-F1={stat['macro_f1']:.4f}, BalAcc={stat['balanced_accuracy']:.4f}, "
              f"AeRec={stat['aedes_recall']:.2f}, AnRec={stat['anopheles_recall']:.2f}, CxRec={stat['culex_recall']:.2f}, ValLoss={stat['val_loss']:.4f}")

    total_duration = round(time.perf_counter() - t_start, 1)
    mean_f1 = float(np.mean([s["macro_f1"] for s in fold_stats]))
    std_f1 = float(np.std([s["macro_f1"] for s in fold_stats], ddof=1))
    pop_std_f1 = float(np.std([s["macro_f1"] for s in fold_stats], ddof=0))
    mean_bal_acc = float(np.mean([s["balanced_accuracy"] for s in fold_stats]))
    std_bal_acc = float(np.std([s["balanced_accuracy"] for s in fold_stats], ddof=1))
    overall_acc = float(np.mean(np.array(all_y_true) == np.array(all_y_pred)))
    mean_val_loss = float(np.mean([s["val_loss"] for s in fold_stats]))
    
    p_cum, r_cum, f_cum, _ = precision_recall_fscore_support(all_y_true, all_y_pred, labels=[0, 1, 2], zero_division=0)
    cm = confusion_matrix(all_y_true, all_y_pred, labels=[0, 1, 2]).tolist()
    peak_ram = get_peak_ram_mb()
    
    exp_summary = {
        "experiment_id": exp_name,
        "description": exp_desc,
        "total_specimens_evaluated": len(all_y_true),
        "mean_macro_f1": round(mean_f1, 4),
        "sample_std_macro_f1": round(std_f1, 4),
        "pop_std_macro_f1": round(pop_std_f1, 4),
        "mean_balanced_accuracy": round(mean_bal_acc, 4),
        "std_balanced_accuracy": round(std_bal_acc, 4),
        "overall_accuracy": round(overall_acc, 4),
        "mean_val_loss": round(mean_val_loss, 4),
        "aedes_recall": round(float(r_cum[0]), 4),
        "anopheles_recall": round(float(r_cum[1]), 4),
        "culex_recall": round(float(r_cum[2]), 4),
        "training_duration_seconds": total_duration,
        "peak_ram_mb": round(peak_ram, 2),
        "median_host_server_latency_ms": round(float(np.median(server_latencies)), 2) if server_latencies else None,
        "cumulative_confusion_matrix": cm,
        "folds": fold_stats,
    }
    
    print(f"\n{exp_name.upper()} RESULTS:")
    print(f"  Mean Macro-F1: {exp_summary['mean_macro_f1']} +/- {exp_summary['sample_std_macro_f1']}")
    print(f"  Mean Balanced Accuracy: {exp_summary['mean_balanced_accuracy']} +/- {exp_summary['std_balanced_accuracy']}")
    print(f"  Overall Accuracy: {exp_summary['overall_accuracy']} ({sum(np.array(all_y_true) == np.array(all_y_pred))}/44)")
    print(f"  Recall: Aedes={exp_summary['aedes_recall']}, Anopheles={exp_summary['anopheles_recall']}, Culex={exp_summary['culex_recall']}")
    print(f"  Duration: {total_duration}s | Peak RAM: {round(peak_ram, 1)} MB | Server Latency: {exp_summary['median_host_server_latency_ms']} ms")
    print(f"  Cumulative Confusion Matrix: {cm}")
    
    return exp_summary

# ----------------------------------------------------------------------
# Main Execution
# ----------------------------------------------------------------------
def main():
    print("VECTORA AI: CONTROLLED COMBINED DATASET TRAINING BENCHMARK")
    print(f"Host Hardware: Intel Core i7-2600 (Threads: 3, Batch: {BATCH_SIZE}, AVX CPU)")
    
    # Initial health check
    init_latency = check_host_server_latency()
    print(f"Initial Host Production Server Health Check Latency: {init_latency} ms\n")
    
    df, audit_summary = load_and_audit_dataset()
    
    # Create identical StratifiedGroupKFold partitions based on the 44 physical specimens
    sgkf = StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=42)
    partitions = []
    
    for train_idx, val_idx in sgkf.split(df, df["label_idx"], df["parent_specimen"]):
        train_full_df = df.iloc[train_idx].copy()
        val_full_df = df.iloc[val_idx].copy()
        # Validation is STRICTLY untouched physical photographs of held-out parents
        val_phys_df = val_full_df[~val_full_df["is_augmented"]].copy()
        partitions.append((train_full_df, val_phys_df))
        
    print(f"Generated {len(partitions)} identical StratifiedGroupKFold partitions (Seed 42).")
    for i, (tr, val) in enumerate(partitions):
        print(f"  Partition {i+1}: Train parents={tr['parent_specimen'].nunique()} (Images: {len(tr)}), Val parents={len(val)} (Physical: {len(val)})")
        
    # Run Experiment A
    exp_a = run_controlled_experiment(
        exp_name="Experiment A",
        exp_desc="Original images with online dynamic augmentation (unweighted)",
        df=df,
        partitions=partitions,
        use_precomputed_aug=False,
        use_online_aug=True,
        use_class_weighting=False,
        online_multiplier=4, # 33 * 4 = 132 images/epoch
        epochs_head=2,
        epochs_fine=2,
    )
    
    # Run Experiment B
    exp_b = run_controlled_experiment(
        exp_name="Experiment B",
        exp_desc="Original images plus verified precomputed augmentations (unweighted, no online aug)",
        df=df,
        partitions=partitions,
        use_precomputed_aug=True,
        use_online_aug=False,
        use_class_weighting=False,
        online_multiplier=1, # ~1,684 images/epoch
        epochs_head=1,
        epochs_fine=1,
    )
    
    # Run Experiment C
    exp_c = run_controlled_experiment(
        exp_name="Experiment C",
        exp_desc="Combined training with class-weighted loss and online dynamic augmentation",
        df=df,
        partitions=partitions,
        use_precomputed_aug=True,
        use_online_aug=True,
        use_class_weighting=True,
        online_multiplier=1, # ~1,684 images/epoch with transforms
        epochs_head=1,
        epochs_fine=1,
    )
    
    # Post-training health check
    final_latency = check_host_server_latency()
    print(f"\nFinal Host Production Server Health Check Latency: {final_latency} ms")
    
    results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hardware": {
            "cpu": "Intel Core i7-2600 @ 3.40GHz",
            "threads_assigned": 3,
            "batch_size": BATCH_SIZE,
            "image_size": IMG_SIZE,
            "ram_total_gb": 16,
            "initial_server_latency_ms": init_latency,
            "final_server_latency_ms": final_latency,
        },
        "audit_summary": audit_summary,
        "experiments": {
            "experiment_a": exp_a,
            "experiment_b": exp_b,
            "experiment_c": exp_c,
        }
    }
    
    json_path = REPORTS_DIR / "v3_combined_experiments.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved structured experimental results to: {json_path}")

if __name__ == "__main__":
    main()
