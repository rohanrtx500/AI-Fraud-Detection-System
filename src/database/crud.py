from datetime import UTC, date, datetime

from sqlalchemy import case, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models import (
    AnalystNote,
    AuditLog,
    Case,
    Evidence,
    RiskAssessment,
    ThreatIndicator,
    TimelineEvent,
    Transaction,
)


async def create_transaction(db: AsyncSession, transaction_data: dict) -> Transaction:
    """
    Inserts a new raw transaction entry into database.
    """
    ts = transaction_data.get("timestamp")
    if isinstance(ts, str):
        # Handle string timestamp from API/JSON
        try:
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            ts = datetime.now(UTC).replace(tzinfo=None)
    elif not isinstance(ts, datetime):
        ts = datetime.now(UTC).replace(tzinfo=None)

    tx = Transaction(
        transaction_id=transaction_data.get("transaction_id"),
        sender_id=transaction_data["sender_id"],
        receiver_id=transaction_data["receiver_id"],
        amount=float(transaction_data["amount"]),
        currency=transaction_data.get("currency", "USD"),
        merchant_category=str(transaction_data["merchant_category"]),
        location_country=transaction_data["location_country"],
        location_city=transaction_data["location_city"],
        device_id=transaction_data["device_id"],
        ip_address=transaction_data["ip_address"],
        timestamp=ts,
    )
    db.add(tx)
    await db.flush()
    return tx


async def create_risk_assessment(db: AsyncSession, assessment_data: dict) -> RiskAssessment:
    """
    Saves ML inference predictions and SHAP data.
    """
    assessed_at = assessment_data.get("assessed_at")
    if isinstance(assessed_at, str):
        try:
            assessed_at = datetime.fromisoformat(assessed_at.replace("Z", "+00:00")).replace(
                tzinfo=None
            )
        except ValueError:
            assessed_at = datetime.now(UTC).replace(tzinfo=None)
    elif not isinstance(assessed_at, datetime):
        assessed_at = datetime.now(UTC).replace(tzinfo=None)

    ra = RiskAssessment(
        assessment_id=assessment_data.get("assessment_id"),
        transaction_id=assessment_data["transaction_id"],
        risk_score=float(assessment_data["risk_score"]),
        recommendation=assessment_data.get("recommendation", "ALLOW"),
        model_version=assessment_data.get("model_version", "v1.0.0"),
        shap_values=assessment_data.get("shap_values"),
        assessed_at=assessed_at,
    )
    db.add(ra)
    await db.flush()
    return ra


