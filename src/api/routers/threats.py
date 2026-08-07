from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session, verify_api_key
from src.api.security import get_current_user, get_required_role
from src.database import crud
from src.database.models import User

router = APIRouter(prefix="/threats", tags=["threats"], dependencies=[Depends(verify_api_key)])


@router.get("", status_code=status.HTTP_200_OK)
async def list_threats(
    indicator_type: str | None = Query(None, pattern="^(IP|DEVICE|ACCOUNT|MERCHANT)$"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    return await crud.get_threat_indicators(db, indicator_type)


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_threat(
    indicator_type: str = Query(..., pattern="^(IP|DEVICE|ACCOUNT|MERCHANT)$"),
    value: str = Query(...),
    risk_multiplier: float = Query(2.0, ge=1.0),
    source: str = Query("manual_entry"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_required_role(["Compliance Officer"])),
):
    indicator_data = {
        "indicator_type": indicator_type,
        "value": value,
        "risk_multiplier": risk_multiplier,
        "source": source,
    }
    return await crud.create_threat_indicator(db, indicator_data)


@router.delete("/{indicator_id}", status_code=status.HTTP_200_OK)
async def remove_threat(
    indicator_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_required_role(["Compliance Officer"])),
):
    deleted = await crud.delete_threat_indicator(db, indicator_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Threat indicator {indicator_id} not found.",
        )
    return {"message": "Threat indicator successfully deleted."}
