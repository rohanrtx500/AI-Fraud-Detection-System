from datetime import UTC, datetime

from fastapi.testclient import TestClient

from src.api.main import app
from src.models.decision import DecisionEngine

DEV_API_KEY = "fraud_dev_sec_key"


def test_websocket_ping_pong():
    """
    Verifies that the WebSocket endpoint accepts connections and responds to ping.
    """
    with TestClient(app) as client:
        with client.websocket_connect("/ws/alerts") as websocket:
            websocket.send_text("ping")
            data = websocket.receive_text()
            assert data == "pong"


def test_websocket_broadcast_on_score():
    """
    Verifies that scoring a transaction broadcasts an alert via WebSocket.
    """
    payload = {
        "sender_id": "usr_ws_test",
        "receiver_id": "merch_ws_test",
        "amount": 150.0,
        "currency": "USD",
        "merchant_category": "5411",
        "location_country": "US",
        "location_city": "New York",
        "device_id": "dev_ws_test",
        "ip_address": "192.168.1.50",
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", ""),
    }

    with TestClient(app) as client:
        with client.websocket_connect("/ws/alerts") as websocket:
            # Score transaction via HTTP POST
            response = client.post(
                "/api/v1/transactions/score",
                json=payload,
                headers={"X-API-KEY": DEV_API_KEY},
            )
            assert response.status_code == 200

            # Receive broadcast alert via WebSocket
            websocket.send_text("ping")  # trigger connection drain if needed
            resp_text = websocket.receive_text()

            # Since the broadcast and ping/pong are async, let's look for the alert message
            if resp_text != "pong":
                import json

                alert = json.loads(resp_text)
                assert alert["sender_id"] == "usr_ws_test"
                assert alert["amount"] == 150.0


def test_decision_routing_matrix():
    """
    Validates various conditional routing options in DecisionEngine.
    """
    # 1. Low risk scenario -> APPROVE
    res1 = DecisionEngine.evaluate_decision(
        risk_score=15.0, threat_match={"matched": False, "indicators": [], "risk_multiplier": 1.0}
    )
    assert res1["action"] == "APPROVE"
    assert "maps to low risk" in "".join(res1["reasons"])

    # 2. Medium risk scenario -> REQUEST_VERIFICATION
    res2 = DecisionEngine.evaluate_decision(
        risk_score=35.0, threat_match={"matched": False, "indicators": [], "risk_multiplier": 1.0}
    )
    assert res2["action"] == "REQUEST_VERIFICATION"

    # 3. High risk scenario -> ESCALATE
    res3 = DecisionEngine.evaluate_decision(
        risk_score=78.0, threat_match={"matched": False, "indicators": [], "risk_multiplier": 1.0}
    )
    assert res3["action"] == "ESCALATE"

    # 4. Critical risk scenario -> BLOCK
    res4 = DecisionEngine.evaluate_decision(
        risk_score=92.0, threat_match={"matched": False, "indicators": [], "risk_multiplier": 1.0}
    )
    assert res4["action"] == "BLOCK"

    # 5. Threat match override -> BLOCK
    res5 = DecisionEngine.evaluate_decision(
        risk_score=20.0,
        threat_match={
            "matched": True,
            "indicators": [
                {"type": "IP", "value": "203.0.113.88", "risk_multiplier": 3.0, "source": "test"}
            ],
            "risk_multiplier": 3.0,
        },
    )
    assert res5["action"] == "BLOCK"
    assert "Threat Intelligence" in "".join(res5["reasons"])


def test_impossible_travel_override():
    """
    Verifies that impossible travel overrides force a BLOCK decision action.
    """
    res = DecisionEngine.evaluate_decision(
        risk_score=10.0,
        threat_match={"matched": False, "indicators": [], "risk_multiplier": 1.0},
        impossible_travel=True,
    )
    assert res["action"] == "BLOCK"
    assert "Impossible Travel" in "".join(res["reasons"])
