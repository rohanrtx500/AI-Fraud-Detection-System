import json
import os

import joblib
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from src.features.definitions import TARGET_COLUMN


def evaluate_models(
    test_data_path: str = "data/processed/v1.0.0/test.csv",
    models_dir: str = "models/registry",
    output_metrics_file: str = "evaluation_metrics.json",
):
    """
    Loads test data, retrieves trained pipeline models from models_dir,
    runs inferences, and logs comparative accuracy metrics (precision, recall, f1, AUC).
    """
    print(f"Loading testing dataset from {test_data_path}...")
    if not os.path.exists(test_data_path):
        raise FileNotFoundError(f"Processed test file not found at: {test_data_path}")

    test_df = pd.read_csv(test_data_path)
    X_test = test_df.drop(columns=[TARGET_COLUMN])
    y_test = test_df[TARGET_COLUMN]

    # Model paths
    xgb_path = os.path.join(models_dir, "xgboost_pipeline.joblib")
    rf_path = os.path.join(models_dir, "random_forest_pipeline.joblib")
    if_path = os.path.join(models_dir, "isolation_forest_pipeline.joblib")

    # Load pipelines
    print("Loading models from registry...")
    xgb_pipeline = joblib.load(xgb_path)
    rf_pipeline = joblib.load(rf_path)
    if_pipeline = joblib.load(if_path)

    metrics_report = {}

    # 1. Evaluate XGBoost
    print("Evaluating XGBoost model...")
    xgb_probs = xgb_pipeline.predict_proba(X_test)[:, 1]
    xgb_preds = xgb_pipeline.predict(X_test)
    metrics_report["xgboost"] = {
        "precision": float(precision_score(y_test, xgb_preds)),
        "recall": float(recall_score(y_test, xgb_preds)),
        "f1_score": float(f1_score(y_test, xgb_preds)),
        "roc_auc": float(roc_auc_score(y_test, xgb_probs)),
        "pr_auc": float(average_precision_score(y_test, xgb_probs)),
    }

    # 2. Evaluate Random Forest
    print("Evaluating Random Forest model...")
    rf_probs = rf_pipeline.predict_proba(X_test)[:, 1]
    rf_preds = rf_pipeline.predict(X_test)
    metrics_report["random_forest"] = {
        "precision": float(precision_score(y_test, rf_preds)),
        "recall": float(recall_score(y_test, rf_preds)),
        "f1_score": float(f1_score(y_test, rf_preds)),
        "roc_auc": float(roc_auc_score(y_test, rf_probs)),
        "pr_auc": float(average_precision_score(y_test, rf_probs)),
    }

    # 3. Evaluate Isolation Forest (Unsupervised)
    print("Evaluating Isolation Forest anomaly model...")
    # score_samples returns negative anomaly scores (lower is more anomalous)
    if_raw_scores = if_pipeline.score_samples(X_test)

    # Normalize to [0.0, 1.0] where higher is anomaly (fraud)
    min_score, max_score = if_raw_scores.min(), if_raw_scores.max()
    if max_score != min_score:
        if_probs = (max_score - if_raw_scores) / (max_score - min_score)
    else:
        if_probs = -if_raw_scores

    # predict() outputs -1 for anomaly and 1 for normal
    if_preds = (if_pipeline.predict(X_test) == -1).astype(int)

    metrics_report["isolation_forest"] = {
        "precision": float(precision_score(y_test, if_preds, zero_division=0)),
        "recall": float(recall_score(y_test, if_preds)),
        "f1_score": float(f1_score(y_test, if_preds, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, if_probs)),
        "pr_auc": float(average_precision_score(y_test, if_probs)),
    }

    # Print summary metrics to console
    print("\n" + "=" * 50)
    print("MODEL PERFORMANCE SUMMARY METRICS")
    print("=" * 50)
    for model_name, metrics in metrics_report.items():
        print(f"\n[{model_name.upper()}]")
        print(f"  ROC-AUC:   {metrics['roc_auc']:.4f}")
        print(f"  PR-AUC:    {metrics['pr_auc']:.4f}")
        print(f"  F1-Score:  {metrics['f1_score']:.4f}")
        print(f"  Precision: {metrics['precision']:.4f}")
        print(f"  Recall:    {metrics['recall']:.4f}")
    print("=" * 50 + "\n")

    # Export report
    output_path = os.path.join(models_dir, output_metrics_file)
    with open(output_path, "w") as f:
        json.dump(metrics_report, f, indent=4)

    print(f"Metrics successfully written to: {output_path}")
    return metrics_report


if __name__ == "__main__":
    evaluate_models()
