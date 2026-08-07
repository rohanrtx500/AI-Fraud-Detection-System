from datetime import datetime

import pytest


@pytest.fixture
def mock_transaction_payload() -> dict:
    """
    Returns a valid mock transaction ingestion payload.
    """
    return {
        "transaction_id": "tx_abc123",
        "sender_id": "user_88432",
        "receiver_id": "merchant_2319",
        "amount": 250.50,
        "currency": "USD",
        "merchant_category": "5411",
        "location_country": "US",
        "location_city": "Los Angeles",
        "device_id": "device_fingerprint_xyz",
        "ip_address": "192.168.1.100",
    }


@pytest.fixture
def mock_scoring_response() -> dict:
    """
    Returns a mock transaction risk assessment outcome.
    """
    return {
        "transaction_id": "tx-test-uuid-99",
        "risk_score": 15.2,
        "recommendation": "ALLOW",
        "model_version": "xgboost-v1.0.0",
        "assessed_at": datetime.utcnow().isoformat(),
        "explanations": [],
    }
