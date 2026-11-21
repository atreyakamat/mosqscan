"""Pydantic Settings configuration for the Vectora AI backend."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str = "sqlite:///./vectora_test.db"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Storage
    MEDIA_STORAGE_PATH: str = os.getenv("MEDIA_STORAGE_PATH", "/tmp/vectora_media")
    _default_models_dir = Path(__file__).resolve().parent.parent.parent / "models"
    _starter_models_dir = Path(__file__).resolve().parent.parent.parent / "vectora-ai-starter" / "models"
    MODEL_REGISTRY_PATH: str = os.getenv(
        "MODEL_REGISTRY_PATH",
        str(_default_models_dir if _default_models_dir.exists() else _starter_models_dir),
    )
    ADULT_MODEL_ARTIFACT: str = os.getenv("ADULT_MODEL_ARTIFACT", "vectora_v3_fp32.onnx")
    MODEL_MANIFEST_PATH: str = os.getenv(
        "MODEL_MANIFEST_PATH",
        str(Path(__file__).resolve().parent.parent.parent / "model-registry" / "manifest.json"),
    )
    EXPECTED_EXP_B_SHA256: str = "d644b9cd9c952d461bbfbb44e8b1926cdcf9bbbfb9cd43f85065cbed0d7b1499"

    # CPU Inference Resource Allocation (i7-2600)
    ONNX_INTRA_OP_THREADS: int = int(os.getenv("ONNX_INTRA_OP_THREADS", "2"))
    ONNX_INTER_OP_THREADS: int = int(os.getenv("ONNX_INTER_OP_THREADS", "1"))
    CONCURRENT_INFERENCE_LIMIT: int = int(os.getenv("CONCURRENT_INFERENCE_LIMIT", "1"))

    # App
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    MAX_IMAGE_SIZE_MB: int = 20
    MAX_VIDEO_SIZE_MB: int = 100

    # Rate limiting
    LOGIN_RATE_LIMIT_ATTEMPTS: int = 5
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 900  # 15 minutes
    PASSWORD_RESET_RATE_LIMIT_ATTEMPTS: int = 5
    PASSWORD_RESET_RATE_LIMIT_WINDOW_SECONDS: int = 900  # 15 minutes
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 15

    # Inference & Model Safety
    CONFIDENCE_THRESHOLD: float = 0.65

    # Ollama / Local AI Research Assistant (CPU i7-2600)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "gemma3:4b")
    OLLAMA_TIMEOUT_SECONDS: float = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120.0"))

    # Email Service
    EMAIL_PROVIDER: str = "console"
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_TLS: bool = True
    EMAIL_FROM: str = "noreply@vectora.org"
    FRONTEND_URL: str = "http://localhost:3000"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v


settings = Settings()

