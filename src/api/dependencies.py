from collections.abc import AsyncGenerator

from fastapi import Request

from src.api.middleware.security import verify_api_key as verify_api_key
from src.database.connection import get_session


async def get_db_session() -> AsyncGenerator:
    """
    Dependency yielding an active transactional session database context.
    """
    async for session in get_session():
        yield session


def get_inference_engine(request: Request):
    """
    Dependency to access the preloaded FraudInferenceEngine scoring instance.
    """
    return getattr(request.app.state, "inference_engine", None)


def get_model_registry(request: Request):
    """
    Dependency to access the preloaded ML Model Wrapper.
    """
    return getattr(request.app.state, "model_manager", None)
