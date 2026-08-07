from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database.connection import Base
from src.database.models import Case, RiskAssessment, Transaction
from src.models.synthetic_engine import CITIES, SyntheticFraudEngine, haversine_distance

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_session():
    """
    In-memory SQLite database session fixture.
    """
    engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()
        await session.close()
    await engine.dispose()


def test_haversine_distance():
    # NYC to London should be ~5570 km
    nyc = CITIES["New York"]
    london = CITIES["London"]
    dist = haversine_distance(nyc["lat"], nyc["lon"], london["lat"], london["lon"])
    assert abs(dist - 5570) < 100  # within reasonable tolerances


def test_engine_init():
    engine = SyntheticFraudEngine(seed=100)
    assert engine.seed == 100
    assert len(engine.device_pool) == 100
    assert len(engine.merchant_pool) == 50


def test_user_profiles_generation():
    engine = SyntheticFraudEngine()
    profiles = engine.generate_user_profiles(num_users=10)
    assert len(profiles) == 10

    for uid, prof in profiles.items():
        assert uid.startswith("usr_")
        assert prof["home_city"] in CITIES
        assert len(prof["common_devices"]) >= 1
        assert len(prof["common_ips"]) >= 1
        assert prof["mean_amount"] > 0
        assert len(prof["typical_mccs"]) == 3
        assert prof["currency"] in ["USD", "CAD", "EUR"]


def test_benign_transaction():
    engine = SyntheticFraudEngine()
    engine.generate_user_profiles(num_users=5)
    uid = list(engine.user_profiles.keys())[0]

    ts = datetime.now(UTC).replace(tzinfo=None)
    tx = engine.generate_benign_transaction(uid, ts)

    assert tx["sender_id"] == uid
    assert tx["amount"] > 0.0
    assert tx["is_fraud"] == 0
    assert tx["scenario_type"] == "normal"
    assert tx["location_country"] == engine.user_profiles[uid]["home_country"]
    assert tx["location_city"] == engine.user_profiles[uid]["home_city"]
    assert tx["timestamp"] == ts


def test_scenario_account_takeover():
    engine = SyntheticFraudEngine()
    engine.generate_user_profiles(num_users=2)
    uid = list(engine.user_profiles.keys())[0]

    start = datetime.now(UTC).replace(tzinfo=None)
    events = engine.generate_account_takeover(uid, start)

    # Check counts (2 benign + 3 fraud = 5 events)
    assert len(events) == 5

    # Benign events
    assert events[0]["is_fraud"] == 0
    assert events[1]["is_fraud"] == 0

    # Fraud takeover events
    assert events[2]["is_fraud"] == 1
    assert events[2]["scenario_type"] == "account_takeover"
    assert events[2]["location_city"] in ["Moscow", "Tokyo"]
    assert events[2]["device_id"] != events[0]["device_id"]
    assert events[2]["amount"] > events[0]["amount"]


def test_scenario_card_testing():
    engine = SyntheticFraudEngine()
    engine.generate_user_profiles(num_users=2)
    uid = list(engine.user_profiles.keys())[0]

    start = datetime.now(UTC).replace(tzinfo=None)
    events = engine.generate_card_testing(uid, start)

    # 4 small checks + 1 target payout = 5 events
    assert len(events) == 5
    for i in range(4):
        assert events[i]["amount"] <= 2.50
        assert events[i]["is_fraud"] == 1
        assert events[i]["scenario_type"] == "card_testing"

    assert events[4]["amount"] >= 850.00
    assert events[4]["is_fraud"] == 1


def test_scenario_velocity_attack():
    engine = SyntheticFraudEngine()
    engine.generate_user_profiles(num_users=2)
    uid = list(engine.user_profiles.keys())[0]

    start = datetime.now(UTC).replace(tzinfo=None)
    events = engine.generate_velocity_attack(uid, start)

    assert len(events) == 8
    for i in range(7):
        time_diff = (events[i + 1]["timestamp"] - events[i]["timestamp"]).total_seconds()
        assert 5 <= time_diff <= 20
        assert events[i]["is_fraud"] == 1
        assert events[i]["scenario_type"] == "velocity_attack"


