# Vectora AI 3.0 — Classifier Training and Staged Fine-Tuning Report

**Date:** 2026-11-12  
**Platform:** Intel Core i7-2600 Workstation (16 GB RAM)  
**Standard:** ASD-STE100  
**Status:** Complete  

---

## 1. Executive Summary

This report documents the machine learning training methodology, staged fine-tuning strategy, loss function formulations, and class balancing applied to Vectora AI 3.0.

The training objective is to produce a robust mosquito genus classifier capable of identifying *Aedes*, *Anopheles*, and *Culex* adult specimens from high-resolution macroscopic photographs.

To ensure scientific integrity and prevent synthetic distribution distortion:
1. All baseline ImageNet models were initialized from standard PyTorch weights (`DEFAULT`). No candidate was initialized from Experiment B checkpoints.
2. Only original specimens (44 photographs) and high/medium-confidence verified augmentations (2,425 photographs) were used. The 215 unconfirmed synthetic images were strictly excluded.
3. Group-aware splitting (`StratifiedGroupKFold`) guaranteed that all synthetic variations of a specimen stayed within the same fold as their parent specimen, eliminating data leakage.

---

## 2. Dataset Partitioning and Provenance Filtering

### 2.1 Class Distribution in Training

The raw distribution across the 44 original photographic specimens exhibits moderate class imbalance:
- *Aedes*: 15 specimens (34.1%)
- *Anopheles*: 9 specimens (20.5%)
- *Culex*: 20 specimens (45.4%)

The synthetic augmented archive contains 2,640 images (60 variations per specimen). However, our SIFT and perceptual hashing lineage sweep identified 215 images with ambiguous keypoint matches ($< 15$ inliers or margin $< 1.15$).

| Genus | Original Photographs | Verified Augmentations | Excluded (Unconfirmed) | Total Usable Images |
| :--- | :--- | :--- | :--- | :--- |
| **Aedes** | 15 | 783 (87.0%) | 117 (13.0%) | 798 |
| **Anopheles** | 9 | 522 (96.7%) | 18 (3.3%) | 531 |
| **Culex** | 20 | 1,120 (93.3%) | 80 (6.7%) | 1,140 |
| **Total** | **44** | **2,425 (91.86%)** | **215 (8.14%)** | **2,469** |

Only verified images were permitted into the training pipeline.

---

## 3. Class Weighting and Loss Formulation

### 3.1 Inverse Frequency Weighting

To prevent the dominant *Culex* and *Aedes* classes from suppressing *Anopheles* detection (which is critical for malaria surveillance), we computed inverse class frequency weights:

$$w_c = \frac{N_{\text{total}}}{3 \cdot N_c}$$

For the balanced training partitions, the class weights applied to the cross-entropy loss are:
- $w_{\text{aedes}} \approx 0.98$
- $w_{\text{anopheles}} \approx 1.63$
- $w_{\text{culex}} \approx 0.73$

### 3.2 Loss Function

The training loss is weighted multi-class cross-entropy:

$$\mathcal{L}_{\text{CE}} = - \sum_{c=1}^{3} w_c \cdot y_c \log(\hat{y}_c)$$

where $y_c \in \{0, 1\}$ is the one-hot ground-truth label and $\hat{y}_c$ is the softmax probability output by the classifier head.

---

## 4. Staged Fine-Tuning Progression

Fine-tuning deep convolutional networks on a small dataset (44 biological specimens) carries a high risk of catastrophic forgetting and severe gradient degradation. We implemented a two-stage training strategy:

```
[Input Image (224x224 RGB)]
             │
             ▼
┌─────────────────────────┐
│     CNN Backbone        │  Stage 1: Frozen completely
│  (Stages 0 to 6)        │  Stage 2: Frozen (preserves generic filters)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   Top Feature Block     │  Stage 1: Frozen
│  (Stage 7 / MBConv)     │  Stage 2: Unfrozen (lr = 2e-5, weight_decay = 1e-4)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│     Classifier Head     │  Stage 1: Unfrozen (lr = 1e-3, AdamW)
│  Linear(1280 -> 3)      │  Stage 2: Fine-tuned (lr = 2e-4, AdamW)
└─────────────────────────┘
```

### 4.1 Stage 1: Classifier Head Alignment
- **Backbone Parameters:** All convolutional feature extractors are frozen (`requires_grad = False`).
- **Head Parameters:** Replaced final 1000-class ImageNet linear projection with a 3-class linear head.
- **Optimizer:** AdamW with learning rate $\eta = 1 \times 10^{-3}$, weight decay $\lambda = 1 \times 10^{-4}$.
- **Objective:** Rapidly align the random classification weights with the pretrained visual representations without distorting backbone convolutional kernels.

### 4.2 Stage 2: Top Block Fine-Tuning
- **Unfrozen Layers:** The final inverted residual block (EfficientNet Stage 7: `features[7]`, or MobileNetV3 `features[-1]`) and the classifier head.
- **Differential Learning Rates:**
  - Backbone Top Layer: $\eta_{\text{backbone}} = 2 \times 10^{-5}$
  - Classification Head: $\eta_{\text{head}} = 2 \times 10^{-4}$
- **Optimizer:** AdamW with weight decay $\lambda = 1 \times 10^{-4}$.
- **Objective:** Adapt high-level visual features (scale patterns, leg banding, wing vein geometry) specifically for culicid morphology.

---

## 5. Regularization and Data Augmentation

During training batches, lightweight online spatial and photometric augmentations were applied to prevent memorization of synthetic backgrounds:
- **Random Horizontal Flip:** $p = 0.5$
- **Random Rotation:** Uniform distribution $\theta \in [-10^\circ, +10^\circ]$
- **Color Jitter:** Brightness $\pm 10\%$, Contrast $\pm 10\%$, Saturation $\pm 5\%$
- **Normalization:** Standard ImageNet channel means $\mu = (0.485, 0.456, 0.406)$ and standard deviations $\sigma = (0.229, 0.224, 0.225)$.

Validation evaluation strictly applied deterministic resizing and normalization without random transformations.

---

## 6. Training Verification and Checkpoints

The final trained weights were saved to:
`models/v3/vectora_v3_best.pt`

The PyTorch checkpoint stores the complete state dictionary of the winning candidate architecture, ready for ONNX export and runtime deployment.
