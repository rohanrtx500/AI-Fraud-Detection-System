import os

import numpy as np
import pandas as pd
import pytest

from src.models.classifier import FraudXGBoostClassifier
from src.models.evaluate import evaluate_models
from src.models.inference import FraudInferenceEngine
from src.models.train import train_models


@pytest.fixture
def sample_features_df(mock_transaction_payload) -> pd.DataFrame:
    """
    Returns a pandas DataFrame matching final engineered features shape for testing.
    """
    # Create simple feature rows
    rows = []
    for i in range(5):
        rows.append(
            {
                "amount": 100.0 + (i * 50.0),
                "hour_of_day": 12,
                "day_of_week": 2,
                "user_velocity_5m": i,
                "user_velocity_1h": i + 2,
                "amount_to_user_avg_ratio": 1.0 + (i * 0.1),
                "ip_country_mismatch": 0 if i % 2 == 0 else 1,
                "merchant_category": "5411",
                "location_country": "US",
                "currency": "USD",
            }
        )
    return pd.DataFrame(rows)


def test_model_training_and_evaluation(tmp_path):
    """
    Tests fitting models, serializing pipelines, and evaluating outputs.
    """
    models_dir = str(tmp_path / "models")
    os.makedirs(models_dir, exist_ok=True)

    # 1. Create a dummy dataset
    # We create a tiny train and test CSV to fit scikit-learn models
    train_data = []
    for _i in range(100):
        train_data.append(
            {
                "amount": float(np.random.exponential(100.0)),
                "hour_of_day": int(np.random.randint(0, 24)),
                "day_of_week": int(np.random.randint(0, 7)),
                "user_velocity_5m": int(np.random.randint(0, 3)),
                "user_velocity_1h": int(np.random.randint(0, 10)),
                "amount_to_user_avg_ratio": float(np.random.uniform(0.5, 2.0)),
                "ip_country_mismatch": int(np.random.choice([0, 1], p=[0.9, 0.1])),
                "merchant_category": str(np.random.choice(["5411", "5812", "5944"])),
                "location_country": str(np.random.choice(["US", "CA", "GB"])),
                "currency": "USD",
                "is_fraud": int(np.random.choice([0, 1], p=[0.95, 0.05])),  # 5% fraud rate
            }
        )

    train_df = pd.DataFrame(train_data)

    train_path = str(tmp_path / "train.csv")
    test_path = str(tmp_path / "test.csv")
    train_df.to_csv(train_path, index=False)
    train_df.to_csv(test_path, index=False)  # Reuse for test baseline

    # 2. Run training
    train_models(train_data_path=train_path, output_dir=models_dir)

    # Assert model files were created
    assert os.path.exists(os.path.join(models_dir, "xgboost_pipeline.joblib"))
    assert os.path.exists(os.path.join(models_dir, "random_forest_pipeline.joblib"))
    assert os.path.exists(os.path.join(models_dir, "isolation_forest_pipeline.joblib"))

    # 3. Run evaluation
    metrics = evaluate_models(test_data_path=test_path, models_dir=models_dir)

    assert "xgboost" in metrics
    assert "random_forest" in metrics
    assert "isolation_forest" in metrics
    assert "roc_auc" in metrics["xgboost"]


def test_inference_scoring_engine(tmp_path, sample_features_df):
    """
    Tests loading pipelines in the scoring engine and scoring a single transactional features frame.
    """
    models_dir = str(tmp_path / "models")
    os.makedirs(models_dir, exist_ok=True)

    # Re-train simple model inside tmp_path
    train_data = []
    for i in range(50):
        train_data.append(
            {
                "amount": 100.0,
                "hour_of_day": 12,
                "day_of_week": 2,
                "user_velocity_5m": 1,
                "user_velocity_1h": 2,
                "amount_to_user_avg_ratio": 1.0,
                "ip_country_mismatch": 0,
                "merchant_category": "5411",
                "location_country": "US",
                "currency": "USD",
                "is_fraud": 0 if i < 48 else 1,
            }
        )
    pd.DataFrame(train_data).to_csv(str(tmp_path / "train.csv"), index=False)
    train_models(train_data_path=str(tmp_path / "train.csv"), output_dir=models_dir)

    # Instantiate inference engine
    engine = FraudInferenceEngine(models_dir=models_dir)

    import asyncio

    # Test scoring with XGBoost
    xgb_out = asyncio.run(
        engine.score_transaction(sample_features_df.iloc[[0]], model_type="xgboost")
    )
    assert 0.0 <= xgb_out["risk_score"] <= 100.0
    assert xgb_out["recommendation"] in ["ALLOW", "FLAG", "BLOCK"]
    assert xgb_out["model_version"] == "xgboost-v1.0.0"

    # Test scoring with Random Forest
    rf_out = asyncio.run(
        engine.score_transaction(sample_features_df.iloc[[0]], model_type="random_forest")
    )
    assert 0.0 <= rf_out["risk_score"] <= 100.0
    assert rf_out["recommendation"] in ["ALLOW", "FLAG", "BLOCK"]

    # Test scoring with Isolation Forest Anomaly model
    if_out = asyncio.run(
        engine.score_transaction(sample_features_df.iloc[[0]], model_type="isolation_forest")
    )
    assert 0.0 <= if_out["risk_score"] <= 100.0
    assert if_out["recommendation"] in ["ALLOW", "FLAG", "BLOCK"]


def test_classifier_wrapper_loading(tmp_path, sample_features_df):
    """
    Verifies the FraudXGBoostClassifier wrapper behaves correctly.
    """
    models_dir = str(tmp_path / "models")
    os.makedirs(models_dir, exist_ok=True)

    # Re-train simple model inside tmp_path
    train_data = []
    for i in range(50):
        train_data.append(
            {
                "amount": 100.0,
                "hour_of_day": 12,
                "day_of_week": 2,
                "user_velocity_5m": 1,
                "user_velocity_1h": 2,
                "amount_to_user_avg_ratio": 1.0,
                "ip_country_mismatch": 0,
                "merchant_category": "5411",
                "location_country": "US",
                "currency": "USD",
                "is_fraud": 0 if i < 48 else 1,
            }
        )
    pd.DataFrame(train_data).to_csv(str(tmp_path / "train.csv"), index=False)
    train_models(train_data_path=str(tmp_path / "train.csv"), output_dir=models_dir)

    clf = FraudXGBoostClassifier()
    clf.load(model_dir=models_dir)
    probs = clf.predict_probability(sample_features_df)

    assert len(probs) == len(sample_features_df)
    assert np.all((probs >= 0.0) & (probs <= 1.0))
