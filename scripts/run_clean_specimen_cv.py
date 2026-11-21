#!/usr/bin/env python3
"""
Vectora AI 3.1: Clean Specimen-Level Cross-Validation with Dynamic Augmentation
ASD-STE100 Compliant Implementation.

Scientific Validation Guarantees:
1. Training and validation splits use ONLY the 44 verified original biological specimens.
2. StratifiedGroupKFold splits groups strictly by physical specimen ID.
3. Augmentations are generated DYNAMICALLY on the training set only.
4. Validation specimens are 100% untouched original photographs (zero augmentations).
5. Precomputed augmented ZIP is quarantined as a separate stress test dataset.
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
from sklearn.metrics import classification_report, confusion_matrix, balanced_accuracy_score, f1_score
from sklearn.model_selection import StratifiedGroupKFold
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights

torch.set_num_threads(4)

CLASSES = ["aedes", "anopheles", "culex"]
CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}
IDX_TO_CLASS = {i: c for i, c in enumerate(CLASSES)}

PROJECT_ROOT = "/home/nimr/Projects/mosqscan"
METADATA_DIR = os.path.join(PROJECT_ROOT, "data/metadata")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")

_IMAGE_CACHE: Dict[str, Image.Image] = {}

def get_cached_image(path: str) -> Image.Image:
    if path not in _IMAGE_CACHE:
        with Image.open(path) as im:
            _IMAGE_CACHE[path] = im.convert("RGB")
    return _IMAGE_CACHE[path]

def get_peak_ram_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0

def build_transforms(img_size: int, train: bool):
    if train:
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

class CleanMosqDataset(Dataset):
    """
    Dataset that dynamically expands training specimens with augmentations on the fly.
    Validation specimens are never augmented.
    """
    def __init__(self, df: pd.DataFrame, transform=None, samples_per_specimen: int = 1):
        self.df = df.reset_index(drop=True)
        self.transform = transform
        self.samples_per_specimen = samples_per_specimen

    def __len__(self):
        return len(self.df) * self.samples_per_specimen

    def __getitem__(self, idx):
        row_idx = idx % len(self.df)
        row = self.df.iloc[row_idx]
        img = get_cached_image(row["file_path"])
        if self.transform:
            img = self.transform(img)
        label = CLASS_TO_IDX[row["genus"].lower()]
        return img, label

def create_model():
    m = efficientnet_b0(weights=EfficientNet_B0_Weights.DEFAULT)
    in_feat = m.classifier[1].in_features
    m.classifier[1] = nn.Linear(in_feat, 3)
    return m

def freeze_backbone(model):
    for p in model.parameters():
        p.requires_grad = False
    for p in model.classifier.parameters():
        p.requires_grad = True

def unfreeze_top_layers(model):
    for p in model.parameters():
        p.requires_grad = False
    for p in model.features[7].parameters():
        p.requires_grad = True
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
    y_true, y_pred, y_probs = [], [], []
    with torch.no_grad():
        for imgs, labels in loader:
            logits = model(imgs)
            probs = torch.softmax(logits, dim=1)
            preds = logits.argmax(dim=1)
            y_true.extend(labels.tolist())
            y_pred.extend(preds.tolist())
            y_probs.extend(probs.tolist())
            
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
        "y_true": y_true,
        "y_pred": y_pred,
        "y_probs": [[round(p, 4) for p in row] for row in y_probs]
    }

def run_clean_cv():
    manifest_df = pd.read_json(os.path.join(METADATA_DIR, "dataset_manifest.json"))
    orig_df = manifest_df[manifest_df["dataset_type"] == "original"].copy().reset_index(drop=True)
    
    print("=" * 70, flush=True)
    print("VECTORA AI 3.1: CLEAN SPECIMEN-LEVEL CROSS-VALIDATION", flush=True)
    print(f"Total Original Biological Specimens: {len(orig_df)}", flush=True)
    print(f"Class Breakdown: Aedes={len(orig_df[orig_df['genus'].str.lower()=='aedes'])}, Anopheles={len(orig_df[orig_df['genus'].str.lower()=='anopheles'])}, Culex={len(orig_df[orig_df['genus'].str.lower()=='culex'])}", flush=True)
    print("Zero Precomputed Augmentation Images Injected.", flush=True)
    print("Validation Sets are 100% Untouched Physical Photographs.", flush=True)
    print("=" * 70, flush=True)
    
    for p in orig_df["file_path"]:
        get_cached_image(p)
    print(f"Pre-cached all {len(_IMAGE_CACHE)} original specimens in memory.", flush=True)
    
    seeds = [42, 1337]
    all_fold_records = []
    img_size = 224
    batch_size = 8
    dynamic_multiplier = 3  # 1 original + 2 dynamic augmentations = 3 views per specimen (99 train images)
    epochs_stage1 = 1
    epochs_stage2 = 1
    
    for seed in seeds:
        sgkf = StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=seed)
        # Groups are unique physical specimen IDs (1 group per specimen)
        groups = orig_df["specimen_id"].values
        y_labels = orig_df["genus"].values
        
        for fold, (train_idx, val_idx) in enumerate(sgkf.split(orig_df, y_labels, groups)):
            t0 = time.time()
            train_df = orig_df.iloc[train_idx].copy()
            val_df = orig_df.iloc[val_idx].copy()
            
            # Verify ZERO specimen overlap
            overlap = set(train_df["specimen_id"]).intersection(set(val_df["specimen_id"]))
            assert len(overlap) == 0, f"LEAKAGE DETECTED: {overlap}"
            
            # Dynamic augmentation on training only
            train_ds = CleanMosqDataset(
                train_df,
                transform=build_transforms(img_size, train=True),
                samples_per_specimen=dynamic_multiplier
            )
            # Pure clean validation set
            val_ds = CleanMosqDataset(
                val_df,
                transform=build_transforms(img_size, train=False),
                samples_per_specimen=1
            )
            
            train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, drop_last=False)
            val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)
            
            model = create_model()
            weights = compute_weights(train_df)
            criterion = nn.CrossEntropyLoss(weight=weights)
            
            # Stage 1: Classifier head
            freeze_backbone(model)
            opt_head = torch.optim.AdamW(
                [p for p in model.parameters() if p.requires_grad],
                lr=0.001, weight_decay=1e-4
            )
            model.train()
            for ep in range(epochs_stage1):
                for imgs, labels in train_loader:
                    opt_head.zero_grad()
                    out = model(imgs)
                    loss = criterion(out, labels)
                    loss.backward()
                    opt_head.step()
                    
            # Stage 2: Top layers fine-tune
            unfreeze_top_layers(model)
            opt_finetune = torch.optim.AdamW([
                {"params": [p for p in model.features.parameters() if p.requires_grad], "lr": 0.00002},
                {"params": [p for p in model.classifier.parameters() if p.requires_grad], "lr": 0.0002},
            ], weight_decay=1e-4)
            model.train()
            for ep in range(epochs_stage2):
                for imgs, labels in train_loader:
                    opt_finetune.zero_grad()
                    out = model(imgs)
                    loss = criterion(out, labels)
                    loss.backward()
                    opt_finetune.step()
                    
            eval_metrics = evaluate_loader(model, val_loader)
            duration = round(time.time() - t0, 1)
            eval_metrics["seed"] = seed
            eval_metrics["fold"] = fold
            eval_metrics["train_specimens"] = len(train_df)
            eval_metrics["val_specimens"] = len(val_df)
            eval_metrics["val_specimen_ids"] = val_df["specimen_id"].tolist()
            eval_metrics["duration_seconds"] = duration
            all_fold_records.append(eval_metrics)
            
            val_supports = {c: eval_metrics["per_class"][c]["support"] for c in CLASSES}
            print(f"Seed {seed} Fold {fold}: Macro-F1={eval_metrics['macro_f1']:.4f}, BalAcc={eval_metrics['balanced_accuracy']:.4f}, AnophRecall={eval_metrics['per_class']['anopheles']['recall']:.4f}, ValSupport={val_supports} ({duration}s)", flush=True)

    # Statistical aggregation
    f1s = [f["macro_f1"] for f in all_fold_records]
    baccs = [f["balanced_accuracy"] for f in all_fold_records]
    accs = [f["accuracy"] for f in all_fold_records]
    aedes_recalls = [f["per_class"]["aedes"]["recall"] for f in all_fold_records]
    anoph_recalls = [f["per_class"]["anopheles"]["recall"] for f in all_fold_records]
    culex_recalls = [f["per_class"]["culex"]["recall"] for f in all_fold_records]
    
    mean_f1 = float(np.mean(f1s))
    sample_std_f1 = float(np.std(f1s, ddof=1))
    pop_std_f1 = float(np.std(f1s, ddof=0))
    mean_bacc = float(np.mean(baccs))
    sample_std_bacc = float(np.std(baccs, ddof=1))
    mean_acc = float(np.mean(accs))
    
    mean_aedes_rec = float(np.mean(aedes_recalls))
    mean_anoph_rec = float(np.mean(anoph_recalls))
    mean_culex_rec = float(np.mean(culex_recalls))
    
    # Cumulative confusion matrix
    total_cm = np.zeros((3, 3), dtype=int)
    for f in all_fold_records:
        total_cm += np.array(f["confusion_matrix"])
        
    results = {
        "experiment": "v3_1_clean_specimen_cv",
        "description": "StratifiedGroupKFold on 44 original biological specimens only, dynamic training augmentations, clean untouched validation specimens.",
        "model_architecture": "efficientnet_b0",
        "input_resolution": 224,
        "total_folds_evaluated": len(all_fold_records),
        "seeds": seeds,
        "prd_macro_f1_target": 0.9200,
        "mean_macro_f1": round(mean_f1, 4),
        "sample_std_macro_f1": round(sample_std_f1, 4),
        "pop_std_macro_f1": round(pop_std_f1, 4),
        "prd_macro_f1_gap_percentage_points": round((0.9200 - mean_f1) * 100, 2),
        "mean_balanced_accuracy": round(mean_bacc, 4),
        "sample_std_balanced_accuracy": round(sample_std_bacc, 4),
        "mean_overall_accuracy": round(mean_acc, 4),
        "per_class_mean_recall": {
            "aedes": round(mean_aedes_rec, 4),
            "anopheles": round(mean_anoph_rec, 4),
            "culex": round(mean_culex_rec, 4),
        },
        "cumulative_confusion_matrix": total_cm.tolist(),
        "folds": all_fold_records
    }
    
    out_file = os.path.join(REPORTS_DIR, "v3_1_cv_clean_results.json")
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
        
    print("\n" + "=" * 70, flush=True)
    print("VECTORA AI 3.1: CLEAN CV SUMMARY", flush=True)
    print(f"Mean Macro-F1:            {mean_f1:.4f} ± {sample_std_f1:.4f} (sample) / {pop_std_f1:.4f} (pop)", flush=True)
    print(f"PRD Target (Macro-F1):    0.9200 (Gap: {results['prd_macro_f1_gap_percentage_points']:.2f} percentage points)", flush=True)
    print(f"Mean Balanced Accuracy:   {mean_bacc:.4f} ± {sample_std_bacc:.4f}", flush=True)
    print(f"Per-Class Mean Recall:    Aedes={mean_aedes_rec:.4f}, Anopheles={mean_anoph_rec:.4f}, Culex={mean_culex_rec:.4f}", flush=True)
    print(f"Cumulative Confusion Matrix (Aedes, Anoph, Culex):\n{total_cm}", flush=True)
    print(f"Results saved to: {out_file}", flush=True)
    print("=" * 70, flush=True)

if __name__ == "__main__":
    run_clean_cv()
