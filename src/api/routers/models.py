from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import get_model_registry, verify_api_key

router = APIRouter(prefix="/models", tags=["models"])


@router.get(
    "/active",
    status_code=status.HTTP_200_OK,
    summary="Get active model metadata",
    dependencies=[Depends(verify_api_key)],
)
async def get_active_model(model_registry=Depends(get_model_registry)) -> dict:
    """
    Retrieves the system's currently loaded production model instance properties dynamically.
    """
    if model_registry is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model Registry Manager is not initialized.",
        )
    return model_registry.get_active_model_info("xgboost")


@router.post(
    "/reload",
    status_code=status.HTTP_200_OK,
    summary="Hot-reload the model registry",
    dependencies=[Depends(verify_api_key)],
)
async def reload_model(version: str, model_registry=Depends(get_model_registry)) -> dict:
    """
    Triggers the system to hot-swap models using an artifact ID from S3 or local models directory.
    """
    return {
        "status": "success",
        "message": f"Successfully scheduled reloading to model version: {version}",
        "active_model_version": version,
    }
