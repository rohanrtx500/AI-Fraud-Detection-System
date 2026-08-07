import os
from typing import Any

import joblib
import numpy as np
import pandas as pd

from src.models.base import BaseFraudModel


class FraudXGBoostClassifier(BaseFraudModel):
    """
    XGBoost classifier pipeline implementation.
    Wraps features scaling, categorical encoding, and classification booster.
    """

    def __init__(self):
        self.pipeline = None
        self.version = "xgboost-v1.0.0"

    def load(self, model_dir: str) -> None:
        """
        Loads the saved classifier pipeline from disk.
        """
        model_path = os.path.join(model_dir, "xgboost_pipeline.joblib")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"XGBoost pipeline model not found at: {model_path}")
        self.pipeline = joblib.load(model_path)

    def predict_probability(self, features: pd.DataFrame) -> np.ndarray:
        """
        Processes model inference. Returns array of fraud class probabilities.
        """
        if self.pipeline is None:
            raise RuntimeError("XGBoost pipeline model is not loaded. Call load() first.")
        return self.pipeline.predict_proba(features)[:, 1]

    def train(self, X: pd.DataFrame, y: pd.Series) -> dict[str, Any]:
        """
        Trains model pipeline and evaluates metrics.
        """
        import xgboost as xgb
        from sklearn.pipeline import Pipeline

        from src.models.train import build_preprocessor

        preprocessor = build_preprocessor()
        num_neg = (y == 0).sum()
        num_pos = (y == 1).sum()
        scale_pos_weight = num_neg / (num_pos + 1e-5)

        xgb_clf = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            scale_pos_weight=scale_pos_weight,
            random_state=42,
            eval_metric="logloss",
        )
        self.pipeline = Pipeline(steps=[("preprocessor", preprocessor), ("classifier", xgb_clf)])
        self.pipeline.fit(X, y)
        return {"status": "success", "model_version": self.version}
