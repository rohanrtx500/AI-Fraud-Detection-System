from fastapi.testclient import TestClient

from src.api.main import app

# Default dev security key configured in security middleware
DEV_API_KEY = "fraud_dev_sec_key"


def test_health_check_endpoint():
    """
    Verifies that the public health liveness probe responds successfully without authentication.
    """
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "service": "fraud-detection-api"}


def test_score_transaction_endpoint_unauthorized(mock_transaction_payload):
    """
    Assures that accessing transactions/score without key triggers 403 Forbidden.
    """
    with TestClient(app) as client:
        # 1. Missing header
        response = client.post("/api/v1/transactions/score", json=mock_transaction_payload)
        assert response.status_code == 403

        # 2. Invalid header key
        response = client.post(
            "/api/v1/transactions/score",
            json=mock_transaction_payload,
            headers={"X-API-KEY": "wrong_key"},
        )
        assert response.status_code == 403


def test_score_transaction_endpoint_authorized(mock_transaction_payload):
    """
    Verifies transactions/score accepts valid API keys and returns prediction keys.
    """
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/transactions/score",
            json=mock_transaction_payload,
            headers={"X-API-KEY": DEV_API_KEY},
        )
        assert response.status_code == 200

        data = response.json()
        assert "risk_score" in data
        assert "recommendation" in data
        assert "explanations" in data


def test_active_model_endpoint_authorized():
    """
    Verifies active models endpoint retrieves dynamic metadata under valid keys.
    """
    with TestClient(app) as client:
        response = client.get("/api/v1/models/active", headers={"X-API-KEY": DEV_API_KEY})
        assert response.status_code == 200

        data = response.json()
        assert "model_version" in data
        assert "metrics" in data
        assert "registered_user_profiles_count" in data
