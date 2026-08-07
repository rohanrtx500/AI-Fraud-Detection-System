from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database.connection import Base
from src.database.crud import (
    create_audit_log,
    create_risk_assessment,
    create_transaction,
    get_daily_trends,
    get_metrics_summary,
    get_transaction_by_id,
)

# SQLite in-memory async connection URL
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_session():
    """
    Fixture initializing the in-memory database schema and yielding an async session.
    """
    engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session
        await session.rollback()
        await session.close()

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_and_retrieve_transaction(db_session):
    """
    Verifies transaction creation and subsequent eager loading retrieval.
    """
    tx_payload = {
        "transaction_id": "test-tx-123",
        "sender_id": "usr_9999",
        "receiver_id": "merch_111",
        "amount": 250.75,
        "currency": "USD",
        "merchant_category": "5411",
        "location_country": "US",
        "location_city": "New York",
        "device_id": "dev_test_device",
        "ip_address": "127.0.0.1",
        "timestamp": datetime.now(UTC).replace(tzinfo=None),
    }

    # Insert
    tx = await create_transaction(db_session, tx_payload)
    assert tx.transaction_id == "test-tx-123"
    assert tx.amount == 250.75

    # Retrieve
    retrieved = await get_transaction_by_id(db_session, "test-tx-123")
    assert retrieved is not None
    assert retrieved.sender_id == "usr_9999"
    assert retrieved.device_id == "dev_test_device"


@pytest.mark.asyncio
async def test_risk_assessment_relation(db_session):
    """
    Verifies saving a risk assessment linked to a transaction.
    """
    tx_payload = {
        "transaction_id": "tx-relation-test",
        "sender_id": "usr_9999",
        "receiver_id": "merch_111",
        "amount": 100.0,
        "location_country": "US",
        "location_city": "New York",
        "device_id": "dev_test",
        "ip_address": "127.0.0.1",
        "merchant_category": "5812",
        "timestamp": datetime.now(UTC).replace(tzinfo=None),
    }
    await create_transaction(db_session, tx_payload)

    assessment_payload = {
        "assessment_id": "assess-123",
        "transaction_id": "tx-relation-test",
        "risk_score": 85.5,
        "recommendation": "BLOCK",
        "model_version": "xgboost-v1",
        "shap_values": {"amount": 0.45, "ip_country_mismatch": 0.2},
        "assessed_at": datetime.now(UTC).replace(tzinfo=None),
    }

    ra = await create_risk_assessment(db_session, assessment_payload)
    assert ra.assessment_id == "assess-123"
    assert ra.risk_score == 85.5

    # Retrieve and check relationship
    retrieved = await get_transaction_by_id(db_session, "tx-relation-test")
    assert retrieved.assessment is not None
    assert retrieved.assessment.risk_score == 85.5
    assert retrieved.assessment.shap_values["amount"] == 0.45


@pytest.mark.asyncio
async def test_audit_logs_creation(db_session):
    """
    Verifies audit logs logging and association with assessments.
    """
    tx_payload = {
        "transaction_id": "tx-audit-test",
        "sender_id": "usr_9999",
        "receiver_id": "merch_111",
        "amount": 5.0,
        "location_country": "US",
        "location_city": "NY",
        "device_id": "dev_test",
        "ip_address": "127.0.0.1",
        "merchant_category": "5812",
        "timestamp": datetime.now(UTC).replace(tzinfo=None),
    }
    await create_transaction(db_session, tx_payload)

    await create_risk_assessment(
        db_session,
        {
            "assessment_id": "assess-audit-123",
            "transaction_id": "tx-audit-test",
            "risk_score": 90.0,
            "recommendation": "BLOCK",
            "model_version": "xgboost-v1",
        },
    )

    log = await create_audit_log(
        db_session,
        assessment_id="assess-audit-123",
        reviewer_id="reviewer_alice",
        action="CONFIRMED_FRAUD",
        notes="Reviewer confirmed fraud pattern.",
    )
    assert log.reviewer_id == "reviewer_alice"
    assert log.action_taken == "CONFIRMED_FRAUD"

    # Eager load
    retrieved = await get_transaction_by_id(db_session, "tx-audit-test")
    assert len(retrieved.assessment.audit_logs) == 1
    assert retrieved.assessment.audit_logs[0].reviewer_id == "reviewer_alice"