async def get_transaction_by_id(db: AsyncSession, transaction_id: str) -> Transaction | None:
    """
    Fetches transaction and eager loads its risk assessment details and audit logs.
    """
    stmt = (
        select(Transaction)
        .where(Transaction.transaction_id == transaction_id)
        .options(selectinload(Transaction.assessment).selectinload(RiskAssessment.audit_logs))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_audit_log(
    db: AsyncSession, assessment_id: str, reviewer_id: str, action: str, notes: str | None = None
) -> AuditLog:
    """
    Creates record logging reviewer manual action.
    """
    log = AuditLog(
        assessment_id=assessment_id,
        reviewer_id=reviewer_id,
        action_taken=action,
        notes=notes,
        logged_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(log)
    await db.flush()
    return log


async def get_metrics_summary(db: AsyncSession, start_date: date, end_date: date) -> dict:
    """
    Queries database aggregates to construct KPI numbers.
    """
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    # 1. Total processed counts & value
    stmt_tx = select(
        func.count(Transaction.transaction_id).label("count"),
        func.sum(Transaction.amount).label("total_amount"),
    ).where(Transaction.timestamp.between(start_dt, end_dt))
    res_tx = await db.execute(stmt_tx)
    tx_stats = res_tx.one()
    total_count = tx_stats.count or 0
    total_value = float(tx_stats.total_amount or 0.0)

    # 2. Blocked transactions (fraud) count
    stmt_fraud = (
        select(func.count(Transaction.transaction_id))
        .join(RiskAssessment, Transaction.transaction_id == RiskAssessment.transaction_id)
        .where(
            Transaction.timestamp.between(start_dt, end_dt),
            RiskAssessment.recommendation == "BLOCK",
        )
    )
    res_fraud = await db.execute(stmt_fraud)
    blocked_count = res_fraud.scalar() or 0
    fraud_rate = (blocked_count / total_count) if total_count > 0 else 0.0

    # 3. Active alerts count (unreviewed assessments with recommendation in FLAG, BLOCK)
    stmt_alerts = select(func.count(RiskAssessment.assessment_id)).where(
        RiskAssessment.assessed_at.between(start_dt, end_dt),
        RiskAssessment.recommendation.in_(["FLAG", "BLOCK"]),
        ~exists().where(AuditLog.assessment_id == RiskAssessment.assessment_id),
    )
    res_alerts = await db.execute(stmt_alerts)
    active_alerts = res_alerts.scalar() or 0

    # 4. Risk distribution bucketing (SQL-native)
    stmt_scores = (
        select(
            func.sum(case((RiskAssessment.risk_score <= 20, 1), else_=0)).label("b_0_20"),
            func.sum(case((RiskAssessment.risk_score.between(20.0001, 40), 1), else_=0)).label(
                "b_21_40"
            ),
            func.sum(case((RiskAssessment.risk_score.between(40.0001, 60), 1), else_=0)).label(
                "b_41_60"
            ),
            func.sum(case((RiskAssessment.risk_score.between(60.0001, 80), 1), else_=0)).label(
                "b_61_80"
            ),
            func.sum(case((RiskAssessment.risk_score > 80, 1), else_=0)).label("b_81_100"),
            func.count(RiskAssessment.risk_score).label("total_scores"),
        )
        .join(Transaction, Transaction.transaction_id == RiskAssessment.transaction_id)
        .where(Transaction.timestamp.between(start_dt, end_dt))
    )
    res_scores = await db.execute(stmt_scores)
    scores_row = res_scores.one()

    total_scores = scores_row.total_scores or 0
    buckets = {
        "0-20": scores_row.b_0_20 or 0,
        "21-40": scores_row.b_21_40 or 0,
        "41-60": scores_row.b_41_60 or 0,
        "61-80": scores_row.b_61_80 or 0,
        "81-100": scores_row.b_81_100 or 0,
    }

    risk_distribution = []
    for r_range, cnt in buckets.items():
        pct = (cnt / total_scores * 100.0) if total_scores > 0 else 0.0
        risk_distribution.append(
            {"score_range": r_range, "count": cnt, "percentage": round(pct, 1)}
        )

    return {
        "total_processed_count": total_count,
        "total_processed_value": round(total_value, 2),
        "overall_fraud_rate": round(fraud_rate, 4),
        "active_alerts_count": active_alerts,
        "risk_distribution": risk_distribution,
    }


async def get_daily_trends(db: AsyncSession, limit_days: int) -> list[dict]:
    """
    Queries group-by date metrics of transactions for plot datasets.
    """
    stmt = (
        select(
            func.date(Transaction.timestamp).label("date"),
            func.count(Transaction.transaction_id).label("total_tx"),
            func.sum(Transaction.amount).label("total_amt"),
            func.sum(
                case((RiskAssessment.recommendation.in_(["FLAG", "BLOCK"]), 1), else_=0)
            ).label("flagged_fraud"),
            func.sum(case((RiskAssessment.recommendation == "BLOCK", 1), else_=0)).label("blocked"),
        )
        .join(
            RiskAssessment,
            Transaction.transaction_id == RiskAssessment.transaction_id,
            isouter=True,
        )
        .group_by(func.date(Transaction.timestamp))
        .order_by(func.date(Transaction.timestamp).desc())
        .limit(limit_days)
    )

    res = await db.execute(stmt)
    trends = []
    for row in reversed(res.all()):
        date_val = row.date
        if isinstance(date_val, str):
            date_val = date.fromisoformat(date_val)
        trends.append(
            {
                "date": date_val,
                "total_transactions": row.total_tx or 0,
                "total_amount": float(row.total_amt or 0.0),
                "flagged_fraud_transactions": int(row.flagged_fraud or 0),
                "blocked_transactions": int(row.blocked or 0),
            }
        )
    return trends


# --- Case Management CRUD ---


async def create_case(
    db: AsyncSession, alert_id: str, priority: str = "MEDIUM", analyst: str | None = None
) -> Case:
    """
    Elevates an alert (RiskAssessment) to a Case.
    Logs a CASE_CREATED timeline event.
    """
    # Check if case already exists for this alert
    stmt_check = select(Case).where(Case.alert_id == alert_id)
    res_check = await db.execute(stmt_check)
    existing_case = res_check.scalar_one_or_none()
    if existing_case:
        return existing_case

    new_case = Case(
        alert_id=alert_id,
        priority=priority,
        analyst=analyst,
        status="OPEN",
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(new_case)
    await db.flush()

    # Create timeline event
    event = TimelineEvent(
        case_id=new_case.case_id,
        event_type="CASE_CREATED",
        description=f"Case initialized from alert {alert_id} with {priority} priority.",
        actor="system",
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(event)
    await db.flush()

    if analyst:
        # Log assignment event
        assign_event = TimelineEvent(
            case_id=new_case.case_id,
            event_type="ANALYST_ASSIGNED",
            description=f"Analyst {analyst} assigned to case.",
            actor="system",
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.add(assign_event)
        await db.flush()

    return new_case


async def get_cases(
    db: AsyncSession,
    status: str | None = None,
    priority: str | None = None,
    analyst: str | None = None,
    search_query: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Case]:
    """
    Retrieves all cases matching filter parameters, eager loading risk assessments and transaction details.
    """
    stmt = (
        select(Case)
        .options(selectinload(Case.assessment).selectinload(RiskAssessment.transaction))
        .order_by(Case.created_at.desc())
    )

    if status:
        stmt = stmt.where(Case.status == status)
    if priority:
        stmt = stmt.where(Case.priority == priority)
    if analyst:
        if analyst == "unassigned":
            stmt = stmt.where(Case.analyst.is_(None))
        else:
            stmt = stmt.where(Case.analyst == analyst)

    if search_query:
        # Search by case_id, sender_id, receiver_id, device_id, merchant_category
        stmt = stmt.join(RiskAssessment, Case.alert_id == RiskAssessment.assessment_id).join(
            Transaction, RiskAssessment.transaction_id == Transaction.transaction_id
        )
        stmt = stmt.where(
            (Case.case_id.ilike(f"%{search_query}%"))
            | (Transaction.sender_id.ilike(f"%{search_query}%"))
            | (Transaction.receiver_id.ilike(f"%{search_query}%"))
            | (Transaction.device_id.ilike(f"%{search_query}%"))
            | (Transaction.merchant_category.ilike(f"%{search_query}%"))
        )

    stmt = stmt.offset(skip).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def get_case_by_id(db: AsyncSession, case_id: str) -> Case | None:
    """
    Fetches a detailed Case profile, eager loading all timeline, notes, and evidence objects.
    """
    stmt = (
        select(Case)
        .where(Case.case_id == case_id)
        .options(
            selectinload(Case.assessment).selectinload(RiskAssessment.transaction),
            selectinload(Case.timeline_events),
            selectinload(Case.notes),
            selectinload(Case.evidence),
        )
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


async def update_case(
    db: AsyncSession,
    case_id: str,
    status: str | None = None,
    priority: str | None = None,
    analyst: str | None = None,
    actor: str = "system",
) -> Case | None:
    """
    Updates a case record status, priority, or analyst assignment.
    Automatically generates corresponding timeline events.
    """
    case_obj = await get_case_by_id(db, case_id)
    if not case_obj:
        return None

    if status and case_obj.status != status:
        old_status = case_obj.status
        case_obj.status = status
        # Log resolution times
        if status in ["RESOLVED", "FALSE_POSITIVE"]:
            case_obj.resolved_at = datetime.now(UTC).replace(tzinfo=None)
        else:
            case_obj.resolved_at = None

        event = TimelineEvent(
            case_id=case_id,
            event_type="STATUS_CHANGED",
            description=f"Status changed from {old_status} to {status}.",
            actor=actor,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.add(event)

        # Log audit entry
        action_map = {
            "RESOLVED": "CONFIRMED_FRAUD",
            "FALSE_POSITIVE": "DISMISSED_ALERT",
        }
        action = action_map.get(status, "OVERRIDE_BLOCK")
        log = AuditLog(
            assessment_id=case_obj.alert_id,
            reviewer_id=actor,
            action_taken=action,
            notes=f"Case status changed from {old_status} to {status}.",
            logged_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.add(log)

    if priority and case_obj.priority != priority:
        old_priority = case_obj.priority
        case_obj.priority = priority
        event = TimelineEvent(
            case_id=case_id,
            event_type="STATUS_CHANGED",
            description=f"Priority updated from {old_priority} to {priority}.",
            actor=actor,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.add(event)

    if analyst is not None and case_obj.analyst != analyst:
        old_analyst = case_obj.analyst or "Unassigned"
        new_analyst = analyst or "Unassigned"
        case_obj.analyst = analyst
        event = TimelineEvent(
            case_id=case_id,
            event_type="ANALYST_ASSIGNED",
            description=f"Assignment updated from {old_analyst} to {new_analyst}.",
            actor=actor,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.add(event)

    db.add(case_obj)
    await db.flush()
    return case_obj


async def create_note(
    db: AsyncSession, case_id: str, category: str, content: str, author: str
) -> AnalystNote:
    """
    Appends an analyst note to a case and logs it in the timeline.
    """
    note = AnalystNote(
        case_id=case_id,
        category=category,
        content=content,
        author=author,
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(note)
    await db.flush()

    event = TimelineEvent(
        case_id=case_id,
        event_type="NOTE_ADDED",
        description=f'New {category} note added by {author}: "{content[:60]}..."',
        actor=author,
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(event)
    await db.flush()
    return note


async def update_note(db: AsyncSession, note_id: str, content: str) -> AnalystNote | None:
    """
    Modifies an analyst note.
    """
    stmt = select(AnalystNote).where(AnalystNote.note_id == note_id)
    res = await db.execute(stmt)
    note = res.scalar_one_or_none()
    if not note:
        return None

    note.content = content
    note.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.add(note)
    await db.flush()
    return note


async def create_evidence(
    db: AsyncSession, case_id: str, filename: str, file_path: str, file_type: str, uploaded_by: str
) -> Evidence:
    """
    Registers an evidence attachment on a case.
    """
    ev = Evidence(
        case_id=case_id,
        filename=filename,
        file_path=file_path,
        file_type=file_type,
        uploaded_by=uploaded_by,
        uploaded_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(ev)
    await db.flush()

    event = TimelineEvent(
        case_id=case_id,
        event_type="EVIDENCE_ATTACHED",
        description=f"Evidence file attached: {filename} ({file_type}) uploaded by {uploaded_by}.",
        actor=uploaded_by,
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(event)
    await db.flush()
    return ev


async def get_case_dashboard_metrics(db: AsyncSession) -> dict:
    """
    Compiles case metrics for dashboard reporting.
    """
    # 1. Total cases by status
    stmt_status = select(Case.status, func.count(Case.case_id)).group_by(Case.status)
    res_status = await db.execute(stmt_status)
    status_counts = dict(res_status.all())

    for s in ["OPEN", "INVESTIGATING", "ESCALATED", "RESOLVED", "FALSE_POSITIVE"]:
        if s not in status_counts:
            status_counts[s] = 0

    # 2. Total cases by priority
    stmt_priority = select(Case.priority, func.count(Case.case_id)).group_by(Case.priority)
    res_priority = await db.execute(stmt_priority)
    priority_counts = dict(res_priority.all())

    for p in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
        if p not in priority_counts:
            priority_counts[p] = 0

    # 3. Analyst workloads (active cases)
    stmt_workload = (
        select(Case.analyst, func.count(Case.case_id))
        .where(Case.status.in_(["OPEN", "INVESTIGATING", "ESCALATED"]))
        .group_by(Case.analyst)
    )
    res_workload = await db.execute(stmt_workload)
    workload = {analyst or "Unassigned": count for analyst, count in res_workload.all()}

    return {
        "status_distribution": status_counts,
        "priority_distribution": priority_counts,
        "analyst_workload": workload,
    }


async def search_workspace(db: AsyncSession, query: str) -> dict:
    """
    Performs system-wide search.
    Matches cases by ID or analyst, and transactions by ID, sender, receiver, device, or merchant.
    """
    # Search Cases
    stmt_cases = (
        select(Case)
        .options(selectinload(Case.assessment).selectinload(RiskAssessment.transaction))
        .where((Case.case_id.ilike(f"%{query}%")) | (Case.analyst.ilike(f"%{query}%")))
        .limit(10)
    )
    res_cases = await db.execute(stmt_cases)
    cases_list = res_cases.scalars().all()

    # Search Transactions
    stmt_txs = (
        select(Transaction)
        .options(selectinload(Transaction.assessment))
        .where(
            (Transaction.transaction_id.ilike(f"%{query}%"))
            | (Transaction.sender_id.ilike(f"%{query}%"))
            | (Transaction.receiver_id.ilike(f"%{query}%"))
            | (Transaction.device_id.ilike(f"%{query}%"))
            | (Transaction.merchant_category.ilike(f"%{query}%"))
        )
        .limit(10)
    )
    res_txs = await db.execute(stmt_txs)
    txs_list = res_txs.scalars().all()

    return {
        "cases": [
            {
                "case_id": c.case_id,
                "status": c.status,
                "priority": c.priority,
                "analyst": c.analyst,
                "created_at": c.created_at.isoformat(),
            }
            for c in cases_list
        ],
        "transactions": [
            {
                "transaction_id": t.transaction_id,
                "sender_id": t.sender_id,
                "receiver_id": t.receiver_id,
                "amount": t.amount,
                "device_id": t.device_id,
                "timestamp": t.timestamp.isoformat(),
            }
            for t in txs_list
        ],
    }


async def get_threat_indicators(
    db: AsyncSession, indicator_type: str | None = None
) -> list[ThreatIndicator]:
    """
    Retrieves threat indicators from the database.
    """
    stmt = select(ThreatIndicator).order_by(ThreatIndicator.added_at.desc())
    if indicator_type:
        stmt = stmt.where(ThreatIndicator.indicator_type == indicator_type)
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def create_threat_indicator(db: AsyncSession, indicator_data: dict) -> ThreatIndicator:
    """
    Creates a new blacklisted threat indicator.
    """
    stmt = select(ThreatIndicator).where(ThreatIndicator.value == indicator_data["value"])
    res = await db.execute(stmt)
    existing = res.scalar_one_or_none()
    if existing:
        return existing

    ti = ThreatIndicator(
        indicator_type=indicator_data["indicator_type"],
        value=indicator_data["value"],
        risk_multiplier=float(indicator_data.get("risk_multiplier", 2.0)),
        source=indicator_data.get("source", "manual_entry"),
        added_at=datetime.utcnow(),
    )
    db.add(ti)
    await db.flush()
    return ti


async def delete_threat_indicator(db: AsyncSession, indicator_id: str) -> bool:
    """
    Deletes a threat indicator by ID.
    """
    stmt = select(ThreatIndicator).where(ThreatIndicator.indicator_id == indicator_id)
    res = await db.execute(stmt)
    ti = res.scalar_one_or_none()
    if ti:
        await db.delete(ti)
        await db.flush()
        return True
    return False
