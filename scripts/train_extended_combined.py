#!/usr/bin/env python3
"""
Vectora AI: Extended Combined Dataset Training (Option 1)
8 Epochs Grouped Train/Val Fine-Tuning with Per-Epoch Physical Evaluation.
ASD-STE100 Compliant Implementation.

Hardware Constraints:
- Intel Core i7-2600 (3 threads, batch size 4, AVX, 16 GB RAM).
- Single training process, RAM preloaded images, workers=0.
- Continuous host production server health monitoring.

Dataset Guarantees:
- Strict exclusion of 215 unconfirmed and 180 ambiguous augmentations.
- Grouped 80/20 train/validation split by biological parent specimen ID.
- Validation on held-out physical specimens is 100% untouched photographs.
- Active server model (vectora_v3_fp32.onnx) preserved untouched.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import resource
import sys
import time
import urllib.request
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

# CPU threading constraint: 3 threads
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
# 1. Dataset Indexing & RAM Cache
# ----------------------------------------------------------------------
_IMAGE_CACHE: Dict[str, Image.Image] = {}

def get_cached_image(path: str) -> Image.Image:
    if path not in _IMAGE_CACHE:
        with Image.open(path) as im:
            _IMAGE_CACHE[path] = im.convert("RGB")
    return _IMAGE_CACHE[path]

def load_verified_dataset() -> pd.DataFrame:
    print("=" * 70)
    print("1. LOADING VERIFIED COMBINED DATASET (STRICT EXCLUSION)")
    print("=" * 70)
    
    with open(MANIFEST_PATH, "r") as f:
        manifest_data = json.load(f)
        
    lineage_records = manifest_data["lineage_records"]
    verified_map = {}
    for r in lineage_records:
        if r["conservative_status"] == "VERIFIED_BLOCK_CONCORDANT":
            img_name = Path(r["augmented_image"]).name
            verified_map[img_name] = r["sequential_block_parent"]
            
    records = []
    # 44 Original photographs
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
        })
        
    # 2,245 Verified block-concordant augmentations
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
            })
            
    df = pd.DataFrame(records)
    print(f"Loaded {len(df)} verified images across {df['parent_specimen'].nunique()} biological parent specimens.")
    print(f"  - Physical Photographs: {len(df[~df['is_augmented']])}")
    print(f"  - Verified Augmentations: {len(df[df['is_augmented']])}")
    
    # Preload all into RAM cache
    t0 = time.perf_counter()
    for fp in df["filepath"]:
        get_cached_image(fp)
    print(f"Preloaded {len(_IMAGE_CACHE)} images into RAM in {round(time.perf_counter() - t0, 2)}s.")
    return df

# ----------------------------------------------------------------------
# 2. Datasets & Transforms
# ----------------------------------------------------------------------
def build_transforms(img_size: int, is_train: bool):
    if is_train:
        return transforms.Compose([
            transforms.Resize((img_size, img_size)),
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

class MosqFastDataset(Dataset):
    def __init__(self, df: pd.DataFrame, transform=None):
        self.df = df.reset_index(drop=True)
        self.transform = transform
        self.filepaths = self.df["filepath"].tolist()
        self.labels = self.df["label_idx"].values

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        img = get_cached_image(self.filepaths[idx])
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
# 3. Extended Training Loop with Epoch Tracking
# ----------------------------------------------------------------------
def run_extended_training(df: pd.DataFrame) -> Tuple[nn.Module, Dict[str, Any]]:
    print("\n" + "=" * 70)
    print("2. EXECUTING EXTENDED COMBINED TRAINING (8 EPOCHS)")
    print("=" * 70)
    
    # 80/20 Grouped Split by parent specimen
    sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    train_idx, val_idx = next(sgkf.split(df, df["label_idx"], df["parent_specimen"]))
    
    train_df = df.iloc[train_idx].copy()
    val_full_df = df.iloc[val_idx].copy()
    val_phys_df = val_full_df[~val_full_df["is_augmented"]].copy()
    
    train_parents = train_df["parent_specimen"].nunique()
    val_parents = val_phys_df["parent_specimen"].nunique()
    print(f"Grouped Split: {train_parents} Training Parent Specimens ({len(train_df)} images)")
    print(f"               {val_parents} Validation Parent Specimens ({len(val_phys_df)} untouched physical photos, {len(val_full_df)} total)")
    
    # Class-weighted loss on training partition
    class_counts = train_df["label_idx"].value_counts().sort_index().values
    class_weights = len(train_df) / (len(class_counts) * class_counts.astype(np.float32))
    weight_tensor = torch.tensor(class_weights, dtype=torch.float32)
    print(f"Inverse class weights: {weight_tensor.tolist()}")
    
    train_ds = MosqFastDataset(train_df, transform=build_transforms(IMG_SIZE, is_train=True))
    val_phys_ds = MosqFastDataset(val_phys_df, transform=build_transforms(IMG_SIZE, is_train=False))
    val_full_ds = MosqFastDataset(val_full_df, transform=build_transforms(IMG_SIZE, is_train=False))
    
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    val_phys_loader = DataLoader(val_phys_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    val_full_loader = DataLoader(val_full_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    
    model = build_model(3)
    criterion = nn.CrossEntropyLoss(weight=weight_tensor)
    eval_criterion = nn.CrossEntropyLoss()
    
    epoch_logs = []
    best_val_f1 = -1.0
    best_model_state = None
    server_latencies = []
    
    total_t0 = time.perf_counter()
    
    # -------------------------------------------------------------
    # Stage 1: Linear Probe Head (3 Epochs)
    # -------------------------------------------------------------
    print("\n--- Stage 1: Classifier Head Warmup (3 Epochs, Backbone Frozen) ---")
    for param in model.features.parameters():
        param.requires_grad = False
    opt_head = torch.optim.AdamW(model.classifier.parameters(), lr=1e-3, weight_decay=1e-4)
    
    for ep in range(1, 4):
        ep_t0 = time.perf_counter()
        model.train()
        train_loss = 0.0
        train_correct = 0
        
        for imgs, targets in train_loader:
            opt_head.zero_grad()
            outputs = model(imgs)
            loss = criterion(outputs, targets)
            loss.backward()
            opt_head.step()
            train_loss += loss.item() * len(targets)
            train_correct += (outputs.argmax(dim=1) == targets).sum().item()
            
        train_loss /= len(train_ds)
        train_acc = train_correct / len(train_ds)
        
        # Validation on held-out untouched physical photographs
        model.eval()
        v_phys_loss = 0.0
        v_phys_preds, v_phys_true = [], []
        with torch.no_grad():
            for imgs, targets in val_phys_loader:
                out = model(imgs)
                v_phys_loss += eval_criterion(out, targets).item() * len(targets)
                v_phys_preds.extend(out.argmax(dim=1).cpu().numpy())
                v_phys_true.extend(targets.numpy())
                
        v_phys_loss /= len(val_phys_ds)
        v_phys_acc = float(np.mean(np.array(v_phys_preds) == np.array(v_phys_true)))
        v_phys_f1 = float(f1_score(v_phys_true, v_phys_preds, average="macro", zero_division=0))
        v_phys_bal = float(balanced_accuracy_score(v_phys_true, v_phys_preds))
        p, r, _, _ = precision_recall_fscore_support(v_phys_true, v_phys_preds, labels=[0, 1, 2], zero_division=0)
        
        ep_duration = round(time.perf_counter() - ep_t0, 1)
        srv_lat = check_host_server_latency()
        if srv_lat > 0: server_latencies.append(srv_lat)
        
        log_entry = {
            "epoch": ep,
            "phase": "head_warmup",
            "train_loss": round(train_loss, 4),
            "train_acc": round(train_acc, 4),
            "val_phys_loss": round(v_phys_loss, 4),
            "val_phys_acc": round(v_phys_acc, 4),
            "val_phys_macro_f1": round(v_phys_f1, 4),
            "val_phys_balanced_acc": round(v_phys_bal, 4),
            "aedes_recall": round(float(r[0]), 4),
            "anopheles_recall": round(float(r[1]), 4),
            "culex_recall": round(float(r[2]), 4),
            "epoch_duration_seconds": ep_duration,
            "host_server_latency_ms": srv_lat,
        }
        epoch_logs.append(log_entry)
        
        print(f"  Epoch {ep}/8 ({ep_duration}s) | Train Loss: {train_loss:.4f}, Acc: {train_acc:.4f} | "
              f"Val Phys Loss: {v_phys_loss:.4f}, F1: {v_phys_f1:.4f}, BalAcc: {v_phys_bal:.4f} "
              f"(Ae: {r[0]:.2f}, An: {r[1]:.2f}, Cx: {r[2]:.2f}) | SrvLat: {srv_lat} ms")
              
        if v_phys_f1 > best_val_f1:
            best_val_f1 = v_phys_f1
            best_model_state = copy.deepcopy(model.state_dict())

    # -------------------------------------------------------------
    # Stage 2: Top Backbone Fine-Tuning (5 Epochs)
    # -------------------------------------------------------------
    print("\n--- Stage 2: Top Backbone Fine-Tuning (5 Epochs, Cosine LR Scheduling) ---")
    for param in model.features[-3:].parameters():
        param.requires_grad = True
    opt_full = torch.optim.AdamW([
        {"params": model.features[-3:].parameters(), "lr": 2e-5},
        {"params": model.classifier.parameters(), "lr": 2e-4},
    ], weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(opt_full, T_max=5, eta_min=1e-6)
    
    for ep in range(4, 9):
        ep_t0 = time.perf_counter()
        model.train()
        train_loss = 0.0
        train_correct = 0
        
        for imgs, targets in train_loader:
            opt_full.zero_grad()
            outputs = model(imgs)
            loss = criterion(outputs, targets)
            loss.backward()
            opt_full.step()
            train_loss += loss.item() * len(targets)
            train_correct += (outputs.argmax(dim=1) == targets).sum().item()
            
        scheduler.step()
        train_loss /= len(train_ds)
        train_acc = train_correct / len(train_ds)
        
        # Validation on held-out physical photographs
        model.eval()
        v_phys_loss = 0.0
        v_phys_preds, v_phys_true = [], []
        with torch.no_grad():
            for imgs, targets in val_phys_loader:
                out = model(imgs)
                v_phys_loss += eval_criterion(out, targets).item() * len(targets)
                v_phys_preds.extend(out.argmax(dim=1).cpu().numpy())
                v_phys_true.extend(targets.numpy())
                
        v_phys_loss /= len(val_phys_ds)
        v_phys_acc = float(np.mean(np.array(v_phys_preds) == np.array(v_phys_true)))
        v_phys_f1 = float(f1_score(v_phys_true, v_phys_preds, average="macro", zero_division=0))
        v_phys_bal = float(balanced_accuracy_score(v_phys_true, v_phys_preds))
        p, r, _, _ = precision_recall_fscore_support(v_phys_true, v_phys_preds, labels=[0, 1, 2], zero_division=0)
        
        ep_duration = round(time.perf_counter() - ep_t0, 1)
        srv_lat = check_host_server_latency()
        if srv_lat > 0: server_latencies.append(srv_lat)
        
        log_entry = {
            "epoch": ep,
            "phase": "backbone_finetune",
            "train_loss": round(train_loss, 4),
            "train_acc": round(train_acc, 4),
            "val_phys_loss": round(v_phys_loss, 4),
            "val_phys_acc": round(v_phys_acc, 4),
            "val_phys_macro_f1": round(v_phys_f1, 4),
            "val_phys_balanced_acc": round(v_phys_bal, 4),
            "aedes_recall": round(float(r[0]), 4),
            "anopheles_recall": round(float(r[1]), 4),
            "culex_recall": round(float(r[2]), 4),
            "epoch_duration_seconds": ep_duration,
            "host_server_latency_ms": srv_lat,
        }
        epoch_logs.append(log_entry)
        
        print(f"  Epoch {ep}/8 ({ep_duration}s) | Train Loss: {train_loss:.4f}, Acc: {train_acc:.4f} | "
              f"Val Phys Loss: {v_phys_loss:.4f}, F1: {v_phys_f1:.4f}, BalAcc: {v_phys_bal:.4f} "
              f"(Ae: {r[0]:.2f}, An: {r[1]:.2f}, Cx: {r[2]:.2f}) | SrvLat: {srv_lat} ms")
              
        if v_phys_f1 >= best_val_f1:
            best_val_f1 = v_phys_f1
            best_model_state = copy.deepcopy(model.state_dict())
            
    total_duration = round(time.perf_counter() - total_t0, 1)
    
    # Load best model weights
    if best_model_state is not None:
        model.load_state_dict(best_model_state)
        print(f"\nLoaded Best Validation Checkpoint (Macro-F1: {best_val_f1:.4f})")
        
    # Full evaluation on all 44 physical original photographs
    model.eval()
    all_phys_df = df[~df["is_augmented"]].copy()
    all_phys_ds = MosqFastDataset(all_phys_df, transform=build_transforms(IMG_SIZE, is_train=False))
    all_phys_loader = DataLoader(all_phys_ds, batch_size=BATCH_SIZE, shuffle=False)
    
    final_preds, final_true = [], []
    with torch.no_grad():
        for imgs, targets in all_phys_loader:
            final_preds.extend(model(imgs).argmax(dim=1).cpu().numpy())
            final_true.extend(targets.numpy())
            
    phys_global_acc = float(np.mean(np.array(final_preds) == np.array(final_true)))
    phys_global_f1 = float(f1_score(final_true, final_preds, average="macro"))
    phys_global_bal = float(balanced_accuracy_score(final_true, final_preds))
    cm = confusion_matrix(final_true, final_preds, labels=[0, 1, 2]).tolist()
    p_cum, r_cum, _, _ = precision_recall_fscore_support(final_true, final_preds, labels=[0, 1, 2], zero_division=0)
    
    print("\nGlobal Evaluation on All 44 Original Physical Photographs:")
    print(f"  Overall Accuracy: {phys_global_acc:.4f} ({sum(np.array(final_preds) == np.array(final_true))}/44)")
    print(f"  Macro-F1: {phys_global_f1:.4f} | Balanced Accuracy: {phys_global_bal:.4f}")
    print(f"  Recall: Aedes={r_cum[0]:.4f}, Anopheles={r_cum[1]:.4f}, Culex={r_cum[2]:.4f}")
    print(f"  Confusion Matrix: {cm}")
    
    results = {
        "training_duration_seconds": total_duration,
        "peak_ram_mb": round(get_peak_ram_mb(), 2),
        "median_host_server_latency_ms": round(float(np.median(server_latencies)), 2) if server_latencies else None,
        "best_val_macro_f1": round(best_val_f1, 4),
        "global_physical_accuracy": round(phys_global_acc, 4),
        "global_physical_macro_f1": round(phys_global_f1, 4),
        "global_physical_balanced_acc": round(phys_global_bal, 4),
        "global_aedes_recall": round(float(r_cum[0]), 4),
        "global_anopheles_recall": round(float(r_cum[1]), 4),
        "global_culex_recall": round(float(r_cum[2]), 4),
        "confusion_matrix": cm,
        "epoch_logs": epoch_logs,
    }
    return model, results

# ----------------------------------------------------------------------
# 4. Artifact Export & Verification
# ----------------------------------------------------------------------
def export_and_verify(model: nn.Module, df: pd.DataFrame) -> Dict[str, Any]:
    print("\n" + "=" * 70)
    print("3. EXPORTING ONNX AND VERIFYING RUNTIME")
    print("=" * 70)
    
    pt_path = MODELS_DIR / "vectora_extended_best.pt"
    onnx_path = MODELS_DIR / "vectora_extended_fp32.onnx"
    
    # Save PyTorch
    torch.save(model.state_dict(), pt_path)
    pt_size = pt_path.stat().st_size
    pt_sha = sha256_file(pt_path)
    print(f"Saved PyTorch weights: {pt_path} ({round(pt_size / 1024 / 1024, 2)} MB)")
    print(f"  SHA-256: {pt_sha}")
    
    # Export ONNX (single self-contained file)
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
    
    # Verify ONNX Runtime on all 44 physical photographs
    so = ort.SessionOptions()
    so.intra_op_num_threads = 3
    session = ort.InferenceSession(str(onnx_path), so, providers=["CPUExecutionProvider"])
    
    val_trans = build_transforms(IMG_SIZE, is_train=False)
    phys_df = df[~df["is_augmented"]]
    
    latencies = []
    onnx_preds = []
    
    for _, row in phys_df.iterrows():
        img = get_cached_image(row["filepath"])
        tensor = val_trans(img).unsqueeze(0).numpy()
        
        t0 = time.perf_counter()
        ort_out = session.run(None, {"input": tensor})[0]
        latencies.append((time.perf_counter() - t0) * 1000.0)
        
        onnx_preds.append(int(np.argmax(ort_out, axis=1)[0]))
        
    onnx_acc = float(np.mean(np.array(onnx_preds) == phys_df["label_idx"].values))
    median_latency = float(np.median(latencies))
    p95_latency = float(np.percentile(latencies, 95))
    
    print(f"ONNX Runtime Verification on 44 Physical Photographs:")
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
        "onnx_accuracy_on_44_originals": round(onnx_acc, 4),
    }

# ----------------------------------------------------------------------
# Main Execution
# ----------------------------------------------------------------------
def main():
    print("VECTORA AI: EXTENDED COMBINED TRAINING PIPELINE")
    init_lat = check_host_server_latency()
    print(f"Host Production Server Health Check Latency: {init_lat} ms")
    
    df = load_verified_dataset()
    model, train_results = run_extended_training(df)
    export_meta = export_and_verify(model, df)
    
    final_lat = check_host_server_latency()
    print(f"Final Host Production Server Health Check Latency: {final_lat} ms")
    
    full_output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hardware": {
            "cpu": "Intel Core i7-2600 @ 3.40GHz",
            "threads_assigned": 3,
            "batch_size": BATCH_SIZE,
            "image_size": IMG_SIZE,
            "initial_server_latency_ms": init_lat,
            "final_server_latency_ms": final_lat,
        },
        "dataset_summary": {
            "total_verified_images": len(df),
            "physical_specimens": 44,
            "verified_augmentations": len(df[df["is_augmented"]]),
            "class_distribution": {str(k): int(v) for k, v in df["genus"].value_counts().items()},
        },
        "training_results": train_results,
        "export_metadata": export_meta,
    }
    
    json_path = REPORTS_DIR / "v3_extended_training_results.json"
    with open(json_path, "w") as f:
        json.dump(full_output, f, indent=2)
    print(f"\nSaved structured results to: {json_path}")

if __name__ == "__main__":
    main()
