from datetime import datetime, timedelta

import pandas as pd
import pytest

from src.features.profiling import (
    calculate_behavioral_deviations,
    fit_user_profiles,
    load_profile,
    save_profile,
)


@pytest.fixture
def mock_user_history() -> pd.DataFrame:
    """
    Returns a dataframe of historical transactions for usr_99 to fit behavior.
    """
    base_time = datetime(2026, 6, 1, 12, 0, 0)
    history = []

    # Generate 10 standard daily transactions
    for i in range(10):
        tx_time = base_time + timedelta(days=i)
        history.append(
            {
                "transaction_id": f"tx_hist_{i}",
                "sender_id": "usr_99",
                "receiver_id": f"merch_{i}",
                "amount": 50.00,  # Constant spend
                "currency": "USD",
                "merchant_category": "5411",
                "location_country": "US",  # Constant country
                "location_city": "Los Angeles",
                "device_id": "dev_macbook_home",  # Constant device
                "ip_address": "192.168.1.10",
                "timestamp": tx_time.isoformat(),
                "is_fraud": 0,
            }
        )
    return pd.DataFrame(history)


def test_fit_and_serialize_profile(mock_user_history, tmp_path):
    """
    Verifies behavioral profile fitting and JSON serialization.
    """
    profiles = fit_user_profiles(mock_user_history)
    assert "usr_99" in profiles

    profile = profiles["usr_99"]
    assert profile.avg_amount == 50.0
    assert profile.std_amount == 0.0  # Standard dev of constant list is zero
    assert profile.preferred_countries == ["US"]
    assert profile.preferred_devices == ["dev_macbook_home"]
    assert profile.typical_hours == [12]

    # Save & Load test
    save_dir = str(tmp_path / "profiles")
    save_profile("usr_99", profile, directory=save_dir)

    loaded = load_profile("usr_99", directory=save_dir)
    assert loaded is not None
    assert loaded.sender_id == "usr_99"
    assert loaded.avg_amount == 50.0
    assert loaded.preferred_countries == ["US"]


def test_profiling_deviations_normal(mock_user_history):
    """
    Verifies that a standard transaction matches the user's learned baseline (zero deviations).
    """
    profiles = fit_user_profiles(mock_user_history)
    profile = profiles["usr_99"]

    # Transaction matching normal habits
    normal_payload = {
        "sender_id": "usr_99",
        "amount": 52.00,  # Z-score deviation will be small
        "location_country": "US",
        "location_city": "Los Angeles",
        "device_id": "dev_macbook_home",
        "timestamp": "2026-06-11T12:30:00",  # 1.02 days after last (normal frequency)
    }

    deviations = calculate_behavioral_deviations(normal_payload, profile)

    assert deviations["location_country_deviation"] == 0
    assert deviations["location_city_deviation"] == 0
    assert deviations["device_deviation"] == 0
    assert deviations["time_deviation"] == 0
    assert deviations["frequency_deviation"] == 0


def test_profiling_deviations_anomaly(mock_user_history):
    """
    Verifies that deviations in amount, location, device, hour, and velocity are correctly flagged.
    """
    profiles = fit_user_profiles(mock_user_history)
    profile = profiles["usr_99"]

    # Fraudulent/anomalous transaction payload
    anomalous_payload = {
        "sender_id": "usr_99",
        "amount": 1500.00,  # 30x average spend
        "location_country": "RU",  # Unseen country
        "location_city": "Moscow",  # Unseen city
        "device_id": "dev_unknown_hacker",  # Unseen device
        "timestamp": "2026-06-10T03:00:00",  # Unseen hour (3 AM vs 12 PM) and occurs only 15 hours after last tx
    }

    deviations = calculate_behavioral_deviations(anomalous_payload, profile)

    assert deviations["amount_z_score"] > 3.0
    assert deviations["location_country_deviation"] == 1
    assert deviations["location_city_deviation"] == 1
    assert deviations["device_deviation"] == 1
    assert deviations["time_deviation"] == 1

    # Frequency velocity check
    # avg_inter_time_seconds for usr_99 is 1 day (86400s).
    # anomalous_payload timestamp is 2026-06-10T03:00:00.
    # Last tx timestamp in mock history is 2026-06-10T12:00:00 (i.e., 10th day at index 9).
    # Wait, 2026-06-10T03:00:00 is BEFORE the last transaction in history (2026-06-10T12:00:00), which represents negative time diff.
    # Let's adjust timestamp to be immediately AFTER the last transaction to test speed velocity anomaly:
    # last transaction was datetime(2026, 6, 1, 12, 0, 0) + 9 days = datetime(2026, 6, 10, 12, 0, 0).
    # Let's set anomalous timestamp to 2026-06-10T12:01:00 (60 seconds after last, which is < 1% of 86400s average!).
    anomalous_payload["timestamp"] = "2026-06-10T12:01:00"

    deviations_fast = calculate_behavioral_deviations(anomalous_payload, profile)
    assert deviations_fast["frequency_deviation"] == 1
