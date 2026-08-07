import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from src.database.connection import Base


class Transaction(Base):
    """
    SQLAlchemy model representing raw ingested transaction event.
    """

    __tablename__ = "transactions"

    transaction_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_id = Column(String(50), nullable=False, index=True)
    receiver_id = Column(String(50), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    merchant_category = Column(String(10), nullable=False)
    location_country = Column(String(2), nullable=False)
    location_city = Column(String(100), nullable=False)
    device_id = Column(String(100), nullable=False)
    ip_address = Column(String(45), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    assessment = relationship("RiskAssessment", back_populates="transaction", uselist=False)


class RiskAssessment(Base):
    """
    SQLAlchemy model storing the ML model inference results, risk output, and SHAP vectors.
    """

    __tablename__ = "risk_assessments"

    assessment_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_id = Column(
        String(36),
        ForeignKey("transactions.transaction_id"),
        nullable=False,
        unique=True,
        index=True,
    )
    risk_score = Column(
        Float, nullable=False, index=True
    )  # Calibrated probability percentage (0-100)
    recommendation = Column(String(10), nullable=False)  # ALLOW, FLAG, BLOCK
    model_version = Column(String(50), nullable=False)  # Version tracking
    assessed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    shap_values = Column(JSON, nullable=True)  # Dict storing local feature importance values

    # Relationships
    transaction = relationship("Transaction", back_populates="assessment")
    audit_logs = relationship("AuditLog", back_populates="assessment")
    case = relationship("Case", back_populates="assessment", uselist=False)


class AuditLog(Base):
    """
    SQLAlchemy model tracking compliance human reviews and override resolutions.
    """

    __tablename__ = "audit_logs"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    assessment_id = Column(String(36), ForeignKey("risk_assessments.assessment_id"), nullable=False)
    reviewer_id = Column(String(50), nullable=False, index=True)
    action_taken = Column(
        String(50), nullable=False
    )  # CONFIRMED_FRAUD, DISMISSED_ALERT, OVERRIDE_BLOCK
    notes = Column(String(500), nullable=True)
    logged_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    assessment = relationship("RiskAssessment", back_populates="audit_logs")


class Case(Base):
    """
    SQLAlchemy model representing a fraud investigation case created from an alert.
    """

    __tablename__ = "cases"

    case_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_id = Column(
        String(36),
        ForeignKey("risk_assessments.assessment_id"),
        nullable=False,
        unique=True,
        index=True,
    )
    analyst = Column(String(100), nullable=True, index=True)
    priority = Column(String(10), nullable=False, default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    status = Column(
        String(20), nullable=False, default="OPEN"
    )  # OPEN, INVESTIGATING, ESCALATED, RESOLVED, FALSE_POSITIVE
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    assessment = relationship("RiskAssessment", back_populates="case")
    timeline_events = relationship(
        "TimelineEvent",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="TimelineEvent.created_at",
    )
    notes = relationship("AnalystNote", back_populates="case", cascade="all, delete-orphan")
    evidence = relationship("Evidence", back_populates="case", cascade="all, delete-orphan")


class TimelineEvent(Base):
    """
    SQLAlchemy model representing an action/event logged on a case's investigation timeline.
    """

    __tablename__ = "timeline_events"

    event_id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(36), ForeignKey("cases.case_id"), nullable=False, index=True)
    event_type = Column(
        String(30), nullable=False
    )  # CASE_CREATED, ANALYST_ASSIGNED, NOTE_ADDED, EVIDENCE_ATTACHED, STATUS_CHANGED
    description = Column(String(500), nullable=False)
    actor = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    case = relationship("Case", back_populates="timeline_events")


class AnalystNote(Base):
    """
    SQLAlchemy model representing a note added by an investigator to a case.
    """

    __tablename__ = "analyst_notes"

    note_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.case_id"), nullable=False, index=True)
    category = Column(
        String(30), nullable=False, default="GENERAL"
    )  # GENERAL, TRANSACTION, BEHAVIORAL, GRAPH, COMPLIANCE
    content = Column(String(1000), nullable=False)
    author = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True)

    # Relationships
    case = relationship("Case", back_populates="notes")


class Evidence(Base):
    """
    SQLAlchemy model representing files uploaded as evidence for a case.
    """

    __tablename__ = "evidence"

    evidence_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.case_id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(100), nullable=False)  # MIME type
    uploaded_by = Column(String(100), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    case = relationship("Case", back_populates="evidence")


class ThreatIndicator(Base):
    """
    SQLAlchemy model representing blacklisted threat intelligence vectors.
    """

    __tablename__ = "threat_indicators"

    indicator_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    indicator_type = Column(String(20), nullable=False, index=True)  # IP, DEVICE, ACCOUNT, MERCHANT
    value = Column(String(255), nullable=False, unique=True, index=True)
    risk_multiplier = Column(Float, default=2.0)
    source = Column(String(100), default="manual_entry")
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class User(Base):
    """
    SQLAlchemy model representing a system compliance user (officer/analyst/auditor).
    """

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), nullable=False, unique=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # Compliance Officer, Analyst, Auditor
    role_id = Column(String(50), nullable=True, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

