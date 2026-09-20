"""FastAPI Main Application Module."""

from __future__ import annotations

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import inference, predictive
from api.schemas import HealthCheckResponse
from src.config import settings
from src.database import check_database_connection

DEFAULT_MODEL_PATH = Path("models/sla_predictor.joblib")

app = FastAPI(
    title=settings.app_name,
    description="AI-Powered Document Intelligence & Predictive Operations Analytics API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for local analytics dashboards / client interfaces
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(predictive.router)
app.include_router(inference.router)


@app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
@app.get("/api/v1/health", response_model=HealthCheckResponse, tags=["Health"])
def health_check() -> HealthCheckResponse:
    """Check API service health and dependency readiness gracefully."""
    try:
        db_connected = check_database_connection()
    except Exception:
        db_connected = False

    try:
        model_present = DEFAULT_MODEL_PATH.exists()
    except Exception:
        model_present = False

    status = "ok" if (db_connected and model_present) else "degraded"

    return HealthCheckResponse(
        status=status,
        app_name=settings.app_name,
        app_env=settings.app_env,
        database_connected=db_connected,
        model_artifact_present=model_present,
    )
