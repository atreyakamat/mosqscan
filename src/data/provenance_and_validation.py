#!/usr/bin/env python3
"""
Vectora AI 3.0 - Dataset Ingestion, Provenance Recovery & Quality Validation Pipeline
ASD-STE100 Compliant Implementation.
"""
from __future__ import annotations

import csv
import glob
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Tuple, Any

import cv2
import imagehash
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt

ORIGINAL_BASE = "/home/nimr/Projects/mosqscan/data/staging/original/Original Images Mendeley"
AUGMENTED_BASE = "/home/nimr/Projects/mosqscan/data/staging/augmented"
METADATA_DIR = "/home/nimr/Projects/mosqscan/data/metadata"
CONTACT_SHEETS_DIR = os.path.join(METADATA_DIR, "contact_sheets")

GENUS_CONFIGS = [
    {
        "genus": "Aedes",
        "orig_dir": os.path.join(ORIGINAL_BASE, "Aedes Aegypti"),
        "aug_dir": os.path.join(AUGMENTED_BASE, "Aedes Aegypti"),
        "prefix": "Aedes_aegypti_",
        "expected_orig": 15,
        "expected_aug": 900,
    },
    {
        "genus": "Anopheles",
        "orig_dir": os.path.join(ORIGINAL_BASE, "Anopheles Stephensi"),
        "aug_dir": os.path.join(AUGMENTED_BASE, "Anopheles Stephensi"),
        "prefix": "Anopheles_stephensi_",
        "expected_orig": 9,
        "expected_aug": 540,
    },
    {
        "genus": "Culex",
        "orig_dir": os.path.join(ORIGINAL_BASE, "Culex Quinquefasciatus"),
        "aug_dir": os.path.join(AUGMENTED_BASE, "Culex Quinquefasciatus"),
        "prefix": "Culex_quinquefasciatus_",
        "expected_orig": 20,
        "expected_aug": 1200,
    },
]

