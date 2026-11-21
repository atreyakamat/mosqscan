"""API endpoints for Vectora AI Local AI Assistant."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.schemas.assistant import (
    AssistantHealthResponse,
    AssistantQueryRequest,
    AssistantResponse,
    AuditScriptReviewRequest,
    ExperimentConfigReviewRequest,
    ExplainResultRequest,
    ReportReviewRequest,
    SummarizeHistoryRequest,
    TrainingLogInterpretationRequest,
)
from app.services.assistant_service import assistant_service

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.get("/health", response_model=AssistantHealthResponse)
async def get_assistant_health():
    """Check health and availability of the local Ollama Gemma 3:4B service."""
    res = await assistant_service.check_health()
    return AssistantHealthResponse(
        status=res.get("status", "unknown"),
        ollama_base_url=res.get("ollama_base_url", ""),
        target_model=res.get("target_model", ""),
        model_loaded=res.get("model_loaded", False),
        available_models=res.get("available_models", []),
    )


@router.post("/chat", response_model=AssistantResponse)
async def chat_with_assistant(req: AssistantQueryRequest):
    """General query to local Gemma 3:4B assistant."""
    result = await assistant_service.query(
        prompt=req.prompt,
        system_prompt=req.system_prompt,
        json_mode=req.json_mode,
        temperature=req.temperature,
    )
    return AssistantResponse(**result)


@router.post("/review-report", response_model=AssistantResponse)
async def review_technical_report(req: ReportReviewRequest):
    """Review technical reports for ASD-STE100 compliance and scientific clarity."""
    result = await assistant_service.review_report(
        report_title=req.report_title,
        report_content=req.report_content,
        focus_areas=req.focus_areas,
    )
    return AssistantResponse(**result)


@router.post("/interpret-log", response_model=AssistantResponse)
async def interpret_training_log(req: TrainingLogInterpretationRequest):
    """Analyze and interpret training logs and loss curves."""
    result = await assistant_service.interpret_training_log(
        log_content=req.log_content,
        architecture=req.architecture or "EfficientNet-B0",
        num_folds=req.num_folds or 4,
    )
    return AssistantResponse(**result)


@router.post("/audit-script", response_model=AssistantResponse)
async def audit_python_script(req: AuditScriptReviewRequest):
    """Audit Python training or evaluation script for CPU hardware safety."""
    result = await assistant_service.audit_script(
        script_name=req.script_name,
        script_content=req.script_content,
        hardware_target=req.hardware_target or "Intel Core i7-2600",
    )
    return AssistantResponse(**result)


@router.post("/review-config", response_model=AssistantResponse)
async def review_experiment_config(req: ExperimentConfigReviewRequest):
    """Review an experiment configuration dictionary."""
    result = await assistant_service.review_experiment_config(
        experiment_name=req.experiment_name,
        config_details=req.config_details,
    )
    return AssistantResponse(**result)


@router.post("/explain-result", response_model=AssistantResponse)
async def explain_scan_result(req: ExplainResultRequest):
    """Explain an ONNX mosquito genus classification in plain language."""
    result = await assistant_service.explain_result(
        genus=req.genus,
        raw_scores=req.raw_scores,
        scan_id=req.scan_id,
        quality_feedback=req.quality_feedback,
    )
    return AssistantResponse(**result)


@router.post("/summarize-history", response_model=AssistantResponse)
async def summarize_scan_history(req: SummarizeHistoryRequest):
    """Summarize user mosquito scan history in plain language."""
    result = await assistant_service.summarize_history(
        submissions=req.submissions,
    )
    return AssistantResponse(**result)
