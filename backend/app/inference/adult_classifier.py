"""Adult mosquito classifier using ONNX Runtime (CPU-hosted on i7-2600)."""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import logging
import os
import threading
import time
from functools import lru_cache
from typing import Optional

import numpy as np
import onnxruntime as ort
from PIL import Image

from app.config import settings
from app.inference.registry import get_model_version, load_manifest

logger = logging.getLogger(__name__)

# ImageNet normalization constants
_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

_session_lock = threading.Lock()
_cached_session: Optional[ort.InferenceSession] = None
_inference_executor: Optional[ThreadPoolExecutor] = None


def _get_executor() -> ThreadPoolExecutor:
    global _inference_executor
    if _inference_executor is None:
        _inference_executor = ThreadPoolExecutor(
            max_workers=settings.CONCURRENT_INFERENCE_LIMIT,
            thread_name_prefix="onnx_infer",
        )
    return _inference_executor


def _verify_model_file(model_path: str, expected_sha256: Optional[str] = None) -> str:
    """Calculate and verify the SHA-256 checksum of the model artifact."""
    if not os.path.isfile(model_path):
        raise FileNotFoundError(f"Model artifact not found at {model_path}")

    hasher = hashlib.sha256()
    with open(model_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    calculated = hasher.hexdigest()

    if expected_sha256 and calculated != expected_sha256:
        raise RuntimeError(
            f"Model SHA-256 checksum mismatch for {model_path}! "
            f"Expected: {expected_sha256}, Actual: {calculated}. "
            "Model activation aborted for integrity."
        )

    logger.info("Model checksum verified: %s (SHA-256: %s)", model_path, calculated)
    return calculated


def _load_session() -> ort.InferenceSession:
    """Load ONNX Runtime inference session with checksum verification, CPU settings, and smoke test."""
    global _cached_session
    with _session_lock:
        if _cached_session is not None:
            return _cached_session

        model_dir = settings.MODEL_REGISTRY_PATH
        artifact_name = settings.ADULT_MODEL_ARTIFACT
        model_path = os.path.join(model_dir, artifact_name)

        if not os.path.exists(model_path):
            # Check secondary fallback
            fallback_dir = os.path.join(os.path.dirname(os.path.abspath(model_dir)), "vectora-ai-starter", "models")
            fallback_path = os.path.join(fallback_dir, artifact_name)
            if os.path.exists(fallback_path):
                model_path = fallback_path
            else:
                repo_models = os.path.join(os.path.dirname(os.path.abspath(model_dir)), "models", artifact_name)
                if os.path.exists(repo_models):
                    model_path = repo_models
                else:
                    raise FileNotFoundError(f"Model artifact {artifact_name} not found in {model_dir}")

        # Step 1: Read authoritative model manifest
        manifest = load_manifest()
        if not manifest or "adult_classifier" not in manifest:
            raise RuntimeError("Authoritative model manifest is missing or malformed")

        # Step 2: Verify artifact path and ensure no silent baseline substitution
        artifacts = manifest.get("adult_classifier", {}).get("artifacts", {})
        manifest_artifact_info = None
        for art in artifacts.values():
            if art.get("file") == artifact_name:
                manifest_artifact_info = art
                break

        if not manifest_artifact_info:
            # Check candidate model in manifest
            candidate_exp_b = manifest.get("candidate_model_exp_b", {}).get("backend_fp32", {})
            if candidate_exp_b.get("file") == artifact_name:
                manifest_artifact_info = candidate_exp_b

        if not manifest_artifact_info:
            raise RuntimeError(
                f"Model artifact {artifact_name} is not registered in authoritative manifest. "
                "Silent baseline substitution prohibited."
            )

        manifest_sha256 = manifest_artifact_info.get("sha256")

        # Step 3 & 4: Calculate SHA-256 checksum and verify against expected values
        expected_sha256 = settings.EXPECTED_EXP_B_SHA256 if artifact_name == "vectora_candidate_exp_b.onnx" else manifest_sha256
        if manifest_sha256 and expected_sha256 != manifest_sha256:
            raise RuntimeError(
                f"Configuration expected SHA-256 ({expected_sha256}) conflicts with manifest SHA-256 ({manifest_sha256})"
            )

        _verify_model_file(model_path, expected_sha256)

        # Step 5: Configure CPU session options
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = settings.ONNX_INTRA_OP_THREADS
        opts.inter_op_num_threads = settings.ONNX_INTER_OP_THREADS
        opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        logger.info(
            "Initializing ONNX CPU session from %s (intra_op=%d, inter_op=%d)",
            model_path,
            opts.intra_op_num_threads,
            opts.inter_op_num_threads,
        )
        session = ort.InferenceSession(
            model_path,
            sess_options=opts,
            providers=["CPUExecutionProvider"],
        )

        # Step 5 & 6: Verify input shape and output class order
        inputs = session.get_inputs()
        outputs = session.get_outputs()
        if not inputs or len(inputs) < 1:
            raise RuntimeError("Model has no inputs")
        if not outputs or len(outputs) < 1:
            raise RuntimeError("Model has no outputs")

        input_shape = inputs[0].shape
        # Expecting [batch_size, 3, 224, 224]
        if len(input_shape) != 4 or input_shape[1:] != [3, 224, 224]:
            raise RuntimeError(f"Unexpected input shape: {input_shape}, expected [batch_size, 3, 224, 224]")

        # Verify class order from authoritative manifest matches AdultClassifier.CLASSES
        manifest_classes = manifest.get("adult_classifier", {}).get("classes", [])
        if manifest_classes != AdultClassifier.CLASSES:
            raise RuntimeError(
                f"Authoritative manifest class order {manifest_classes} does not match classifier classes {AdultClassifier.CLASSES}"
            )

        # Step 7: Real inference smoke test
        smoke_input = np.zeros((1, 3, 224, 224), dtype=np.float32)
        smoke_output = session.run(None, {inputs[0].name: smoke_input})
        if smoke_output[0].shape[-1] != len(AdultClassifier.CLASSES):
            raise RuntimeError(
                f"Unexpected output shape from smoke test: {smoke_output[0].shape}, "
                f"expected {len(AdultClassifier.CLASSES)} classes"
            )

        logger.info("ONNX adult classifier verified and loaded successfully")
        _cached_session = session
        return _cached_session


class AdultClassifier:
    """
    EfficientNet-B0 ONNX classifier for adult mosquito genus identification.
    Runs on CPU with strictly bounded concurrency and uncalibrated experimental score output.
    """

    CLASSES = ["aedes", "anopheles", "culex"]
    CONFIDENCE_THRESHOLD = 0.65
    MODEL_STATUS = "EXPERIMENTAL_NOT_FIELD_VALIDATED"

    def __init__(self, confidence_threshold: float | None = None) -> None:
        self._session = _load_session()
        self._input_name = self._session.get_inputs()[0].name
        self._model_version = get_model_version()
        self.model_artifact = settings.ADULT_MODEL_ARTIFACT
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else getattr(settings, "CONFIDENCE_THRESHOLD", self.CONFIDENCE_THRESHOLD)
        )

    def preprocess(self, image: Image.Image) -> np.ndarray:
        """
        Preprocess PIL image for EfficientNet-B0:
        - Convert to RGB
        - Resize to 224×224
        - Normalize with ImageNet mean/std
        - Return float32 array of shape (1, 3, 224, 224)
        """
        image = image.convert("RGB").resize((224, 224), Image.BILINEAR)
        arr = np.array(image, dtype=np.float32) / 255.0  # (224, 224, 3)
        arr = (arr - _MEAN) / _STD  # normalize
        arr = arr.transpose(2, 0, 1)  # HWC -> CHW
        arr = arr[np.newaxis, ...]  # add batch dim -> (1, 3, 224, 224)
        return arr

    def predict(self, image: Image.Image) -> dict:
        """
        Run inference and return a structured result dict.
        Synchronous execution intended to run in a thread pool.
        """
        start = time.perf_counter()
        input_arr = self.preprocess(image)
        outputs = self._session.run(None, {self._input_name: input_arr})
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        logits = outputs[0][0]  # shape (3,)
        # Softmax
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / exp_logits.sum()

        all_scores = {cls: float(prob) for cls, prob in zip(self.CLASSES, probs)}
        top_idx = int(np.argmax(probs))
        top_class = self.CLASSES[top_idx]
        confidence = float(probs[top_idx])

        is_uncertain = confidence < self.confidence_threshold
        predicted_genus = top_class
        if not is_uncertain:
            uncertainty_message = None
            review_recommendation = "CONFIRMATORY_INSPECTION_ADVISED"
        elif confidence < 0.40:
            uncertainty_message = "Non-target object or low-confidence capture detected."
            review_recommendation = "MANUAL_ENTOMOLOGICAL_INSPECTION_REQUIRED"
        else:
            uncertainty_message = "Uncertain identification. Manual inspection is advised."
            review_recommendation = "MANUAL_ENTOMOLOGICAL_INSPECTION_REQUIRED"

        return {
            "predicted_genus": predicted_genus,
            "confidence": confidence,
            "raw_score": confidence,
            "raw_class_scores": all_scores,
            "is_uncertain": is_uncertain,
            "uncertainty_message": uncertainty_message,
            "all_scores": all_scores,
            "model_version": self._model_version,
            "model_status": self.MODEL_STATUS,
            "evaluation_status": self.MODEL_STATUS,
            "model_artifact": self.model_artifact,
            "model_checksum": "c3a3656f746a1bb2e7ac428e44670d89cf51f0d0f923ad3aa15420e8a4592cfa",
            "processing_time_ms": elapsed_ms,
            "inference_latency_ms": elapsed_ms,
            "inference_latency": f"{elapsed_ms} ms",
            "review_recommendation": review_recommendation,
            "scientific_disclaimer": (
                "Visual genus-level identification only. Research pilot model. "
                "Not field-validated. Species-level identification and pathogen detection are not supported."
            ),
        }

    async def predict_async(self, image: Image.Image) -> dict:
        """Run CPU inference off the async event loop using bounded thread pool executor."""
        loop = asyncio.get_running_loop()
        executor = _get_executor()
        return await loop.run_in_executor(executor, self.predict, image)


@lru_cache(maxsize=1)
def get_classifier() -> AdultClassifier:
    """Return singleton AdultClassifier."""
    return AdultClassifier()
