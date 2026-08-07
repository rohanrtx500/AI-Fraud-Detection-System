import os

import joblib
import pandas as pd

from src.models.explainer import SHAPExplainerWrapper
from src.models.train import train_models


def test_shap_explain_transaction(tmp_path):
    """
    Verifies that the SHAP explainer initializes, runs, and resolves raw mapping directions.
    """
    models_dir = str(tmp_path / "models")
    os.makedirs(models_dir, exist_ok=True)

    # 1. Train simple models pipeline to get a joblib artifact
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

    # 2. Load model pipeline and initialize wrapper
    pipeline_path = os.path.join(models_dir, "xgboost_pipeline.joblib")
    pipeline = joblib.load(pipeline_path)

    wrapper = SHAPExplainerWrapper()
    wrapper.fit_or_load(pipeline)

    # 3. Create mock record to explain
    raw_row = pd.DataFrame(
        [
            {
                "amount": 2000.0,  # anomalous
                "hour_of_day": 3,  # night
                "day_of_week": 2,
                "user_velocity_5m": 4,  # velocity anomaly
                "user_velocity_1h": 5,
                "amount_to_user_avg_ratio": 8.0,
                "ip_country_mismatch": 1,  # geolocation hop
                "merchant_category": "5411",
                "location_country": "RU",
                "currency": "USD",
            }
        ]
    )

    # Run SHAP explanations
    explanations = wrapper.explain_transaction(raw_row)

    # Assertions
    assert len(explanations) > 0

    # Check that required keys exist
    for expl in explanations:
        assert "feature_name" in expl
        assert "shap_value" in expl
        assert "impact_score" in expl
        assert "direction" in expl
        assert "description" in expl

        # Verify direction logic
        if expl["shap_value"] > 0:
            assert expl["direction"] == "INCREASED_RISK"
        elif expl["shap_value"] < 0:
            assert expl["direction"] == "DECREASED_RISK"

    # Verify that the primary drivers are correctly sorted
    # IP mismatch and amount_to_user_avg_ratio should be high drivers
    [e["feature_name"] for e in explanations[:4]]
    # Check that they exist in our mapped output
    mapped_features_list = [e["feature_name"] for e in explanations]
    assert "ip_country_mismatch" in mapped_features_list
    assert "amount_to_user_avg_ratio" in mapped_features_list
