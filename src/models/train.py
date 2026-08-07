import os

import joblib
import pandas as pd
import xgboost as xgb
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.features.definitions import (
    ENGINEERED_CATEGORICAL_FEATURES,
    ENGINEERED_NUMERICAL_FEATURES,
    RAW_NUMERICAL_FEATURES,
    TARGET_COLUMN,
)


def build_preprocessor() -> ColumnTransformer:
    """
    Constructs a ColumnTransformer to handle categorical and numerical features.
    - Categoricals: OneHotEncoder (handling unseen values gracefully)
    - Numericals: StandardScaler
    """
    numerical_cols = RAW_NUMERICAL_FEATURES + ENGINEERED_NUMERICAL_FEATURES
    categorical_cols = ENGINEERED_CATEGORICAL_FEATURES

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numerical_cols),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_cols),
        ],
        remainder="drop",
    )
    return preprocessor


def train_models(
    train_data_path: str = "data/processed/v1.0.0/train.csv", output_dir: str = "models/registry"
):
    """
    Loads train dataset, constructs preprocessing pipelines, fits models
    (XGBoost, Random Forest, Isolation Forest), and serializes artifacts.
    """
    print(f"Loading training data from {train_data_path}...")
    if not os.path.exists(train_data_path):
        raise FileNotFoundError(f"Processed training file not found at: {train_data_path}")

    train_df = pd.read_csv(train_data_path)

    X_train = train_df.drop(columns=[TARGET_COLUMN])
    y_train = train_df[TARGET_COLUMN]

    # Calculate pos class weights to account for fraud imbalance
    num_neg = (y_train == 0).sum()
    num_pos = (y_train == 1).sum()
    scale_pos_weight = num_neg / (num_pos + 1e-5)
    contamination = num_pos / len(y_train)

    print(f"Class distribution: Normal={num_neg}, Fraud={num_pos} (Fraud Rate={contamination:.4%})")

    # Create the base feature engineering transformer
    preprocessor = build_preprocessor()

    # 1. XGBoost Pipeline
    print("Training XGBoost Classifier...")
    xgb_clf = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        eval_metric="logloss",
    )
    xgb_pipeline = Pipeline(steps=[("preprocessor", preprocessor), ("classifier", xgb_clf)])
    xgb_pipeline.fit(X_train, y_train)

    # 2. Random Forest Pipeline
    print("Training Random Forest Classifier...")
    rf_clf = RandomForestClassifier(
        n_estimators=100, max_depth=10, class_weight="balanced", random_state=42, n_jobs=-1
    )
    rf_pipeline = Pipeline(steps=[("preprocessor", preprocessor), ("classifier", rf_clf)])
    rf_pipeline.fit(X_train, y_train)

    # 3. Isolation Forest Pipeline (Unsupervised anomaly detection)
    print("Training Isolation Forest Anomaly Detector...")
    # Isolation forest is fit on the preprocessed feature matrix, without target labels
    preprocessor_if = build_preprocessor()
    X_train_preprocessed = preprocessor_if.fit_transform(X_train)

    if_clf = IsolationForest(
        n_estimators=150, contamination=contamination, random_state=42, n_jobs=-1
    )
    if_clf.fit(X_train_preprocessed)

    # We serialize preprocessor and isolation forest separately or as a custom wrapper pipeline
    # For ease of use, we package them as a combined pipeline object by wrapping the estimator
    if_pipeline = Pipeline(steps=[("preprocessor", preprocessor_if), ("classifier", if_clf)])

    # Ensure registry directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Save Pipeline models
    xgb_path = os.path.join(output_dir, "xgboost_pipeline.joblib")
    rf_path = os.path.join(output_dir, "random_forest_pipeline.joblib")
    if_path = os.path.join(output_dir, "isolation_forest_pipeline.joblib")

    joblib.dump(xgb_pipeline, xgb_path)
    joblib.dump(rf_pipeline, rf_path)
    joblib.dump(if_pipeline, if_path)

    print("=" * 60)
    print("MODEL TRAINING AND PERSISTENCE COMPLETED SUCCESSFULLY")
    print(f"XGBoost pipeline saved to: {xgb_path}")
    print(f"Random Forest pipeline saved to: {rf_path}")
    print(f"Isolation Forest pipeline saved to: {if_path}")
    print("=" * 60)


if __name__ == "__main__":
    train_models()
