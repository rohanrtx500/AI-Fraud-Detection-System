import json
import os
from datetime import datetime

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split

from src.features.definitions import (
    FINAL_FEATURE_COLUMNS,
    RAW_SCHEMA,
    TARGET_COLUMN,
    VALIDATION_RULES,
)


def load_raw_dataset(file_path: str) -> pd.DataFrame:
    """
    Loads raw CSV dataset from local storage.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Raw data file not found at: {file_path}")

    print(f"Loading raw dataset from {file_path}...")
    df = pd.read_csv(file_path)
    return df


def validate_dataframe(df: pd.DataFrame) -> bool:
    """
    Validates structural schema and business bounds of raw transactional dataframe.
    Returns True if valid, raises ValueError otherwise.
    """
    print("Validating dataset schema and integrity constraints...")

    # 1. Check required columns exist
    missing_cols = [col for col in RAW_SCHEMA if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Schema validation failed: Missing columns: {missing_cols}")

    # 2. Check data type compatibility / casting
    for col, expected_type in RAW_SCHEMA.items():
        try:
            if expected_type == "float64":
                df[col] = df[col].astype(float)
            elif expected_type == "string":
                df[col] = df[col].astype(str)
        except Exception as e:
            raise ValueError(
                f"Schema validation failed: Cannot cast column {col} to {expected_type}. Error: {e}"
            ) from e

    # 3. Check values constraints
    if (df["amount"] < VALIDATION_RULES["amount_min"]).any():
        invalid_rows = df[df["amount"] < VALIDATION_RULES["amount_min"]]
        raise ValueError(
            f"Business validation failed: {len(invalid_rows)} transactions have amounts below "
            f"minimum threshold of ${VALIDATION_RULES['amount_min']}."
        )

    # Check country code constraint
    country_len_violations = df[
        df["location_country"].str.len() != VALIDATION_RULES["country_code_length"]
    ]
    if not country_len_violations.empty:
        raise ValueError(
            f"Business validation failed: {len(country_len_violations)} transactions "
            f"have invalid country code formats."
        )

    print("Dataframe validation passed successfully.")
    return True


def handle_missing_values(
    df: pd.DataFrame, is_training: bool = True, stats_dir: str = "models/registry"
) -> tuple[pd.DataFrame, dict]:
    """
    Imputes missing categorical and numerical parameters.
    Saves imputation rules (medians) during training to enforce consistent serving preprocessing.
    """
    print(f"Handling missing values (is_training={is_training})...")
    df_clean = df.copy()

    metadata_path = os.path.join(stats_dir, "preprocessing_metadata.joblib")

    if is_training:
        # Calculate medians for numerical columns
        medians = {}
        for col in ["amount"]:
            medians[col] = float(df_clean[col].median())

        # Standard fallback for categories
        category_modes = {}
        for col in ["currency", "merchant_category", "location_country"]:
            category_modes[col] = str(
                df_clean[col].mode()[0] if not df_clean[col].mode().empty else "UNKNOWN"
            )

        imputation_stats = {"medians": medians, "category_modes": category_modes}

        # Save fit metadata (will be expanded with home countries later)
        os.makedirs(stats_dir, exist_ok=True)
        joblib.dump(imputation_stats, metadata_path)
        print(f"Imputation metadata serialized to: {metadata_path}")
    else:
        # Serving mode: load pre-calculated stats
        if not os.path.exists(metadata_path):
            raise FileNotFoundError(
                f"Imputation statistics missing at {metadata_path}. Fit the pipeline first."
            )
        imputation_stats = joblib.load(metadata_path)
        medians = imputation_stats["medians"]
        category_modes = imputation_stats["category_modes"]

    # Apply imputation
    for col, val in medians.items():
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].fillna(val)

    for col, val in category_modes.items():
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].fillna(val)

    return df_clean, imputation_stats


def engineer_features(
    df: pd.DataFrame, is_training: bool = True, stats_dir: str = "models/registry"
) -> pd.DataFrame:
    """
    Extracts time properties, historical user averages, geographical hops, and rolling velocity counters.
    """
    print("Engineering transactional features...")
    df_feat = df.copy()

    # Ensure sorted order and index for time-series rolling calculations
    df_feat["datetime"] = pd.to_datetime(df_feat["timestamp"])
    df_feat = df_feat.sort_values("datetime")

    # Time indicators
    df_feat["hour_of_day"] = df_feat["datetime"].dt.hour
    df_feat["day_of_week"] = df_feat["datetime"].dt.dayofweek

    metadata_path = os.path.join(stats_dir, "preprocessing_metadata.joblib")

    if is_training:
        # 1. Infer user home countries based on most frequent location country
        user_home_countries = (
            df_feat.groupby("sender_id")["location_country"]
            .agg(lambda x: str(x.mode()[0] if not x.mode().empty else "US"))
            .to_dict()
        )

        # 2. Ingest user baseline spending averages
        user_avg_amounts = df_feat.groupby("sender_id")["amount"].mean().to_dict()

        # Update metadata storage
        imputation_stats = joblib.load(metadata_path) if os.path.exists(metadata_path) else {}
        imputation_stats["user_home_countries"] = user_home_countries
        imputation_stats["user_avg_amounts"] = user_avg_amounts
        joblib.dump(imputation_stats, metadata_path)
    else:
        if not os.path.exists(metadata_path):
            raise FileNotFoundError(f"Pipeline metadata missing at {metadata_path}")
        imputation_stats = joblib.load(metadata_path)
        user_home_countries = imputation_stats.get("user_home_countries", {})
        user_avg_amounts = imputation_stats.get("user_avg_amounts", {})

    # Compute IP location mismatches
    # Fallback to the country if user is unseen
    df_feat["home_country"] = (
        df_feat["sender_id"].map(user_home_countries).fillna(df_feat["location_country"])
    )
    df_feat["ip_country_mismatch"] = (
        df_feat["location_country"] != df_feat["home_country"]
    ).astype(int)

    # Compute spending ratio relative to user average
    # Fallback to amount (ratio = 1.0) if user average is unseen
    user_avg_map = df_feat["sender_id"].map(user_avg_amounts).fillna(df_feat["amount"])
    df_feat["amount_to_user_avg_ratio"] = df_feat["amount"] / (user_avg_map + 1e-5)

    # Compute User Velocities (Rolling transaction count lookback)
    # Using datetime index for rolling window
    df_feat = df_feat.set_index("datetime", drop=False)

    # 5-minute rolling velocity (closed='left' to exclude current transaction from prior count)
    df_feat["user_velocity_5m"] = (
        df_feat.groupby("sender_id")["amount"]
        .rolling("5min", closed="left")
        .count()
        .reset_index(level=0, drop=True)
        .fillna(0)
        .astype(int)
    )

    # 1-hour rolling velocity
    df_feat["user_velocity_1h"] = (
        df_feat.groupby("sender_id")["amount"]
        .rolling("1h", closed="left")
        .count()
        .reset_index(level=0, drop=True)
        .fillna(0)
        .astype(int)
    )

    df_feat = df_feat.reset_index(drop=True)
    return df_feat


def split_and_version_dataset(
    df: pd.DataFrame, version: str, output_dir: str = "data/processed"
) -> dict:
    """
    Splits processed features stratifiably into train/test CSV partitions.
    Saves output files to data/processed/{version}/ alongside a validation metadata log.
    """
    print(f"Splitting dataset and saving version {version}...")

    # Select only required model features + target label
    all_cols = FINAL_FEATURE_COLUMNS + ([TARGET_COLUMN] if TARGET_COLUMN in df.columns else [])
    df_model = df[all_cols].copy()

    # Stratified Train/Test split (80/20)
    train_df, test_df = train_test_split(
        df_model,
        test_size=0.20,
        stratify=df_model[TARGET_COLUMN] if TARGET_COLUMN in df_model.columns else None,
        random_state=42,
    )

    # Ensure output directory exists
    version_path = os.path.join(output_dir, version)
    os.makedirs(version_path, exist_ok=True)

    # Save to CSV files
    train_file = os.path.join(version_path, "train.csv")
    test_file = os.path.join(version_path, "test.csv")

    train_df.to_csv(train_file, index=False)
    test_df.to_csv(test_file, index=False)

    print(f"Train split saved to: {train_file}")
    print(f"Test split saved to: {test_file}")

    # Generate metadata manifest metrics
    fraud_rate_train = (
        float(train_df[TARGET_COLUMN].mean()) if TARGET_COLUMN in train_df.columns else 0.0
    )
    fraud_rate_test = (
        float(test_df[TARGET_COLUMN].mean()) if TARGET_COLUMN in test_df.columns else 0.0
    )

    metadata = {
        "version": version,
        "created_at": datetime.utcnow().isoformat(),
        "total_records": len(df_model),
        "train_records": len(train_df),
        "test_records": len(test_df),
        "fraud_rate_train": round(fraud_rate_train, 6),
        "fraud_rate_test": round(fraud_rate_test, 6),
        "feature_columns": FINAL_FEATURE_COLUMNS,
        "target_column": TARGET_COLUMN,
    }

    metadata_path = os.path.join(version_path, "metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=4)

    print(f"Dataset version manifest saved to: {metadata_path}")
    return metadata


def run_pipeline(raw_file_path: str, version: str) -> dict:
    """
    Orchestrates the entire ingestion, validation, preprocessing, and versioning flow.
    Fits and serializes user behavioral profiles during training.
    """
    print("=" * 60)
    print("STARTING DATA INGESTION AND PREPROCESSING PIPELINE")
    print("=" * 60)

    df_raw = load_raw_dataset(raw_file_path)
    validate_dataframe(df_raw)

    # Fit and save user behavioral profiles
    from src.features.profiling import fit_user_profiles, save_profile

    user_profiles = fit_user_profiles(df_raw)
    for u_id, profile in user_profiles.items():
        save_profile(u_id, profile)

    # Fit and save graph fraud detection model
    from src.features.graph_analysis import GraphFraudDetector

    graph_detector = GraphFraudDetector()
    graph_detector.build_graph(df_raw)
    graph_detector.save_graph("models/registry/graph_fraud_model.pkl")

    df_clean, _ = handle_missing_values(df_raw, is_training=True)
    df_features = engineer_features(df_clean, is_training=True)
    manifest = split_and_version_dataset(df_features, version=version)

    print("=" * 60)
    print("PIPELINE EXECUTION COMPLETED SUCCESSFULLY")
    print("=" * 60)
    return manifest


def preprocess_single_transaction(
    raw_data: dict, stats_dir: str = "models/registry"
) -> pd.DataFrame:
    """
    Transforms a single real-time transaction JSON payload into a 1-row DataFrame.
    Calculates derived metrics (velocity, spending ratio, location mismatch) using
    serialized training statistics.
    """
    # 1. Map JSON payload into 1-row DataFrame
    df = pd.DataFrame([raw_data])

    # Cast types matching raw schema
    df["amount"] = df["amount"].astype(float)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Extract temporal properties
    df["hour_of_day"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek

    # 2. Load pre-fit stats from model registry
    metadata_path = os.path.join(stats_dir, "preprocessing_metadata.joblib")
    if os.path.exists(metadata_path):
        stats = joblib.load(metadata_path)
        user_home_countries = stats.get("user_home_countries", {})
        user_avg_amounts = stats.get("user_avg_amounts", {})
    else:
        user_home_countries = {}
        user_avg_amounts = {}

    sender_id = raw_data.get("sender_id")
    location_country = raw_data.get("location_country")
    amount = float(raw_data.get("amount", 0.0))

    # 3. Compute location mismatch
    home_country = user_home_countries.get(sender_id, location_country)
    df["ip_country_mismatch"] = 1 if location_country != home_country else 0

    # 4. Compute spend ratio
    user_avg = user_avg_amounts.get(sender_id, amount)
    df["amount_to_user_avg_ratio"] = amount / (user_avg + 1e-5)

    # 5. Velocity lookups (defaults to 0 or utilizes mock overrides from client if testing)
    df["user_velocity_5m"] = int(raw_data.get("user_velocity_5m", 0))
    df["user_velocity_1h"] = int(raw_data.get("user_velocity_1h", 0))

    # Order columns matching definitions file expectation
    from src.features.definitions import FINAL_FEATURE_COLUMNS

    return df[FINAL_FEATURE_COLUMNS]


if __name__ == "__main__":
    # Test pipeline operation on default locations
    run_pipeline(raw_file_path="data/raw/transactions_raw.csv", version="v1.0.0")
