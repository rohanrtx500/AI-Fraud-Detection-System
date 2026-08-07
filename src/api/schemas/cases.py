from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CaseCreate(BaseModel):
    alert_id: str = Field(..., description="The RiskAssessment assessment_id to escalate.")
    priority: str = Field("MEDIUM", description="Priority level: LOW, MEDIUM, HIGH, CRITICAL.")
    analyst: str | None = Field(None, description="Username/ID of the assigned analyst.")


class CaseUpdate(BaseModel):
    status: str | None = Field(
        None, description="New status: OPEN, INVESTIGATING, ESCALATED, RESOLVED, FALSE_POSITIVE."
    )
    priority: str | None = Field(None, description="New priority level.")
    analyst: str | None = Field(None, description="Assigned analyst username/ID.")


class NoteCreate(BaseModel):
    category: str = Field(
        "GENERAL", description="Note category: GENERAL, TRANSACTION, BEHAVIORAL, GRAPH, COMPLIANCE."
    )
    content: str = Field(..., description="Note text content.")
    author: str = Field(..., description="Authoring analyst username.")


class NoteUpdate(BaseModel):
    content: str = Field(..., description="Updated note text content.")


class TimelineEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: int
    case_id: str
    event_type: str
    description: str
    actor: str
    created_at: datetime


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    note_id: str
    case_id: str
    category: str
    content: str
    author: str
    created_at: datetime
    updated_at: datetime | None


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evidence_id: str
    case_id: str
    filename: str
    file_type: str
    uploaded_by: str
    uploaded_at: datetime


class CaseBriefResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    case_id: str
    alert_id: str
    analyst: str | None
    priority: str
    status: str
    created_at: datetime
    resolved_at: datetime | None


class TransactionBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transaction_id: str
    sender_id: str
    receiver_id: str
    amount: float
    currency: str
    merchant_category: str
    location_country: str
    location_city: str
    device_id: str
    ip_address: str
    timestamp: datetime


class RiskAssessmentBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    assessment_id: str
    transaction_id: str
    risk_score: float
    recommendation: str
    model_version: str
    assessed_at: datetime
    transaction: TransactionBrief | None = None


class CaseDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    case_id: str
    alert_id: str
    analyst: str | None
    priority: str
    status: str
    created_at: datetime
    resolved_at: datetime | None

    # Nested fields
    assessment: RiskAssessmentBrief | None = None
    timeline_events: list[TimelineEventResponse] = []
    notes: list[NoteResponse] = []
    evidence: list[EvidenceResponse] = []


class CaseDashboardMetricsResponse(BaseModel):
    status_distribution: dict[str, int]
    priority_distribution: dict[str, int]
    analyst_workload: dict[str, int]


class UnifiedSearchResponse(BaseModel):
    cases: list[dict]
    transactions: list[dict]
