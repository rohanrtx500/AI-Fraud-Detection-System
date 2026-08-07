import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.middleware.telemetry import APIRequestTelemetryMiddleware
from src.api.routers.analytics import router as analytics_router
from src.api.routers.cases import router as cases_router
from src.api.routers.models import router as models_router
from src.api.routers.monitoring import router as monitoring_router
from src.api.routers.reports import router as reports_router
from src.api.routers.threats import router as threats_router
from src.api.routers.transactions import router as transactions_router
from src.api.routers.websocket import router as websocket_router
from src.api.routers.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Stateful lifespan manager replacing deprecated startup/shutdown event handlers.
    Ensures safe initialization and release of system pools and logging states.
    """
    # 1. Initialize structured logger configurations
    from src.utils.logging import configure_structured_logging

    configure_structured_logging()

    import structlog

    logger = structlog.get_logger()
    logger.info("Initializing API application services...")

    # 2. Database setups
    from dotenv import load_dotenv

    from src.database.connection import create_tables, initialize_db

    load_dotenv()

    database_url = os.getenv("DATABASE_URL")
    os.makedirs("data/evidence", exist_ok=True)
    if not database_url:
        os.makedirs("data", exist_ok=True)
        database_url = "sqlite+aiosqlite:///data/fraud_detection_db.db"

    logger.info("Initializing database session pool", host=database_url.split("@")[-1])
    initialize_db(database_url)

    # Auto-generate missing table schemas in development/sqlite
    env = os.getenv("ENVIRONMENT", "development")
    if env == "development" or "sqlite" in database_url:
        logger.info("Auto-executing database DDL migrations")
        await create_tables()

    # 3. Load Model Registry Manager and ML Inference Engine
    from src.models.inference import FraudInferenceEngine
    from src.models.registry_manager import ModelRegistryManager

    logger.info("Caching inference and registry managers in app state")
    app.state.inference_engine = FraudInferenceEngine()
    app.state.model_manager = ModelRegistryManager()

    logger.info("Application lifecycle startup complete.")
    yield

    # Shutdown execution
    logger.info("Disposing database connection pool...")
    from src.database.connection import close_db

    await close_db()
    logger.info("Teardown lifecycle complete. Server stopped.")


def create_app() -> FastAPI:
    """
    FastAPI Application Factory.
    Configures lifecycles, middlewares, exception handlers, and routing.
    """
    app = FastAPI(
        title="AI Fraud Detection & Risk Intelligence API",
        description="Production-grade API for scoring financial transactions, explaining risk decisions using SHAP, and managing model registry lifecycles.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS Settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Adjust for production requirements
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Custom Telemetry Middleware
    app.add_middleware(APIRequestTelemetryMiddleware)

    # Register Routers
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(transactions_router, prefix="/api/v1")
    app.include_router(models_router, prefix="/api/v1")
    app.include_router(analytics_router, prefix="/api/v1")
    app.include_router(cases_router, prefix="/api/v1")
    app.include_router(monitoring_router, prefix="/api/v1")
    app.include_router(reports_router, prefix="/api/v1")
    app.include_router(websocket_router)
    app.include_router(threats_router, prefix="/api/v1")

    @app.get("/health", tags=["system"])
    async def health_check():
        """
        Liveness probe for deployment/Kubernetes.
        """
        return {"status": "healthy", "service": "fraud-detection-api"}

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
