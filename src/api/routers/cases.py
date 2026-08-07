import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select

from src.api.dependencies import get_db_session, verify_api_key
from src.api.schemas.cases import (
    CaseBriefResponse,
    CaseDashboardMetricsResponse,
    CaseDetailResponse,
    CaseUpdate,
    EvidenceResponse,
    NoteCreate,
    NoteResponse,
    NoteUpdate,
    UnifiedSearchResponse,
)
from src.api.security import get_current_user, get_required_role
from src.database import crud
from src.database.models import AuditLog, Evidence, RiskAssessment, User

router = APIRouter(prefix="/cases", tags=["cases"], dependencies=[Depends(verify_api_key)])


@router.post(
    "",
    response_model=CaseBriefResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Escalate an alert to a Case",
)
async def escalate_alert(
    alert_id: str = Query(..., description="The RiskAssessment assessment_id to escalate"),
    priority: str = Query("MEDIUM", description="Case priority level"),
    analyst: str | None = Query(None, description="Assigned analyst username"),
    db=Depends(get_db_session),
    current_user: User = Depends(get_required_role(["Compliance Officer", "Analyst"])),
):
    # Verify RiskAssessment alert exists
    stmt = select(RiskAssessment).where(RiskAssessment.assessment_id == alert_id)
    res = await db.execute(stmt)
    alert = res.scalar_one_or_none()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Risk alert {alert_id} not found.",
        )

    case_record = await crud.create_case(
        db=db, alert_id=alert_id, priority=priority, analyst=analyst
    )
    return case_record


@router.get(
    "",
    response_model=list[CaseBriefResponse],
    status_code=status.HTTP_200_OK,
    summary="List cases with optional filters",
)
async def list_cases(
    status: str | None = Query(None, description="Filter by case status"),
    priority: str | None = Query(None, description="Filter by case priority"),
    analyst: str | None = Query(None, description="Filter by assigned analyst"),
    search_query: str | None = Query(None, description="Sub-text search"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db=Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    cases = await crud.get_cases(
        db=db,
        status=status,
        priority=priority,
        analyst=analyst,
        search_query=search_query,
        skip=skip,
        limit=limit,
    )
    return cases


@router.get(
    "/dashboard/metrics",
    response_model=CaseDashboardMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get case metrics aggregates for dashboard reports",
)
async def get_dashboard_metrics(
    db=Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    metrics = await crud.get_case_dashboard_metrics(db)
    return metrics


@router.get(
    "/search",
    response_model=UnifiedSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Unified workspace search across cases and transactions",
)
async def search_all(
    query: str = Query(..., min_length=2, description="Search keyword"),
    db=Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    results = await crud.search_workspace(db, query)
    return results


@router.get(
    "/{case_id}",
    response_model=CaseDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get full case profile and investigation details",
)
async def get_case_details(
    case_id: str,
    db=Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    case_record = await crud.get_case_by_id(db, case_id)
    if not case_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found.",
        )
    return case_record


@router.patch(
    "/{case_id}",
    response_model=CaseBriefResponse,
    status_code=status.HTTP_200_OK,
    summary="Update case properties",
)
async def modify_case(
    case_id: str,
    payload: CaseUpdate,
    actor: str = Query("system", description="Analyst username making the edit"),
    db=Depends(get_db_session),
    current_user: User = Depends(get_required_role(["Compliance Officer", "Analyst"])),
):
    case_record = await crud.update_case(
        db=db,
        case_id=case_id,
        status=payload.status,
        priority=payload.priority,
        analyst=payload.analyst,
        actor=actor,
    )
    if not case_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found.",
        )
    return case_record


@router.post(
    "/{case_id}/notes",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an analyst note to a case",
)
async def add_case_note(
    case_id: str,
    payload: NoteCreate,
    db=Depends(get_db_session),
    current_user: User = Depends(get_required_role(["Compliance Officer", "Analyst"])),
):
    case_record = await crud.get_case_by_id(db, case_id)
    if not case_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found.",
        )

    note_record = await crud.create_note(
        db=db,
        case_id=case_id,
        category=payload.category,
        content=payload.content,
        author=payload.author,
    )
    return note_record


@router.put(
    "/notes/{note_id}",
    response_model=NoteResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an existing analyst note",
)
async def modify_case_note(
    note_id: str,
    payload: NoteUpdate,
    db=Depends(get_db_session),
    current_user: User = Depends(get_required_role(["Compliance Officer", "Analyst"])),
):
    note_record = await crud.update_note(db=db, note_id=note_id, content=payload.content)
    if not note_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note {note_id} not found.",
        )
    return note_record


@router.post(
    "/{case_id}/evidence",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an evidence attachment for a case",
)
async def upload_evidence_file(
    case_id: str,
    file: UploadFile = File(...),
    uploaded_by: str = Query(..., description="Analyst username uploading the file"),
    db=Depends(get_db_session),
    current_user: User = Depends(get_required_role(["Compliance Officer", "Analyst"])),
):
    case_record = await crud.get_case_by_id(db, case_id)
    if not case_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found.",
        )

    # Prepare local evidence directory
    evidence_dir = "data/evidence"
    os.makedirs(evidence_dir, exist_ok=True)

    # Clean filename
    safe_filename = "".join(c for c in file.filename if c.isalnum() or c in "._-")

    # Save to a temporary file path
    temp_file_id = str(uuid.uuid4())
    temp_path = os.path.join(evidence_dir, f"temp_{temp_file_id}_{safe_filename}")

    try:
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write file to local disk: {str(e)}",
        ) from e

    # Save initial metadata in DB to generate DB evidence ID
    evidence_record = await crud.create_evidence(
        db=db,
        case_id=case_id,
        filename=file.filename,
        file_path=temp_path,
        file_type=file.content_type or "application/octet-stream",
        uploaded_by=uploaded_by,
    )

    # Rename file to use final evidence_id
    db_evidence_id = evidence_record.evidence_id
    final_path = os.path.join(evidence_dir, f"{db_evidence_id}_{safe_filename}")

    try:
        os.rename(temp_path, final_path)
        evidence_record.file_path = final_path
        db.add(evidence_record)
        await db.flush()
    except Exception as e:
        print(f"Renaming temp evidence file to final UUID path failed: {e}")
        # Keep temp_path in DB as fallback if rename fails

    return evidence_record


@router.get(
    "/evidence/{evidence_id}/file",
    status_code=status.HTTP_200_OK,
    summary="Download evidence attachment file binary",
)
async def download_evidence_file(
    evidence_id: str,
    db=Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Evidence).where(Evidence.evidence_id == evidence_id)
    res = await db.execute(stmt)
    evidence_record = res.scalar_one_or_none()
    if not evidence_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence {evidence_id} not found.",
        )

    if not os.path.exists(evidence_record.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File binary not found on disk storage.",
        )

    return FileResponse(
        path=evidence_record.file_path,
        filename=evidence_record.filename,
        media_type=evidence_record.file_type,
    )


@router.get(
    "/audit/logs",
    status_code=status.HTTP_200_OK,
    summary="Get case audit logs",
)
async def list_audit_logs(
    limit: int = Query(100, ge=1),
    db=Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    stmt = select(AuditLog).order_by(AuditLog.logged_at.desc()).limit(limit)
    res = await db.execute(stmt)
    logs = res.scalars().all()
    return [
        {
            "log_id": log.log_id,
            "assessment_id": log.assessment_id,
            "reviewer_id": log.reviewer_id,
            "action_taken": log.action_taken,
            "notes": log.notes,
            "logged_at": log.logged_at.isoformat(),
        }
        for log in logs
    ]
