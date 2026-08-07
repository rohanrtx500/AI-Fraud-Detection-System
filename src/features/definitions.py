# Feature engineering, validation, and pipeline definitions

# Raw transaction schema and data type mappings
RAW_SCHEMA = {
    "transaction_id": "string",
    "sender_id": "string",
    "receiver_id": "string",
    "amount": "float64",
    "currency": "string",
    "merchant_category": "string",
    "location_country": "string",
    "location_city": "string",
    "device_id": "string",
    "ip_address": "string",
    "timestamp": "string",
}

# Targets and unique identifiers
TARGET_COLUMN = "is_fraud"
ID_COLUMN = "transaction_id"

# Ingestion validation bounds
VALIDATION_RULES = {
    "amount_min": 0.01,
    "allowed_currencies": ["USD", "EUR", "GBP", "CAD", "AUD", "JPY"],
    "country_code_length": 2,
}

# Base raw numerical and categorical variables
RAW_NUMERICAL_FEATURES = ["amount"]
RAW_CATEGORICAL_FEATURES = ["currency", "merchant_category", "location_country"]

# Engineered features definitions
ENGINEERED_NUMERICAL_FEATURES = [
    "hour_of_day",
    "day_of_week",
    "user_velocity_5m",  # Count of user transactions in last 5 minutes
    "user_velocity_1h",  # Count of user transactions in last 1 hour
    "amount_to_user_avg_ratio",  # Ratio of current amount to user average transaction amount
    "ip_country_mismatch",  # Flag if IP country is different from home country
]

ENGINEERED_CATEGORICAL_FEATURES = [
    "merchant_category",
    "location_country",
    "currency",
]

# Final consolidated features fed into machine learning classifiers
FINAL_FEATURE_COLUMNS = (
    RAW_NUMERICAL_FEATURES + ENGINEERED_NUMERICAL_FEATURES + ENGINEERED_CATEGORICAL_FEATURES
)