def sha256_file(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def compute_quality_metrics(filepath: str) -> Dict[str, Any]:
    stat = os.stat(filepath)
    file_size = stat.st_size
    file_hash = sha256_file(filepath)
    
    # PIL check
    try:
        with Image.open(filepath) as pil_img:
            width, height = pil_img.size
            mode = pil_img.mode
            pil_ok = True
    except Exception as e:
        width, height, mode = 0, 0, "ERROR"
        pil_ok = False
        
    # OpenCV check
    cv_img = cv2.imread(filepath)
    if cv_img is None:
        cv_ok = False
        blur_score = 0.0
        mean_lum = 0.0
        underexposed = 0.0
        overexposed = 0.0
    else:
        cv_ok = True
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        mean_lum = float(np.mean(gray))
        total_pixels = gray.size
        underexposed = float(np.sum(gray < 15) / total_pixels)
        overexposed = float(np.sum(gray > 240) / total_pixels)
        
    return {
        "file_path": filepath,
        "file_name": os.path.basename(filepath),
        "file_size_bytes": file_size,
        "sha256": file_hash,
        "pil_valid": pil_ok,
        "cv_valid": cv_ok,
        "width": width,
        "height": height,
        "channels": mode,
        "blur_laplacian_var": round(blur_score, 2),
        "mean_luminance": round(mean_lum, 2),
        "underexposed_ratio": round(underexposed, 4),
        "overexposed_ratio": round(overexposed, 4),
    }

def run_pipeline():
    os.makedirs(METADATA_DIR, exist_ok=True)
    os.makedirs(CONTACT_SHEETS_DIR, exist_ok=True)
    
    sift = cv2.SIFT_create()
    bf = cv2.BFMatcher()
    
    all_manifest = []
    all_lineage = []
    all_quality = []
    genus_summary = {}
    hash_to_files: Dict[str, List[str]] = {}
    
    t_start = time.time()
    print("=" * 70)
    print("VECTORA AI 3.0: STARTING DATASET PROVENANCE AND QUALITY PIPELINE")
    print("=" * 70)
    
    for cfg in GENUS_CONFIGS:
        genus = cfg["genus"]
        orig_dir = cfg["orig_dir"]
        aug_dir = cfg["aug_dir"]
        prefix = cfg["prefix"]
        
        orig_files = sorted(glob.glob(os.path.join(orig_dir, "*.jpg")))
        aug_files = sorted(glob.glob(os.path.join(aug_dir, "*.jpg")), 
                           key=lambda x: int(os.path.basename(x).replace(prefix, "").replace(".jpg", "")))
        
        print(f"\nProcessing {genus}: {len(orig_files)} original, {len(aug_files)} augmented images...")
        
        # 1. Profile original specimens
        orig_data = {}
        for of in orig_files:
            bname = os.path.basename(of)
            q = compute_quality_metrics(of)
            q["dataset_type"] = "original"
            q["genus"] = genus
            q["specimen_id"] = bname
            all_quality.append(q)
            all_manifest.append(q)
            
            hash_to_files.setdefault(q["sha256"], []).append(of)
            
            # Feature extraction
            img_bgr = cv2.imread(of)
            img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            # Resize for consistent SIFT scale
            img_small = cv2.resize(img_gray, (512, 512))
            kp, des = sift.detectAndCompute(img_small, None)
            
            with Image.open(of) as pil_im:
                ph = imagehash.phash(pil_im.convert("L").resize((256, 256)))
                
            orig_data[bname] = {
                "path": of,
                "kp": kp,
                "des": des,
                "phash": ph,
            }
            
        # 2. Process augmented images and establish lineage
        genus_lineage = []
        for idx, af in enumerate(aug_files):
            bname = os.path.basename(af)
            q = compute_quality_metrics(af)
            q["dataset_type"] = "augmented"
            q["genus"] = genus
            
            hash_to_files.setdefault(q["sha256"], []).append(af)
            
            aimg_bgr = cv2.imread(af)
            aimg_gray = cv2.cvtColor(aimg_bgr, cv2.COLOR_BGR2GRAY) if aimg_bgr is not None else None
            akp, ades = (sift.detectAndCompute(aimg_gray, None)) if aimg_gray is not None else (None, None)
            
            with Image.open(af) as pil_aim:
                aph = imagehash.phash(pil_aim.convert("L"))
                
            match_scores = {}
            for of_bname, oinfo in orig_data.items():
                odes = oinfo["des"]
                if ades is None or odes is None or len(ades) < 2 or len(odes) < 2:
                    good_matches = 0
                else:
                    m = bf.knnMatch(ades, odes, k=2)
                    good = [x for x, y in m if x.distance < 0.75 * y.distance]
                    good_matches = len(good)
                    
                hdist = int(aph - oinfo["phash"])
                match_scores[of_bname] = {
                    "sift_matches": good_matches,
                    "phash_distance": hdist,
                }
                
            # Rank matches
            sorted_candidates = sorted(
                match_scores.items(),
                key=lambda item: (item[1]["sift_matches"], -item[1]["phash_distance"]),
                reverse=True
            )
            
            top1_id, top1_info = sorted_candidates[0]
            top2_id, top2_info = sorted_candidates[1] if len(sorted_candidates) > 1 else ("none", {"sift_matches": 0, "phash_distance": 64})
            
            top1_sift = top1_info["sift_matches"]
            top2_sift = top2_info["sift_matches"]
            top1_phash = top1_info["phash_distance"]
            margin = top1_sift - top2_sift
            
            # Confidence criteria
            # High: substantial SIFT matches and clear margin over runner-up
            if top1_sift >= 8 and (margin >= 4 or top2_sift <= 0.4 * top1_sift):
                confidence = "HIGH"
                status = "VERIFIED"
                score = round(min(1.0, (top1_sift / 20.0) * 0.7 + max(0, (32 - top1_phash)/32.0) * 0.3), 3)
            elif top1_sift >= 5 and margin >= 2:
                confidence = "MEDIUM"
                status = "VERIFIED"
                score = round(min(1.0, (top1_sift / 20.0) * 0.7 + max(0, (32 - top1_phash)/32.0) * 0.3), 3)
            elif top1_sift >= 3 and top1_phash <= 16:
                confidence = "MEDIUM"
                status = "VERIFIED"
                score = round(min(1.0, (top1_sift / 20.0) * 0.7 + max(0, (32 - top1_phash)/32.0) * 0.3), 3)
            else:
                confidence = "LOW"
                status = "UNCONFIRMED"
                score = round(max(0.1, (top1_sift / 20.0)), 3)
                
            q["specimen_id"] = top1_id if status == "VERIFIED" else "UNKNOWN"
            all_quality.append(q)
            all_manifest.append(q)
            
            lineage_row = {
                "augmented_image": os.path.relpath(af, "/home/nimr/Projects/mosqscan"),
                "genus": genus,
                "parent_specimen_id": top1_id,
                "similarity_score": score,
                "matching_method": "SIFT_BFMatcher_Ratio_Test+PerceptualHash",
                "top1_sift_matches": top1_sift,
                "top2_sift_matches": top2_sift,
                "phash_distance": top1_phash,
                "mapping_confidence": confidence,
                "verification_status": status,
            }
            all_lineage.append(lineage_row)
            genus_lineage.append(lineage_row)
            
            if (idx + 1) % 200 == 0 or (idx + 1) == len(aug_files):
                print(f"  Processed {idx + 1}/{len(aug_files)} augmented images for {genus}...")
                
        # 3. Generate contact sheet for this genus
        # Select first 3 original specimens and 5 sample children each
        sample_parents = list(orig_data.keys())[:3]
        fig, axes = plt.subplots(len(sample_parents), 6, figsize=(15, 3 * len(sample_parents)))
        fig.suptitle(f"Contact Sheet: {genus} Specimens and Augmented Children", fontsize=14, weight="bold")
        
        for r_idx, parent_id in enumerate(sample_parents):
            parent_path = orig_data[parent_id]["path"]
            p_img = Image.open(parent_path).resize((224, 224))
            axes[r_idx, 0].imshow(p_img)
            axes[r_idx, 0].set_title(f"Parent: {parent_id}", fontsize=9, color="darkblue")
            axes[r_idx, 0].axis("off")
            
            # Find children mapped to this parent
            children = [row for row in genus_lineage if row["parent_specimen_id"] == parent_id and row["verification_status"] == "VERIFIED"]
            sample_children = children[:5]
            for c_idx in range(5):
                ax = axes[r_idx, c_idx + 1]
                if c_idx < len(sample_children):
                    child_rel = sample_children[c_idx]["augmented_image"]
                    child_path = os.path.join("/home/nimr/Projects/mosqscan", child_rel)
                    c_img = Image.open(child_path).resize((224, 224))
                    ax.imshow(c_img)
                    ax.set_title(f"Child #{c_idx+1}\nScore: {sample_children[c_idx]['similarity_score']}", fontsize=8)
                else:
                    ax.text(0.5, 0.5, "N/A", ha="center", va="center")
                ax.axis("off")
                
        plt.tight_layout()
        sheet_path = os.path.join(CONTACT_SHEETS_DIR, f"contact_sheet_{genus.lower()}.png")
        plt.savefig(sheet_path, dpi=120)
        plt.close(fig)
        print(f"  Saved contact sheet to {sheet_path}")
        
        # Summary for genus
        verified_count = sum(1 for r in genus_lineage if r["verification_status"] == "VERIFIED")
        high_conf = sum(1 for r in genus_lineage if r["mapping_confidence"] == "HIGH")
        med_conf = sum(1 for r in genus_lineage if r["mapping_confidence"] == "MEDIUM")
        low_conf = sum(1 for r in genus_lineage if r["mapping_confidence"] == "LOW")
        
        genus_summary[genus] = {
            "original_count": len(orig_files),
            "augmented_count": len(aug_files),
            "verified_count": verified_count,
            "high_confidence": high_conf,
            "medium_confidence": med_conf,
            "low_confidence": low_conf,
        }
        print(f"  Summary {genus}: Verified={verified_count}/{len(aug_files)} (High={high_conf}, Med={med_conf}, Low={low_conf})")

    # 4. Save Lineage CSV
    lineage_csv = os.path.join(METADATA_DIR, "augmentation_lineage.csv")
    with open(lineage_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "augmented_image", "genus", "parent_specimen_id", "similarity_score",
            "matching_method", "top1_sift_matches", "top2_sift_matches",
            "phash_distance", "mapping_confidence", "verification_status"
        ])
        writer.writeheader()
        writer.writerows(all_lineage)
    print(f"\nSaved lineage CSV: {lineage_csv} ({len(all_lineage)} rows)")
    
    # 5. Save Quality Metrics CSV
    quality_csv = os.path.join(METADATA_DIR, "data_quality_metrics.csv")
    with open(quality_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "file_path", "file_name", "dataset_type", "genus", "specimen_id",
            "file_size_bytes", "sha256", "pil_valid", "cv_valid", "width", "height",
            "channels", "blur_laplacian_var", "mean_luminance", "underexposed_ratio",
            "overexposed_ratio"
        ])
        writer.writeheader()
        writer.writerows(all_quality)
    print(f"Saved quality CSV: {quality_csv} ({len(all_quality)} rows)")
    
    # 6. Save Dataset Manifest JSON
    manifest_json = os.path.join(METADATA_DIR, "dataset_manifest.json")
    with open(manifest_json, "w") as f:
        json.dump(all_manifest, f, indent=2)
    print(f"Saved dataset manifest: {manifest_json}")
    
    # 7. Check for Duplicates
    duplicate_rows = []
    for h, files in hash_to_files.items():
        if len(files) > 1:
            for f in files:
                duplicate_rows.append({"sha256": h, "file_path": f})
    dup_csv = os.path.join(METADATA_DIR, "duplicate_report.csv")
    with open(dup_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["sha256", "file_path"])
        writer.writeheader()
        writer.writerows(duplicate_rows)
    print(f"Saved duplicate report: {dup_csv} ({len(duplicate_rows)} duplicate occurrences)")
    
    # 8. Save Class Distribution Summary
    dist_json = os.path.join(METADATA_DIR, "class_distribution.json")
    with open(dist_json, "w") as f:
        json.dump(genus_summary, f, indent=2)
    print(f"Saved class distribution summary: {dist_json}")
    
    t_end = time.time()
    print("=" * 70)
    print(f"PIPELINE COMPLETED SUCCESSFULLY IN {t_end - t_start:.2f} SECONDS")
    print("=" * 70)

if __name__ == "__main__":
    run_pipeline()
