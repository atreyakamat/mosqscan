"""Assistant Service integrating local Ollama Gemma 3:4B into Vectora AI."""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException, status

from app.config import settings

logger = logging.getLogger("vectora.assistant")

GUARDRAIL_SYSTEM_INSTRUCTION = (
    "You are the Vectora AI Technical Research Assistant, running locally on an Intel Core i7-2600. "
    "Follow these strict operational rules:\n"
    "1. Adhere to ASD-STE100 principles: use clear, active, concise, unambiguous technical language.\n"
    "2. Strict Guardrail: You are strictly an advisory tool. You cannot calculate official evaluation metrics, "
    "modify production model checkpoints, or change dataset partitions.\n"
    "3. Hardware awareness: The host machine is an Intel Core i7-2600 (4 cores, 8 threads, AVX, no AVX2, "
    "16GB DDR3 RAM, no GPU). All training and inference must respect CPU threading and memory limits.\n"
    "4. When asked for structured JSON, output strictly valid JSON without extra markdown wrapping unless requested."
)


class AssistantService:
    def __init__(self) -> None:
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT_SECONDS

    async def check_health(self) -> Dict[str, Any]:
        """Check Ollama connectivity and whether target model is available."""
        url = f"{self.base_url}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return {
                        "status": "degraded",
                        "ollama_base_url": self.base_url,
                        "target_model": self.model,
                        "model_loaded": False,
                        "available_models": [],
                        "error": f"Ollama returned HTTP {resp.status_code}",
                    }
                data = resp.json()
                models = [m.get("name") for m in data.get("models", [])]
                model_loaded = any(self.model in m for m in models)
                return {
                    "status": "healthy" if model_loaded else "model_missing",
                    "ollama_base_url": self.base_url,
                    "target_model": self.model,
                    "model_loaded": model_loaded,
                    "available_models": models,
                }
        except httpx.ConnectError:
            logger.warning("Ollama service unreachable at %s", self.base_url)
            return {
                "status": "unavailable",
                "ollama_base_url": self.base_url,
                "target_model": self.model,
                "model_loaded": False,
                "available_models": [],
                "error": f"Cannot connect to Ollama at {self.base_url}. Service may be stopped (Mode B).",
            }
        except Exception as exc:
            logger.error("Error checking Ollama health: %s", exc)
            return {
                "status": "error",
                "ollama_base_url": self.base_url,
                "target_model": self.model,
                "model_loaded": False,
                "available_models": [],
                "error": str(exc),
            }

    async def _call_ollama(
        self,
        prompt: str,
        system: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """Call Ollama /api/generate endpoint."""
        url = f"{self.base_url}/api/generate"
        full_system = f"{GUARDRAIL_SYSTEM_INSTRUCTION}\n\n{system}" if system else GUARDRAIL_SYSTEM_INSTRUCTION
        
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "system": full_system,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": 4096,
            },
        }
        if json_mode:
            payload["format"] = "json"

        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail={
                            "error_code": "OLLAMA_GATEWAY_ERROR",
                            "message": f"Ollama returned HTTP {resp.status_code}: {resp.text}",
                        },
                    )
                data = resp.json()
        except httpx.ConnectError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error_code": "LOCAL_AI_UNAVAILABLE",
                    "message": (
                        f"Local AI assistant is currently offline at {self.base_url}. "
                        "Ensure Mode A is running (docker compose --profile llm up -d ollama)."
                    ),
                },
            )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail={
                    "error_code": "LOCAL_AI_TIMEOUT",
                    "message": f"Ollama generation timed out after {self.timeout}s on CPU.",
                },
            )
        except Exception as exc:
            if isinstance(exc, HTTPException):
                raise
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error_code": "LOCAL_AI_ERROR",
                    "message": f"Unexpected error during Ollama invocation: {str(exc)}",
                },
            )

        duration_ms = (time.perf_counter() - t0) * 1000.0
        response_text = data.get("response", "")
        
        structured_json = None
        if json_mode:
            try:
                structured_json = json.loads(response_text)
            except Exception:
                structured_json = None

        return {
            "success": True,
            "model": self.model,
            "duration_ms": round(duration_ms, 2),
            "response": response_text,
            "structured_json": structured_json,
        }

    async def query(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """General inquiry to Gemma 3:4B."""
        return await self._call_ollama(
            prompt=prompt,
            system=system_prompt,
            json_mode=json_mode,
            temperature=temperature,
        )

    async def review_report(
        self,
        report_title: str,
        report_content: str,
        focus_areas: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Review technical report for ASD-STE100 compliance, scientific claims, and clarity."""
        areas_str = ", ".join(focus_areas) if focus_areas else "ASD-STE100, scientific precision, statistical claims"
        prompt = (
            f"Review the following technical document: '{report_title}'.\n"
            f"Focus Areas: {areas_str}.\n\n"
            f"Document Text:\n{report_content}\n\n"
            "Provide structured feedback in JSON format with keys:\n"
            "- 'title': Document title\n"
            "- 'ste100_compliance': Comments on sentence brevity and active voice\n"
            "- 'scientific_rigor': Verification of claims and statistical framing\n"
            "- 'recommended_edits': List of specific text improvements\n"
            "- 'status': One of 'APPROVED', 'CHANGES_REQUESTED', 'CAUTION'\n"
        )
        return await self._call_ollama(
            prompt=prompt,
            system="You are an expert technical editor specialized in aerospace/biomedical ASD-STE100 technical writing.",
            json_mode=True,
            temperature=0.1,
        )

    async def interpret_training_log(
        self,
        log_content: str,
        architecture: str = "EfficientNet-B0",
        num_folds: int = 4,
    ) -> Dict[str, Any]:
        """Interpret classifier training logs and loss curves."""
        prompt = (
            f"Analyze the following training log for {architecture} across {num_folds} folds.\n\n"
            f"Log excerpt:\n{log_content}\n\n"
            "Provide structured assessment in JSON format with keys:\n"
            "- 'convergence_status': Observation on loss reduction\n"
            "- 'overfitting_risk': Assessment of train vs validation gap\n"
            "- 'fold_variability': Assessment of consistency across splits\n"
            "- 'anomalies_detected': List of unexpected behaviors (e.g. stalled loss, high variance)\n"
            "- 'recommendations': Actionable guidance for hyperparameter or regularization adjustments\n"
        )
        return await self._call_ollama(
            prompt=prompt,
            system="You are a machine learning engineering assistant analyzing CPU training runs.",
            json_mode=True,
            temperature=0.1,
        )

    async def audit_script(
        self,
        script_name: str,
        script_content: str,
        hardware_target: str = "Intel Core i7-2600",
    ) -> Dict[str, Any]:
        """Audit Python script for concurrency, thread limits, memory leaks, and specimen leakage."""
        prompt = (
            f"Audit the Python script '{script_name}' targeting {hardware_target}.\n\n"
            f"Script Content:\n{script_content}\n\n"
            "Analyze and output structured JSON with keys:\n"
            "- 'hardware_safety': Check torch thread limits (max 3), worker counts (0), batch size\n"
            "- 'data_leakage_risk': Check if physical specimen IDs are grouped properly to avoid leakage\n"
            "- 'resource_leak_risk': Check file descriptor, memory caching, or process management issues\n"
            "- 'safety_rating': 'SAFE', 'WARNING', or 'UNSAFE'\n"
            "- 'findings': List of specific code findings\n"
        )
        return await self._call_ollama(
            prompt=prompt,
            system="You are an ML systems auditor specializing in constrained CPU deployment and safety.",
            json_mode=True,
            temperature=0.1,
        )

    async def review_experiment_config(
        self,
        experiment_name: str,
        config_details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Review an experiment configuration dictionary."""
        prompt = (
            f"Review experiment configuration for '{experiment_name}'.\n"
            f"Configuration: {json.dumps(config_details, indent=2)}\n\n"
            "Output JSON with keys:\n"
            "- 'validity': boolean\n"
            "- 'cpu_suitability': Analysis of CPU threads, batch size, image dimensions\n"
            "- 'risk_level': 'LOW', 'MEDIUM', 'HIGH'\n"
            "- 'notes': List of recommendations\n"
        )
        return await self._call_ollama(
            prompt=prompt,
            system="You are an ML experiment planner verifying configuration safety.",
            json_mode=True,
            temperature=0.1,
        )

    async def explain_result(
        self,
        genus: str,
        raw_scores: Optional[Dict[str, float]] = None,
        scan_id: Optional[str] = None,
        quality_feedback: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Explain a returned ONNX classification in plain language with scientific guardrails."""
        scores_str = json.dumps(raw_scores) if raw_scores else "N/A"
        prompt = (
            f"The Vectora AI ONNX model classified a specimen as genus '{genus}'.\n"
            f"Scan ID: {scan_id or 'N/A'}\n"
            f"Raw scores: {scores_str}\n"
            f"Image feedback: {quality_feedback or 'Acceptable'}\n\n"
            "Explain in plain, clear language:\n"
            "1. Two typical morphological characteristics of this genus.\n"
            "2. Note that the output score is an uncalibrated experimental estimate, not diagnostic certainty.\n"
            "3. State clearly that confirmatory entomological or PCR inspection is recommended.\n"
            "Do NOT alter or dispute the ONNX model classification. Keep response under 100 words."
        )
        return await self._call_ollama(
            prompt=prompt,
            system=(
                "You are an educational vector biology assistant. "
                "Explain model findings clearly. Never override or alter the ONNX prediction."
            ),
            json_mode=False,
            temperature=0.2,
        )

    async def summarize_history(
        self,
        submissions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Summarize user scan histories in plain language."""
        summary_data = []
        for s in submissions[:20]:  # limit to recent 20
            r = s.get("result") or {}
            summary_data.append({
                "id": s.get("id"),
                "created_at": s.get("created_at"),
                "predicted_genus": r.get("predicted_genus"),
                "raw_score": r.get("raw_score") or r.get("confidence"),
                "is_uncertain": r.get("is_uncertain", False),
            })
        prompt = (
            f"Summarize the following recent mosquito scan history:\n"
            f"{json.dumps(summary_data, indent=2)}\n\n"
            "Provide a concise summary: total scans, breakdown by genus, count of uncertain scans, "
            "and reminders that all results are experimental. Keep under 100 words."
        )
        return await self._call_ollama(
            prompt=prompt,
            system="You are a helpful research dashboard assistant.",
            json_mode=False,
            temperature=0.2,
        )


assistant_service = AssistantService()
