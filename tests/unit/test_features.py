import pandas as pd
import pytest

from src.features.pipeline import (
    engineer_features,
    handle_missing_values,
    load_raw_dataset,
    validate_dataframe,
)


def test_load_raw_dataset_missing():
    """
    Checks that non-existent paths raise FileNotFoundError.
    """
    with pytest.raises(FileNotFoundError):
        load_raw_dataset("non_existent_file.csv")


def test_validate_dataframe_invalid_amount(mock_transaction_payload):
    """
    Verifies validation rejects invalid transaction amounts.
    """
    df = pd.DataFrame([mock_transaction_payload])
    df["amount"] = 0.00  # Invalid (minimum is 0.01)
    df["timestamp"] = "2026-06-05T12:00:00"

    with pytest.raises(ValueError, match="amounts below minimum threshold"):
        validate_dataframe(df)


def test_handle_missing_values(mock_transaction_payload, tmp_path):
    """
    Verifies missing numeric and categorical columns are filled correctly.
    """
    # Create simple dataframe with missing values
    df = pd.DataFrame(
        [mock_transaction_payload, {**mock_transaction_payload, "amount": None, "currency": None}]
    )
    df["timestamp"] = "2026-06-05T12:00:00"

    # Setup temp path to save metadata stats
    stats_dir = str(tmp_path)

    # Run fit imputing
    df_clean, stats = handle_missing_values(df, is_training=True, stats_dir=stats_dir)

    assert df_clean["amount"].isnull().sum() == 0
    assert df_clean["currency"].isnull().sum() == 0
    assert (
        df_clean.iloc[1]["amount"] == mock_transaction_payload["amount"]
    )  # Median of single present value


def test_engineer_features(mock_transaction_payload, tmp_path):
    """
    Verifies that temporal and velocity feature transformations are calculated properly.
    """
    stats_dir = str(tmp_path)

    # Generate sequential transactions for a user to test rolling features
    tx1 = {
        **mock_transaction_payload,
        "sender_id": "usr_99",
        "location_country": "US",
        "amount": 100.0,
        "timestamp": "2026-06-05T12:00:00",
    }
    tx2 = {
        **mock_transaction_payload,
        "sender_id": "usr_99",
        "location_country": "US",
        "amount": 150.0,
        "timestamp": "2026-06-05T12:02:00",  # 2 mins later
    }
    tx3 = {
        **mock_transaction_payload,
        "sender_id": "usr_99",
        "location_country": "US",
        "amount": 200.0,
        "timestamp": "2026-06-05T12:04:00",  # 4 mins after tx1
    }
    tx4 = {
        **mock_transaction_payload,
        "sender_id": "usr_99",
        "location_country": "RU",  # IP Mismatch!
        "amount": 50.0,
        "timestamp": "2026-06-05T12:09:00",  # 9 mins after tx1, 5 mins after tx3
    }

    df = pd.DataFrame([tx1, tx2, tx3, tx4])

    # Need to run imputation first to serialize baseline stats
    df_clean, _ = handle_missing_values(df, is_training=True, stats_dir=stats_dir)

    # Fit engineer features
    df_engineered = engineer_features(df_clean, is_training=True, stats_dir=stats_dir)

    # Assertions
    assert "hour_of_day" in df_engineered.columns
    assert "day_of_week" in df_engineered.columns

    # Velocity asserts (lookback count excludes current transaction)
    # tx1 (12:00) -> 0 prior transactions
    assert df_engineered.iloc[0]["user_velocity_5m"] == 0
    # tx2 (12:02) -> 1 prior transaction (tx1)
    assert df_engineered.iloc[1]["user_velocity_5m"] == 1
    # tx3 (12:04) -> 2 prior transactions (tx1, tx2)
    assert df_engineered.iloc[2]["user_velocity_5m"] == 2
    # tx4 (12:09) -> only tx3 is within 5 minutes of 12:09 (closed='left' excludes 12:09, 12:04 to 12:09 is exactly 5 min)
    # Let's verify lookback of 5min at 12:09.
    # The lookback time window is (12:04, 12:09). tx3 timestamp is 12:04.
    # 12:09 - 5 minutes = 12:04. Since closed='left', the window is [12:04, 12:09), which includes 12:04.
    # Therefore, user_velocity_5m for tx4 should be 1 (tx3).
    assert df_engineered.iloc[3]["user_velocity_5m"] == 1

    # Hour velocity asserts (1 hour lookback)
    # tx4 (12:09) -> 3 prior transactions (tx1, tx2, tx3) within 1 hour
    assert df_engineered.iloc[3]["user_velocity_1h"] == 3

    # IP country mismatch asserts
    # Mode country for usr_99 is US, so tx4 (RU) should trigger mismatch
    assert df_engineered.iloc[0]["ip_country_mismatch"] == 0
    assert df_engineered.iloc[3]["ip_country_mismatch"] == 1

    # Amount average ratio asserts
    # usr_99 mean amount: (100+150+200+50)/4 = 125.0
    # tx1 amount: 100.0. Ratio: 100.0 / 125.0 = 0.8
    assert round(df_engineered.iloc[0]["amount_to_user_avg_ratio"], 2) == 0.80
