from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
import numpy as np
from PIL import Image

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import onnxruntime as ort
except ImportError:
    ort = None

CLASSES = ("aedes", "anopheles", "culex")
DEFAULT_THRESHOLD = 0.50
MIN_LAPLACIAN_VARIANCE = 2.0  # Quality threshold for severe blur detection

VECTOR_METADATA = {
    "aedes": {
        "display_name": "Aedes",
        "candidate_vectors": ["Aedes aegypti", "Aedes albopictus"],
        "known_pathogen_associations": ["Dengue", "Chikungunya", "Zika", "Yellow Fever"],
        "scientific_disclaimer": "Visual identification only. Does not indicate individual pathogen infection.",
    },
    "anopheles": {
        "display_name": "Anopheles",
        "candidate_vectors": ["Anopheles stephensi", "Anopheles culicifacies"],
        "known_pathogen_associations": ["Malaria (Plasmodium vivax, P. falciparum)"],
        "scientific_disclaimer": "Visual identification only. Does not indicate individual pathogen infection.",
    },
    "culex": {
        "display_name": "Culex",
        "candidate_vectors": ["Culex quinquefasciatus", "Culex pipiens"],
        "known_pathogen_associations": ["Lymphatic Filariasis", "West Nile Virus", "Japanese Encephalitis"],
        "scientific_disclaimer": "Visual identification only. Does not indicate individual pathogen infection.",
    },
}


def check_image_quality(image_np: np.ndarray) -> Tuple[bool, float, str]:
    """Check image sharpness using Laplacian variance."""
    if cv2 is None:
        return True, 100.0, "OpenCV not available; blur check skipped."
    if len(image_np.shape) == 3:
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
    else:
        gray = image_np
    variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    if variance < MIN_LAPLACIAN_VARIANCE:
        return False, variance, f"Image is too blurry (sharpness score {variance:.1f} < {MIN_LAPLACIAN_VARIANCE})."
    return True, variance, f"Sharpness score: {variance:.1f}"


def preprocess_image(image: Image.Image, target_size: int = 224) -> Tuple[np.ndarray, np.ndarray]:
    """
    Standardize image preprocessing across Android, Web, and Python backends:
    1. Convert to RGB.
    2. Resize to (target_size, target_size) using Bilinear interpolation.
    3. Normalize to [0, 1].
    4. Standardize with ImageNet mean and std.
    5. Transpose to [1, 3, target_size, target_size].
    """
    rgb_img = image.convert("RGB")
    raw_np = np.array(rgb_img)

    resized = rgb_img.resize((target_size, target_size), Image.Resampling.BILINEAR)
    arr = np.array(resized).astype(np.float32) / 255.0

    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    normalized = (arr - mean) / std

    # HWC to CHW -> [1, 3, H, W]
    tensor = np.transpose(normalized, (2, 0, 1))[np.newaxis, ...]
    return tensor, raw_np


class VectoraInferenceEngine:
    def __init__(self, onnx_model_path: Union[str, Path], confidence_threshold: float = DEFAULT_THRESHOLD):
        self.onnx_model_path = Path(onnx_model_path)
        self.confidence_threshold = confidence_threshold
        if ort is None:
            raise RuntimeError("onnxruntime is required for VectoraInferenceEngine")
        if not self.onnx_model_path.exists():
            raise FileNotFoundError(f"Model file not found: {self.onnx_model_path}")
        
        # Load ONNX session with CPUExecutionProvider
        self.session = ort.InferenceSession(str(self.onnx_model_path), providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

    def predict(self, image_input: Union[str, Path, bytes, Image.Image]) -> Dict[str, Any]:
        """
        Unified inference method matching the production API response contract.
        """
        # Load PIL image
        if isinstance(image_input, (str, Path)):
            with Image.open(image_input) as img:
                pil_image = img.copy()
        elif isinstance(image_input, bytes):
            with Image.open(io.BytesIO(image_input)) as img:
                pil_image = img.copy()
        elif isinstance(image_input, Image.Image):
            pil_image = image_input
        else:
            raise ValueError(f"Unsupported image input type: {type(image_input)}")

        # 1. Image preprocessing and quality audit
        input_tensor, raw_np = preprocess_image(pil_image, target_size=224)
        is_sharp, sharpness_score, quality_msg = check_image_quality(raw_np)

        if not is_sharp:
            return {
                "status": "REJECTED_BLURRY",
                "predicted_genus": None,
                "confidence": 0.0,
                "probabilities": {c: 0.0 for c in CLASSES},
                "quality_metrics": {
                    "is_sharp": False,
                    "sharpness_score": round(sharpness_score, 2),
                    "message": quality_msg,
                },
                "guidance": "Specimen is out of focus. Hold phone steady, tap to focus on the mosquito body, and retake the photo.",
                "model_version": self.onnx_model_path.stem,
            }

        # 2. Forward pass via ONNX Runtime
        outputs = self.session.run([self.output_name], {self.input_name: input_tensor})
        logits = outputs[0][0]  # shape (3,)

        # 3. Softmax calculation
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / exp_logits.sum()

        top_idx = int(np.argmax(probs))
        top_conf = float(probs[top_idx])
        top_class = CLASSES[top_idx]
        all_probs = {c: round(float(probs[i]), 4) for i, c in enumerate(CLASSES)}

        # 4. Uncertainty & Rejection Policy
        if top_conf < self.confidence_threshold:
            return {
                "status": "UNCERTAIN_LOW_CONFIDENCE",
                "predicted_genus": None,
                "confidence": round(top_conf, 4),
                "probabilities": all_probs,
                "quality_metrics": {
                    "is_sharp": True,
                    "sharpness_score": round(sharpness_score, 2),
                    "message": quality_msg,
                },
                "guidance": f"Identification confidence ({top_conf*100:.1f}%) is below acceptance threshold ({self.confidence_threshold*100:.1f}%). Specimen cannot be reliably distinguished. Ensure good lighting and fill the frame with the mosquito.",
                "model_version": self.onnx_model_path.stem,
            }

        # 5. Confident Identification
        meta = VECTOR_METADATA.get(top_class, {})
        return {
            "status": "IDENTIFIED",
            "predicted_genus": top_class,
            "display_name": meta.get("display_name", top_class.capitalize()),
            "confidence": round(top_conf, 4),
            "probabilities": all_probs,
            "vector_context": {
                "candidate_vectors": meta.get("candidate_vectors", []),
                "known_diseases": meta.get("known_pathogen_associations", []),
                "disclaimer": meta.get("scientific_disclaimer", ""),
            },
            "quality_metrics": {
                "is_sharp": True,
                "sharpness_score": round(sharpness_score, 2),
                "message": quality_msg,
            },
            "model_version": self.onnx_model_path.stem,
        }


def main():
    parser = argparse.ArgumentParser(description="Vectora AI Unified Inference Engine")
    parser.add_argument("--image", type=Path, required=True, help="Path to input specimen image")
    parser.add_argument("--model", type=Path, default=Path("models/vectora_candidate_exp_b_int8.onnx"), help="Path to ONNX model")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD, help="Confidence threshold")
    args = parser.parse_args()

    engine = VectoraInferenceEngine(args.model, confidence_threshold=args.threshold)
    result = engine.predict(args.image)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