@pytest.mark.asyncio
async def test_get_metrics_summary(db_session):
    """
    Verifies aggregated metrics calculations over date range.
    """
    today_date = date.today()

    # Insert 3 transactions
    txs = [
        {
            "transaction_id": "t1",
            "sender_id": "u1",
            "receiver_id": "m1",
            "amount": 10.0,
            "location_country": "US",
            "location_city": "NY",
            "device_id": "d1",
            "ip_address": "1",
            "merchant_category": "A",
            "timestamp": datetime.now(UTC).replace(tzinfo=None),
        },
        {
            "transaction_id": "t2",
            "sender_id": "u2",
            "receiver_id": "m2",
            "amount": 20.0,
            "location_country": "US",
            "location_city": "NY",
            "device_id": "d2",
            "ip_address": "2",
            "merchant_category": "A",
            "timestamp": datetime.now(UTC).replace(tzinfo=None),
        },
        {
            "transaction_id": "t3",
            "sender_id": "u3",
            "receiver_id": "m3",
            "amount": 30.0,
            "location_country": "US",
            "location_city": "NY",
            "device_id": "d3",
            "ip_address": "3",
            "merchant_category": "A",
            "timestamp": datetime.now(UTC).replace(tzinfo=None),
        },
    ]
    for tx in txs:
        await create_transaction(db_session, tx)

    # Assessments
    await create_risk_assessment(
        db_session,
        {
            "assessment_id": "a1",
            "transaction_id": "t1",
            "risk_score": 10.0,
            "recommendation": "ALLOW",
        },
    )
    await create_risk_assessment(
        db_session,
        {
            "assessment_id": "a2",
            "transaction_id": "t2",
            "risk_score": 50.0,
            "recommendation": "FLAG",
        },
    )
    await create_risk_assessment(
        db_session,
        {
            "assessment_id": "a3",
            "transaction_id": "t3",
            "risk_score": 95.0,
            "recommendation": "BLOCK",
        },
    )

    metrics = await get_metrics_summary(
        db_session, today_date - timedelta(days=1), today_date + timedelta(days=1)
    )

    assert metrics["total_processed_count"] == 3
    assert metrics["total_processed_value"] == 60.00
    assert metrics["overall_fraud_rate"] == pytest.approx(0.3333, abs=0.01)  # 1 block out of 3
    assert metrics["active_alerts_count"] == 2  # FLAG and BLOCK are alerts, neither has audit logs

    # Check risk score distribution count
    dist = {item["score_range"]: item["count"] for item in metrics["risk_distribution"]}
    assert dist["0-20"] == 1
    assert dist["41-60"] == 1
    assert dist["81-100"] == 1


@pytest.mark.asyncio
async def test_get_daily_trends(db_session):
    """
    Verifies daily trends grouping aggregates.
    """
    # Insert transactions spread over today and yesterday
    today_dt = datetime.now(UTC).replace(tzinfo=None)
    yesterday = today_dt - timedelta(days=1)

    await create_transaction(
        db_session,
        {
            "transaction_id": "y1",
            "sender_id": "u1",
            "receiver_id": "m1",
            "amount": 50.0,
            "location_country": "US",
            "location_city": "NY",
            "device_id": "d1",
            "ip_address": "1",
            "merchant_category": "A",
            "timestamp": yesterday,
        },
    )
    await create_transaction(
        db_session,
        {
            "transaction_id": "t1",
            "sender_id": "u2",
            "receiver_id": "m2",
            "amount": 150.0,
            "location_country": "US",
            "location_city": "NY",
            "device_id": "d2",
            "ip_address": "2",
            "merchant_category": "A",
            "timestamp": today_dt,
        },
    )

    await create_risk_assessment(
        db_session,
        {
            "assessment_id": "ay1",
            "transaction_id": "y1",
            "risk_score": 90.0,
            "recommendation": "BLOCK",
        },
    )
    await create_risk_assessment(
        db_session,
        {
            "assessment_id": "at1",
            "transaction_id": "t1",
            "risk_score": 10.0,
            "recommendation": "ALLOW",
        },
    )

    trends = await get_daily_trends(db_session, limit_days=5)

    assert len(trends) >= 2
    # Check yesterday's trend metrics (e.g. index -2 or depending on sorting)
    y_trend = next(item for item in trends if item["date"] == yesterday.date())
    t_trend = next(item for item in trends if item["date"] == today_dt.date())

    assert y_trend["total_transactions"] == 1
    assert y_trend["total_amount"] == 50.0
    assert y_trend["blocked_transactions"] == 1

    assert t_trend["total_transactions"] == 1
    assert t_trend["total_amount"] == 150.0
    assert t_trend["blocked_transactions"] == 0
