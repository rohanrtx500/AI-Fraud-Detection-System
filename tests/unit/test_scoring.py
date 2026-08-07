import pandas as pd
import pytest

from src.models.scoring_engine import FraudRiskScoringEngine


@pytest.fixture
def scoring_engine() -> FraudRiskScoringEngine:
    return FraudRiskScoringEngine()


def test_calculate_sub_scores(scoring_engine):
    """
    Verifies that individual sub-risk calculations map correctly.
    """
    # 1. Location Risk
    mismatch_tx = pd.Series({"ip_country_mismatch": 1})
    assert scoring_engine.calculate_location_risk(mismatch_tx) == 90.0

    normal_loc_tx = pd.Series({"ip_country_mismatch": 0})
    assert scoring_engine.calculate_location_risk(normal_loc_tx) == 10.0

    # 2. Frequency Risk
    low_vel_tx = pd.Series({"user_velocity_5m": 0, "user_velocity_1h": 1})
    assert scoring_engine.calculate_frequency_risk(low_vel_tx) == 10.0

    high_vel_tx = pd.Series({"user_velocity_5m": 3, "user_velocity_1h": 5})
    assert scoring_engine.calculate_frequency_risk(high_vel_tx) == 98.0

    # 3. Amount Risk
    small_tx = pd.Series({"amount": 20.0, "amount_to_user_avg_ratio": 0.8})
    assert scoring_engine.calculate_amount_risk(small_tx) == 10.0

    large_tx = pd.Series({"amount": 5000.0, "amount_to_user_avg_ratio": 12.0})
    assert scoring_engine.calculate_amount_risk(large_tx) == 98.0


def test_scoring_buckets_low(scoring_engine):
    """
    Verifies low risk transactions fall in 0-30 Low bucket.
    """
    low_risk_tx = pd.Series(
        {
            "amount": 25.0,
            "amount_to_user_avg_ratio": 0.9,
            "user_velocity_5m": 0,
            "user_velocity_1h": 1,
            "ip_country_mismatch": 0,
            "hour_of_day": 12,
        }
    )
    res = scoring_engine.score_transaction(low_risk_tx, ml_prob=0.01)

    assert res["risk_score"] <= 30.00
    assert res["risk_bucket"] == "Low"
    assert res["sub_scores"]["location_risk"] == 10.0


def test_scoring_buckets_medium(scoring_engine):
    """
    Verifies moderate risk transactions fall in 31-60 Medium bucket.
    """
    med_risk_tx = pd.Series(
        {
            "amount": 150.0,
            "amount_to_user_avg_ratio": 2.1,  # Moderate ratio spend
            "user_velocity_5m": 1,  # Velocity = 1
            "user_velocity_1h": 2,
            "ip_country_mismatch": 0,
            "hour_of_day": 12,
        }
    )
    res = scoring_engine.score_transaction(med_risk_tx, ml_prob=0.15)

    assert 30.0 < res["risk_score"] <= 60.00
    assert res["risk_bucket"] == "Medium"


def test_scoring_buckets_high(scoring_engine):
    """
    Verifies high risk transactions fall in 61-80 High bucket.
    """
    high_risk_tx = pd.Series(
        {
            "amount": 850.0,
            "amount_to_user_avg_ratio": 4.5,
            "user_velocity_5m": 1,
            "user_velocity_1h": 3,
            "ip_country_mismatch": 0,
            "hour_of_day": 2,  # Night time risk offset
        }
    )
    res = scoring_engine.score_transaction(high_risk_tx, ml_prob=0.45)

    assert 60.0 < res["risk_score"] <= 80.00
    assert res["risk_bucket"] == "High"


def test_scoring_buckets_critical(scoring_engine):
    """
    Verifies critical risk transactions (hops/high velocity/amounts) fall in 81-100 Critical bucket.
    """
    critical_risk_tx = pd.Series(
        {
            "amount": 4500.0,
            "amount_to_user_avg_ratio": 15.0,
            "user_velocity_5m": 3,
            "user_velocity_1h": 8,
            "ip_country_mismatch": 1,
            "hour_of_day": 3,
        }
    )
    res = scoring_engine.score_transaction(critical_risk_tx, ml_prob=0.95)

    assert res["risk_score"] >= 81.00
    assert res["risk_bucket"] == "Critical"
    assert res["sub_scores"]["location_risk"] == 90.0
    assert res["sub_scores"]["frequency_risk"] == 98.0
