import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from src.api.main import app
from src.models.monitoring import ModelMonitor, calculate_psi

DEV_API_KEY = "fraud_dev_sec_key"
HEADERS = {"X-API-KEY": DEV_API_KEY}


def test_calculate_psi_identical():
    """
    Identical distributions should yield a PSI near 0.0.
    """
    expected = np.random.normal(50, 10, 1000)
    actual = expected.copy()
    psi = calculate_psi(expected, actual)
    assert abs(psi) < 0.05


def test_calculate_psi_divergent():
    """
    Significantly divergent distributions should yield a high PSI.
    """
    expected = np.random.normal(30, 5, 1000)
    actual = np.random.normal(60, 5, 1000)
    psi = calculate_psi(expected, actual)
    assert psi > 0.5


def test_calculate_psi_edge_cases():
    """
    Checks calculation with empty arrays and zero smoothing.
    """
    assert calculate_psi(np.array([]), np.array([])) == 0.0

    # Expected lacks some buckets completely
    expected = np.array([5.0, 5.0, 5.0])
    actual = np.array([95.0, 95.0, 95.0])
    psi = calculate_psi(expected, actual)
    assert psi > 0.0


def test_model_monitor_performance_metrics_fallback(tmp_path):
    """
    Verifies that performance calculations fall back to stable metrics
    if there are fewer than 5 resolved cases in the DB.
    """
    report_file = tmp_path / "monitoring_report.json"
    monitor = ModelMonitor(report_path=str(report_file))

    class MockResult:
        def all(self):
            return []  # 0 resolved cases

    class MockDb:
        async def execute(self, stmt):
            return MockResult()

    import asyncio

    metrics = asyncio.run(monitor.calculate_performance_metrics(MockDb()))
    assert metrics["is_baseline_estimate"] is True
    assert metrics["sample_size"] == 0
    assert metrics["f1_score"] == 0.847


def test_model_monitor_performance_metrics_live(tmp_path):
    """
    Verifies metric calculations with sufficient ground truth resolved cases.
    """
    report_file = tmp_path / "monitoring_report.json"
    monitor = ModelMonitor(report_path=str(report_file))

    # Mock resolved cases: 4 True Positives, 1 False Positive, 1 True Negative, 0 False Negatives
    # Predicted is 1 if score >= 50
    # Confirmed is 1 if status is RESOLVED, benign if FALSE_POSITIVE
    class MockResult:
        def all(self):
            return [
                (80.0, "RESOLVED"),  # TP
                (90.0, "RESOLVED"),  # TP
                (70.0, "RESOLVED"),  # TP
                (55.0, "RESOLVED"),  # TP
                (60.0, "FALSE_POSITIVE"),  # FP
                (20.0, "FALSE_POSITIVE"),  # TN
            ]

    class MockDb:
        async def execute(self, stmt):
            return MockResult()

    import asyncio

    metrics = asyncio.run(monitor.calculate_performance_metrics(MockDb()))
    assert metrics["is_baseline_estimate"] is False
    assert metrics["sample_size"] == 6
    assert metrics["accuracy"] == round(5 / 6, 4)
    assert metrics["precision"] == round(4 / 5, 4)
    assert metrics["recall"] == round(4 / 4, 4)
    assert metrics["f1_score"] == round(2 * (0.8 * 1.0) / (0.8 + 1.0), 4)


def test_model_monitor_evaluate_drift(tmp_path):
    """
    Verifies KS test evaluation on baseline and target dataframes.
    """
    report_file = tmp_path / "monitoring_report.json"
    monitor = ModelMonitor(report_path=str(report_file))

    df_base = pd.DataFrame(
        {
            "amount": np.random.normal(10, 1, 100),
            "hour_of_day": np.random.randint(0, 24, 100),
            "day_of_week": np.random.randint(0, 7, 100),
            "user_velocity_5m": np.zeros(100),
            "user_velocity_1h": np.ones(100),
            "amount_to_user_avg_ratio": np.ones(100),
            "ip_country_mismatch": np.zeros(100),
        }
    )

    # Target distribution matches baseline
    df_target = df_base.copy()

    drift_report = monitor.evaluate_drift(df_base, df_target)
    for feat in monitor.numerical_features:
        assert feat in drift_report
        assert drift_report[feat]["status"] == "STABLE"


def test_monitoring_api_endpoints():
    """
    Verifies FastAPI routing integration and authorization guards.
    """
    with TestClient(app) as client:
        # 1. Access denied without API key
        res = client.get("/api/v1/monitoring/report")
        assert res.status_code == 403

        res = client.post("/api/v1/monitoring/run")
        assert res.status_code == 403

        # 2. Access allowed with API key (GET report)
        res = client.get("/api/v1/monitoring/report", headers=HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert "last_run" in data
        assert "performance" in data
        assert "feature_drift" in data
        assert "prediction_drift" in data
        assert "class_distribution" in data
        assert "alerts" in data

        # 3. Access allowed with API key (POST run cycle)
        res = client.post("/api/v1/monitoring/run", headers=HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert "last_run" in data
        assert "performance" in data
        assert "prediction_drift" in data
