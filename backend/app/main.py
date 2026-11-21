"""FastAPI Application entrypoint for Vectora AI."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import admin, adult, assistant, auth, dashboard, larvae, models, submissions
from app.config import settings
from app.core.exceptions import VectoraException
from app.db.base import Base
from app.db.session import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("vectora.backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure tables exist in development / test SQLite
    if settings.DATABASE_URL.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
    logger.info("Vectora AI Backend starting up (env=%s)", settings.ENVIRONMENT)

    # Load and verify ONNX adult classification model once during startup
    try:
        from app.inference.adult_classifier import get_classifier
        classifier = get_classifier()
        logger.info(
            "Adult classifier initialized: artifact=%s, version=%s, threshold=%.2f",
            classifier.model_artifact,
            classifier._model_version,
            classifier.confidence_threshold,
        )
    except Exception as exc:
        logger.error("Failed to load and verify adult classifier during startup: %s", exc)
        raise

    yield
    logger.info("Vectora AI Backend shutting down")


app = FastAPI(
    title="Vectora AI API",
    version="2.2.0",
    description="Unified API for Vectora AI Mosquito Identification Platform",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(VectoraException)
async def vectora_exception_handler(request: Request, exc: VectoraException):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


from fastapi.encoders import jsonable_encoder


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_msg = errors[0].get("msg") if errors else "Validation error"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": str(first_msg),
            "detail": jsonable_encoder(errors),
        },
    )



@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        content = {"success": False, **exc.detail}
    else:
        content = {
            "success": False,
            "error_code": f"HTTP_{exc.status_code}",
            "message": str(exc.detail),
        }
    return JSONResponse(status_code=exc.status_code, content=content)


# Health checks
@app.get("/health", tags=["health"])
@app.get("/api/v1/health", tags=["health"])
def health_check():
    return {
        "status": "healthy",
        "service": "vectora-ai-backend",
        "version": "2.2.0",
        "environment": settings.ENVIRONMENT,
    }


# Include Routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(adult.router, prefix="/api/v1")
app.include_router(larvae.router, prefix="/api/v1")
app.include_router(models.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(submissions.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(assistant.router, prefix="/api/v1")