def test_scenario_device_spoofing():
    engine = SyntheticFraudEngine()
    engine.generate_user_profiles(num_users=2)

    start = datetime.now(UTC).replace(tzinfo=None)
    events = engine.generate_device_spoofing(start)

    assert len(events) == 8
    shared_dev = events[0]["device_id"]

    # Verify same device used by different users
    for i, ev in enumerate(events):
        assert ev["device_id"] == shared_dev
        assert ev["sender_id"] == f"usr_spoof_{100 + i}"
        assert ev["is_fraud"] == 1
        assert ev["scenario_type"] == "device_spoofing"


def test_scenario_location_anomaly():
    engine = SyntheticFraudEngine()
    engine.generate_user_profiles(num_users=2)
    uid = list(engine.user_profiles.keys())[0]

    start = datetime.now(UTC).replace(tzinfo=None)
    events = engine.generate_location_anomaly(uid, start)

    assert len(events) == 2
    ev1, ev2 = events[0], events[1]

    assert ev1["location_city"] == "New York"
    assert ev2["location_city"] == "London"
    assert ev1["is_fraud"] == 0
    assert ev2["is_fraud"] == 1
    assert ev2["scenario_type"] == "impossible_travel"

    # Calculate travel speed
    time_diff_hours = (ev2["timestamp"] - ev1["timestamp"]).total_seconds() / 3600.0
    c1 = CITIES[ev1["location_city"]]
    c2 = CITIES[ev2["location_city"]]
    distance = haversine_distance(c1["lat"], c1["lon"], c2["lat"], c2["lon"])
    speed = distance / time_diff_hours

    # Speed should be supersonic (~22000 km/h)
    assert speed > 10000.0


def test_scenario_merchant_abuse():
    engine = SyntheticFraudEngine()
    engine.generate_user_profiles(num_users=2)

    start = datetime.now(UTC).replace(tzinfo=None)
    events = engine.generate_merchant_abuse(start)

    assert len(events) == 12
    target_merchant = events[0]["receiver_id"]

    refunds_count = 0
    for ev in events:
        assert ev["receiver_id"] == target_merchant
        assert ev["is_fraud"] == 1
        assert ev["scenario_type"] == "merchant_abuse"
        if ev["amount"] < 0:
            refunds_count += 1

    assert refunds_count > 0


def test_build_dataset():
    engine = SyntheticFraudEngine()
    df = engine.build_dataset(
        num_normal=100,
        num_ato=1,
        num_card_testing=1,
        num_velocity=1,
        num_device_spoofing=1,
        num_location_anomaly=1,
        num_merchant_abuse=1,
    )

    # Total count = 100 + 5 (ATO) + 5 (Card) + 8 (Velocity) + 8 (Spoof) + 2 (Travel) + 12 (Abuse) = 140 transactions
    assert len(df) == 140
    assert "timestamp" in df.columns
    assert "is_fraud" in df.columns
    assert "scenario_type" in df.columns

    # Check sorted chronologically
    timestamps = df["timestamp"].tolist()
    assert all(timestamps[i] <= timestamps[i + 1] for i in range(len(timestamps) - 1))


@pytest.mark.asyncio
async def test_seed_database(db_session):
    engine = SyntheticFraudEngine()
    df = engine.build_dataset(
        num_normal=10,
        num_ato=1,
        num_card_testing=1,
        num_velocity=1,
        num_device_spoofing=1,
        num_location_anomaly=1,
        num_merchant_abuse=1,
    )

    # Seed
    await engine.seed_database(db_session, df)

    # Query database to check insertions
    res_tx = await db_session.execute(select(Transaction))
    txs = res_tx.all()
    assert len(txs) == len(df)

    res_ra = await db_session.execute(select(RiskAssessment))
    ras = res_ra.all()
    assert len(ras) == len(df)

    # Some cases must be created since we trigger case creation on BLOCK/FLAG scenarios
    res_cases = await db_session.execute(select(Case))
    cases = res_cases.all()
    assert len(cases) > 0
