from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_db_session, verify_api_key
from src.models.monitoring import ModelMonitor

router = APIRouter(
    prefix="/monitoring", tags=["monitoring"], dependencies=[Depends(verify_api_key)]
)


@router.get(
    "/report",
    status_code=status.HTTP_200_OK,
    summary="Get model monitoring and drift reports",
)
async def get_monitoring_report(db=Depends(get_db_session)):
    monitor = ModelMonitor()
    report = monitor.load_report()
    if not report:
        # Generate on the fly if report doesn't exist
        report = await monitor.run_monitoring_cycle(db)
    return report


@router.post(
    "/run",
    status_code=status.HTTP_200_OK,
    summary="Manually trigger model drift and statistical monitoring checks",
)
async def trigger_monitoring_check(db=Depends(get_db_session)):
    monitor = ModelMonitor()
    report = await monitor.run_monitoring_cycle(db)
    return report
