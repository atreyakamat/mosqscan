#!/usr/bin/env python3
"""
Vectora AI: Hybrid Mosquito Classifier Training Script
Strictly CPU-constrained training for Intel Core i7-2600.
ASD-STE100 Compliant Implementation.

Safety & Hardware Rules:
- CPU Threads: Constrained to 3 (leaves 5 threads for host OS and containers).
- DataLoader Workers: 0 (in-memory image caching eliminates disk I/O).
- Batch Size: 4 (maximizes L3 cache efficiency on Sandy Bridge).
- Specimen-Grouped Cross-Validation: StratifiedGroupKFold (n_splits=4, random_state=42).
- Zero Specimen Leakage: All augmentations of a physical parent remain in the parent's fold.
- Validation Partition: Contains untouched physical photographs ONLY (no augmentations).
- Active Server Preservation: models/vectora_v3_fp32.onnx remains untouched.
- Outputs stored strictly in models/research/ and reports/research/.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import resource
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

os.environ["TORCH_CPP_LOG_LEVEL"] = "ERROR"
os.environ["GLOG_minloglevel"] = "3"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

import numpy as np
import pandas as pd
from PIL import Image
import urllib.request
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    balanced_accuracy_score,
    f1_score,
    precision_recall_fscore_support,
)
from sklearn.model_selection import StratifiedGroupKFold
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights

PROJECT_ROOT = Path("/home/nimr/Projects/mosqscan")
ORIGINAL_DIR = PROJECT_ROOT / "Mosquito Images Original"
AUGMENTED_DIR = PROJECT_ROOT / "Mosquito Images Augmented"
MODELS_DIR = PROJECT_ROOT / "models"
RESEARCH_MODELS_DIR = PROJECT_ROOT / "models/research"
RESEARCH_REPORTS_DIR = PROJECT_ROOT / "reports/research"
MANIFEST_PATH = PROJECT_ROOT / "data/metadata/conservative_lineage_manifest.json"
PRODUCTION_ONNX = MODELS_DIR / "vectora_v3_fp32.onnx"
EXPECTED_PROD_SHA256 = "c3a3656f746a1bb2e7ac428e44670d89cf51f0d0f923ad3aa15420e8a4592cfa"

CLASSES = ["aedes", "anopheles", "culex"]
CLASS_TO_IDX = {"aedes": 0, "anopheles": 1, "culex": 2}
IDX_TO_CLASS = {0: "aedes", 1: "anopheles", 2: "culex"}
IMG_SIZE = 224


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


# In-memory PIL Image Cache
_IMAGE_CACHE: Dict[str, Image.Image] = {}


def get_cached_image(path: str) -> Image.Image:
    if path not in _IMAGE_CACHE:
        with Image.open(path) as im:
            _IMAGE_CACHE[path] = im.convert("RGB")
    return _IMAGE_CACHE[path]


class HybridDataset(Dataset):
    def __init__(self, df: pd.DataFrame, transform=None, multiplier: int = 1):
        self.df = df.reset_index(drop=True)
        self.transform = transform
        self.multiplier = multiplier
        self.base_len = len(self.df)

    def __len__(self):
        return self.base_len * self.multiplier

    def __getitem__(self, idx: int):
        real_idx = idx % self.base_len
        row = self.df.iloc[real_idx]
        img = get_cached_image(row["filepath"])
        if self.transform:
            img = self.transform(img)
        label = row["label_idx"]
        return img, label, row["parent_specimen"], row["filename"]


def build_transforms(img_size: int, is_train: bool, online_augment: bool = True):
    if is_train and online_augment:
        return transforms.Compose([
            transforms.Resize((img_size, img_size)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomVerticalFlip(p=0.5),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
            transforms.RandomRotation(degrees=15),
            transforms.RandomAffine(degrees=0, translate=(0.05, 0.05)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
    return transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])


def build_model(num_classes: int = 3) -> nn.Module:
    weights = EfficientNet_B0_Weights.DEFAULT
    model = efficientnet_b0(weights=weights)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, num_classes)
    return model


def load_and_audit_dataset() -> Tuple[pd.DataFrame, Dict[str, Any]]:
    print("=" * 70)
    print("1. LOADING AND AUDITING DATASET (STRICT LINEAGE)")
    print("=" * 70)

    with open(MANIFEST_PATH, "r") as f:
        manifest_data = json.load(f)

    lineage_records = manifest_data["lineage_records"]
    total_augmented = len(lineage_records)
    verified_map: Dict[str, str] = {}
    excluded_counts = {"UNCONFIRMED_LOW_CONFIDENCE": 0, "AMBIGUOUS_SIBLING_DISCORDANT": 0}

    for r in lineage_records:
        status = r["conservative_status"]
        img_name = Path(r["augmented_image"]).name
        if status == "VERIFIED_BLOCK_CONCORDANT":
            verified_map[img_name] = r["sequential_block_parent"]
        else:
            excluded_counts[status] = excluded_counts.get(status, 0) + 1

    print(f"Precomputed augmented images in manifest: {total_augmented}")
    print(f"  - Verified Block-Concordant (Included): {len(verified_map)}")
    print(f"  - Excluded (Unconfirmed Low Confidence): {excluded_counts.get('UNCONFIRMED_LOW_CONFIDENCE', 0)}")
    print(f"  - Excluded (Ambiguous Sibling Discordant): {excluded_counts.get('AMBIGUOUS_SIBLING_DISCORDANT', 0)}")

    # Load 44 original photographs
    records = []
    for p in sorted(ORIGINAL_DIR.rglob("*.jpg")):
        parent_dir = p.parent.name.lower()
        if "aedes" in parent_dir:
            genus = "aedes"
        elif "anopheles" in parent_dir:
            genus = "anopheles"
        elif "culex" in parent_dir:
            genus = "culex"
        else:
            continue

        records.append({
            "filename": p.name,
            "filepath": str(p),
            "genus": genus,
            "label_idx": CLASS_TO_IDX[genus],
            "parent_specimen": p.name,
            "is_augmented": False,
            "status": "ORIGINAL_PHYSICAL_SPECIMEN",
        })
    print(f"Loaded {len(records)} original physical photographs.")

    # Add verified augmented images
    aug_included_count = 0
    for p in sorted(AUGMENTED_DIR.rglob("*.jpg")):
        if p.name in verified_map:
            parent_dir = p.parent.name.lower()
            if "aedes" in parent_dir:
                genus = "aedes"
            elif "anopheles" in parent_dir:
                genus = "anopheles"
            elif "culex" in parent_dir:
                genus = "culex"
            else:
                continue

            records.append({
                "filename": p.name,
                "filepath": str(p),
                "genus": genus,
                "label_idx": CLASS_TO_IDX[genus],
                "parent_specimen": verified_map[p.name],
                "is_augmented": True,
                "status": "VERIFIED_PRECOMPUTED_AUGMENTATION",
            })
            aug_included_count += 1

    df = pd.DataFrame(records)
    print(f"Total dataset records: {len(df)}")
    print(f"  - Physical Specimens: 44")
    print(f"  - Precomputed Verified Augmentations: {aug_included_count}")
    print(f"  - Unique Biological Parents: {df['parent_specimen'].nunique()}")

    # Preload into RAM cache
    print("Preloading all images into RAM cache...")
    t0 = time.perf_counter()
    for fp in df["filepath"]:
        get_cached_image(fp)
    print(f"Preloaded {len(_IMAGE_CACHE)} images into RAM in {round(time.perf_counter() - t0, 2)}s.")

    audit_summary = {
        "original_specimens_count": 44,
        "verified_augmented_count": aug_included_count,
        "excluded_unconfirmed_count": excluded_counts.get("UNCONFIRMED_LOW_CONFIDENCE", 0),
        "excluded_ambiguous_count": excluded_counts.get("AMBIGUOUS_SIBLING_DISCORDANT", 0),
        "total_training_eligible_pool": len(df),
        "unique_biological_parents": int(df["parent_specimen"].nunique()),
    }
    return df, audit_summary


def create_partitions(df: pd.DataFrame, n_splits: int = 4, random_state: int = 42):
    phys_df = df[~df["is_augmented"]].sort_values("filename").reset_index(drop=True)
    sgkf = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    splits = list(sgkf.split(phys_df, phys_df["label_idx"], groups=phys_df["parent_specimen"]))

    partitions = []
    print("\n" + "=" * 70)
    print(f"2. PARTITIONING ({n_splits}-FOLD STRATIFIED GROUP K-FOLD)")
    print("=" * 70)

    for fold_idx, (train_phys_idx, val_phys_idx) in enumerate(splits):
        val_phys_specimens = set(phys_df.iloc[val_phys_idx]["parent_specimen"])
        train_phys_specimens = set(phys_df.iloc[train_phys_idx]["parent_specimen"])

        overlap = val_phys_specimens.intersection(train_phys_specimens)
        assert len(overlap) == 0, f"Critical Leakage in fold {fold_idx}: {overlap}"

        val_phys_df = phys_df.iloc[val_phys_idx].copy()
        # All derivative images for train specimens belong to training partition
        train_full_df = df[df["parent_specimen"].isin(train_phys_specimens)].copy()

        # Leakage check: ensure no validation specimen derivative is in train
        val_deriv_in_train = train_full_df[train_full_df["parent_specimen"].isin(val_phys_specimens)]
        assert len(val_deriv_in_train) == 0, f"Augmentation leakage in fold {fold_idx}"

        val_class_counts = val_phys_df["genus"].value_counts().to_dict()
        train_spec_counts = phys_df.iloc[train_phys_idx]["genus"].value_counts().to_dict()
        print(f"Fold {fold_idx + 1}:")
        print(f"  - Train: {len(train_full_df)} images ({len(train_phys_specimens)} parents) -> {train_spec_counts}")
        print(f"  - Val:   {len(val_phys_df)} physical specimens -> {val_class_counts}")

        partitions.append((train_full_df, val_phys_df))
    return partitions


def run_experiment(
    experiment_name: str,
    partitions: List[Tuple[pd.DataFrame, pd.DataFrame]],
    use_class_weighting: bool,
    epochs_head: int,
    epochs_fine: int,
    batch_size: int,
    checkpoint_prefix: str,
) -> Dict[str, Any]:
    print("\n" + "=" * 70)
    print(f"EXECUTING EXPERIMENT: {experiment_name}")
    print(f"Class Weighting: {use_class_weighting} | Head Epochs: {epochs_head} | Fine Epochs: {epochs_fine}")
    print("=" * 70)

    train_trans = build_transforms(IMG_SIZE, is_train=True, online_augment=True)
    val_trans = build_transforms(IMG_SIZE, is_train=False, online_augment=False)

    fold_stats = []
    all_y_true = []
    all_y_pred = []
    all_specimens = []
    all_probabilities = []
    server_latencies = []

    t_start = time.perf_counter()

    for fold_idx, (train_df, val_phys_df) in enumerate(partitions):
        fold_t0 = time.perf_counter()

        # Class weighting calculation
        if use_class_weighting:
            class_counts = train_df["label_idx"].value_counts().sort_index().values
            class_weights = len(train_df) / (len(class_counts) * class_counts.astype(np.float32))
            weight_tensor = torch.tensor(class_weights, dtype=torch.float32)
        else:
            weight_tensor = None

        train_ds = HybridDataset(train_df, transform=train_trans, multiplier=1)
        val_ds = HybridDataset(val_phys_df, transform=val_trans, multiplier=1)

        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0)
        val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)

        model = build_model(3)
        criterion = nn.CrossEntropyLoss(weight=weight_tensor)

        # Baseline latency check during training
        lat = check_host_server_latency()
        if lat > 0:
            server_latencies.append(lat)

        # Stage 1: Linear Probe Head
        for param in model.features.parameters():
            param.requires_grad = False
        opt_head = torch.optim.AdamW(model.classifier.parameters(), lr=1e-3, weight_decay=1e-4)

        model.train()
        for ep in range(epochs_head):
            for imgs, targets, _, _ in train_loader:
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
            for imgs, targets, _, _ in train_loader:
                opt_full.zero_grad()
                loss = criterion(model(imgs), targets)
                loss.backward()
                opt_full.step()

        # Save fold checkpoint in models/research/
        ckpt_path = RESEARCH_MODELS_DIR / f"{checkpoint_prefix}_fold{fold_idx + 1}.pt"
        torch.save(model.state_dict(), ckpt_path)

        # Evaluate strictly on untouched physical validation specimens
        model.eval()
        fold_y_true = []
        fold_y_pred = []
        fold_specs = []
        fold_probs = []
        val_losses = []

        eval_criterion = nn.CrossEntropyLoss()
        with torch.no_grad():
            for imgs, targets, specs, fnames in val_loader:
                outputs = model(imgs)
                v_loss = eval_criterion(outputs, targets)
                val_losses.append(v_loss.item())
                probs = torch.softmax(outputs, dim=1).cpu().numpy()
                preds = outputs.argmax(dim=1).cpu().numpy()

                fold_y_true.extend(targets.numpy())
                fold_y_pred.extend(preds)
                fold_specs.extend(specs)
                fold_probs.extend(probs.tolist())

        macro_f1 = f1_score(fold_y_true, fold_y_pred, average="macro", zero_division=0)
        bal_acc = balanced_accuracy_score(fold_y_true, fold_y_pred)
        acc = float(np.mean(np.array(fold_y_true) == np.array(fold_y_pred)))
        mean_val_loss = float(np.mean(val_losses))

        all_y_true.extend(fold_y_true)
        all_y_pred.extend(fold_y_pred)
        all_specimens.extend(fold_specs)
        all_probabilities.extend(fold_probs)

        p, r, f, s = precision_recall_fscore_support(
            fold_y_true, fold_y_pred, labels=[0, 1, 2], zero_division=0
        )
        fold_duration = round(time.perf_counter() - fold_t0, 1)

        stat = {
            "fold": fold_idx + 1,
            "checkpoint_path": str(ckpt_path),
            "checkpoint_sha256": sha256_file(ckpt_path),
            "train_images": len(train_df),
            "train_specimens": int(train_df["parent_specimen"].nunique()),
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
        print(
            f"  Fold {fold_idx + 1} ({fold_duration}s): "
            f"Macro-F1={stat['macro_f1']:.4f}, BalAcc={stat['balanced_accuracy']:.4f}, "
            f"Acc={stat['accuracy']:.4f}, Anopheles-R={stat['anopheles_recall']:.4f}, "
            f"ValLoss={stat['val_loss']:.4f}"
        )

    total_duration = round(time.perf_counter() - t_start, 1)

    # Pooled Out-Of-Fold Evaluation (All 44 Physical Specimens)
    pooled_macro_f1 = f1_score(all_y_true, all_y_pred, average="macro", zero_division=0)
    pooled_bal_acc = balanced_accuracy_score(all_y_true, all_y_pred)
    pooled_acc = float(np.mean(np.array(all_y_true) == np.array(all_y_pred)))
    cm = confusion_matrix(all_y_true, all_y_pred, labels=[0, 1, 2]).tolist()
    p_pool, r_pool, f_pool, s_pool = precision_recall_fscore_support(
        all_y_true, all_y_pred, labels=[0, 1, 2], zero_division=0
    )

    f1_scores = [s["macro_f1"] for s in fold_stats]
    bal_accs = [s["balanced_accuracy"] for s in fold_stats]

    # Detailed specimen predictions
    specimen_predictions = []
    for spec, yt, yp, pr in zip(all_specimens, all_y_true, all_y_pred, all_probabilities):
        specimen_predictions.append({
            "specimen_id": spec,
            "true_genus": IDX_TO_CLASS[yt],
            "pred_genus": IDX_TO_CLASS[yp],
            "correct": bool(yt == yp),
            "probabilities": {
                "aedes": round(pr[0], 4),
                "anopheles": round(pr[1], 4),
                "culex": round(pr[2], 4),
            },
        })

    result = {
        "experiment_name": experiment_name,
        "class_weighting": use_class_weighting,
        "epochs_head": epochs_head,
        "epochs_fine": epochs_fine,
        "batch_size": batch_size,
        "total_duration_seconds": total_duration,
        "mean_fold_macro_f1": round(float(np.mean(f1_scores)), 4),
        "std_fold_macro_f1": round(float(np.std(f1_scores, ddof=1)), 4),
        "mean_fold_bal_acc": round(float(np.mean(bal_accs)), 4),
        "std_fold_bal_acc": round(float(np.std(bal_accs, ddof=1)), 4),
        "pooled_out_of_fold": {
            "total_physical_specimens": len(all_y_true),
            "macro_f1": round(float(pooled_macro_f1), 4),
            "balanced_accuracy": round(float(pooled_bal_acc), 4),
            "accuracy": round(float(pooled_acc), 4),
            "confusion_matrix": cm,
            "per_class": {
                "aedes": {
                    "precision": round(float(p_pool[0]), 4),
                    "recall": round(float(r_pool[0]), 4),
                    "f1": round(float(f_pool[0]), 4),
                    "support": int(s_pool[0]),
                },
                "anopheles": {
                    "precision": round(float(p_pool[1]), 4),
                    "recall": round(float(r_pool[1]), 4),
                    "f1": round(float(f_pool[1]), 4),
                    "support": int(s_pool[1]),
                },
                "culex": {
                    "precision": round(float(p_pool[2]), 4),
                    "recall": round(float(r_pool[2]), 4),
                    "f1": round(float(f_pool[2]), 4),
                    "support": int(s_pool[2]),
                },
            },
        },
        "fold_statistics": fold_stats,
        "specimen_predictions": specimen_predictions,
        "server_latencies_during_run": server_latencies,
    }

    print("\n" + "-" * 50)
    print(f"Summary for {experiment_name}:")
    print(f"  Mean Fold Macro-F1: {result['mean_fold_macro_f1']} +/- {result['std_fold_macro_f1']}")
    print(f"  Pooled Macro-F1:    {result['pooled_out_of_fold']['macro_f1']}")
    print(f"  Pooled BalAcc:      {result['pooled_out_of_fold']['balanced_accuracy']}")
    print(f"  Pooled Accuracy:    {result['pooled_out_of_fold']['accuracy']} ({int(pooled_acc * 44)}/44)")
    print(f"  Anopheles Recall:   {result['pooled_out_of_fold']['per_class']['anopheles']['recall']} ({int(r_pool[1] * s_pool[1])}/{s_pool[1]})")
    print(f"  Confusion Matrix:   {cm}")
    print("-" * 50)
    return result


def main():
    parser = argparse.ArgumentParser(description="Train Vectora AI Hybrid Mosquito Classifier on CPU.")
    parser.add_argument("--epochs-head", type=int, default=1, help="Head warmup epochs per fold (default: 1)")
    parser.add_argument("--epochs-fine", type=int, default=1, help="Fine-tuning epochs per fold (default: 1)")
    parser.add_argument("--batch-size", type=int, default=4, help="Batch size (default: 4)")
    parser.add_argument("--threads", type=int, default=3, help="PyTorch CPU threads (default: 3)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument("--run-ablation", action="store_true", help="Execute class-weighted ablation after primary")
    args = parser.parse_args()

    # Enforce CPU threading
    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    print("=" * 70)
    print("VECTORA AI — HYBRID CLASSIFIER CPU TRAINING EXECUTION")
    print(f"CPU Threads: {args.threads} | Batch Size: {args.batch_size} | Seed: {args.seed}")
    print("=" * 70)

    # Verify active server ONNX checksum before anything
    assert PRODUCTION_ONNX.exists(), f"Missing production model: {PRODUCTION_ONNX}"
    pre_sha = sha256_file(PRODUCTION_ONNX)
    print(f"Verified Production ONNX Pre-run SHA-256: {pre_sha}")
    if pre_sha != EXPECTED_PROD_SHA256:
        print(f"WARNING: Active ONNX checksum mismatch! Expected {EXPECTED_PROD_SHA256}")

    # Ensure output directories exist
    RESEARCH_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    RESEARCH_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Dataset Loading & Audit
    df, audit_summary = load_and_audit_dataset()

    # 2. Partitioning
    partitions = create_partitions(df, n_splits=4, random_state=args.seed)

    # 3. Primary Run: Unweighted Cross-Entropy
    primary_results = run_experiment(
        experiment_name="Primary_Hybrid_Unweighted",
        partitions=partitions,
        use_class_weighting=False,
        epochs_head=args.epochs_head,
        epochs_fine=args.epochs_fine,
        batch_size=args.batch_size,
        checkpoint_prefix="hybrid_unweighted",
    )

    # 4. Optional Ablation: Class-Weighted Cross-Entropy
    ablation_results = None
    if args.run_ablation:
        ablation_results = run_experiment(
            experiment_name="Ablation_Hybrid_ClassWeighted",
            partitions=partitions,
            use_class_weighting=True,
            epochs_head=args.epochs_head,
            epochs_fine=args.epochs_fine,
            batch_size=args.batch_size,
            checkpoint_prefix="hybrid_weighted",
        )

    # Verify active server ONNX checksum remains intact
    post_sha = sha256_file(PRODUCTION_ONNX)
    print(f"\nVerified Production ONNX Post-run SHA-256: {post_sha}")
    assert pre_sha == post_sha, "CRITICAL ERROR: Production ONNX was modified during training!"

    peak_ram = get_peak_ram_mb()
    print(f"Peak Process RAM: {peak_ram:.1f} MB")

    # Save comprehensive results JSON
    final_payload = {
        "metadata": {
            "execution_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "hardware_platform": "Intel Core i7-2600 (Sandy Bridge, 4 cores, 8 threads, AVX)",
            "cpu_threads_allocated": args.threads,
            "batch_size": args.batch_size,
            "random_seed": args.seed,
            "peak_process_ram_mb": round(peak_ram, 1),
            "production_onnx_preserved": bool(pre_sha == post_sha),
            "production_onnx_sha256": post_sha,
        },
        "dataset_audit": audit_summary,
        "primary_experiment": primary_results,
        "ablation_experiment": ablation_results,
    }

    out_json = RESEARCH_REPORTS_DIR / "hybrid_training_results.json"
    with open(out_json, "w") as f:
        json.dump(final_payload, f, indent=2)
    print(f"\nFinal hybrid training results written to: {out_json}")


if __name__ == "__main__":
    main()
