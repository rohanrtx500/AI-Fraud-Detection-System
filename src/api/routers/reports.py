from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.analytics.reports import ExecutiveReportGenerator
from src.api.dependencies import get_db_session, verify_api_key
from src.api.security import get_required_role
from src.database.models import User

router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(verify_api_key)])


@router.get(
    "/summary",
    status_code=status.HTTP_200_OK,
    summary="Fetch raw executive fraud statistics",
)
async def get_reports_summary(
    window: str = Query("weekly", pattern="^(daily|weekly|monthly)$"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_required_role(["Compliance Officer", "Auditor"])),
):
    generator = ExecutiveReportGenerator(db)
    report_data = await generator.generate_report_data(window)
    return report_data


@router.get(
    "/export",
    summary="Download aggregated executive fraud report file",
)
async def export_executive_report(
    window: str = Query("weekly", pattern="^(daily|weekly|monthly)$"),
    format: str = Query("pdf", pattern="^(pdf|excel|csv)$"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_required_role(["Compliance Officer", "Auditor"])),
):
    generator = ExecutiveReportGenerator(db)
    report_data = await generator.generate_report_data(window)

    if format == "pdf":
        content = generator.generate_pdf_report(report_data)
        media_type = "application/pdf"
        filename = f"executive_fraud_report_{window}.pdf"
    elif format == "excel":
        content = generator.generate_excel_report(report_data)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"executive_fraud_report_{window}.xlsx"
    else:  # csv
        content = generator.generate_csv_report(report_data)
        media_type = "text/csv"
        filename = f"executive_fraud_report_{window}.csv"

    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=content, media_type=media_type, headers=headers)
