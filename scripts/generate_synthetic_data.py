import os
import random
import uuid
from datetime import datetime, timedelta

import pandas as pd


def generate_synthetic_data(num_users: int = 1000, num_records: int = 20000) -> pd.DataFrame:
    """
    Generates realistic financial transaction history with injected fraud patterns.
    Fraud patterns:
    1. Large transaction amounts (highly anomalous for a user profile)
    2. Short-window velocity (multiple transactions by same sender in under 5 minutes)
    3. Location mismatch (IP address country doesn't match billing country)
    """
    print(f"Generating synthetic transaction logs for {num_users} users ({num_records} records)...")

    # Pre-define some profiles for users
    user_profiles = {}
    countries = ["US", "CA", "GB", "DE", "FR", "AU", "JP"]
    currencies = {
        "US": "USD",
        "CA": "CAD",
        "GB": "GBP",
        "DE": "EUR",
        "FR": "EUR",
        "AU": "AUD",
        "JP": "JPY",
    }
    merchants = {
        "5411": "Groceries",
        "5812": "Restaurants",
        "5732": "Electronics",
        "5944": "Jewelry",
        "4829": "Wire Transfers",
        "7995": "Betting/Casino",
    }

    for i in range(num_users):
        u_id = f"usr_{100000 + i}"
        home_country = random.choice(countries)
        user_profiles[u_id] = {
            "home_country": home_country,
            "currency": currencies[home_country],
            "avg_spend": random.uniform(10.0, 150.0),
            "device_id": f"dev_{uuid.uuid4().hex[:12]}",
            "last_tx_time": datetime.utcnow() - timedelta(days=30),
            "billing_city": f"City_{random.randint(1, 20)}",
        }

    records = []
    base_time = datetime.utcnow() - timedelta(days=30)

    # Generate sequential transactions to simulate timeline (needed for rolling metrics)
    time_increments = [random.randint(10, 180) for _ in range(num_records)]
    current_time = base_time

    # Track recent transactions per user to simulate velocity
    user_recent_txs = {u_id: [] for u_id in user_profiles}

    for idx in range(num_records):
        current_time += timedelta(seconds=time_increments[idx])
        u_id = random.choice(list(user_profiles.keys()))
        profile = user_profiles[u_id]

        # Decide if this transaction is simulated fraud
        is_fraud = 0
        fraud_reason = None

        # Standard transaction baseline parameters
        amount = abs(random.normalvariate(profile["avg_spend"], profile["avg_spend"] * 0.3)) + 1.0
        currency = profile["currency"]
        country = profile["home_country"]
        city = profile["billing_city"]
        device = profile["device_id"]
        ip_country = country
        merchant_cat = random.choice(list(merchants.keys()))

        # Inject Fraud Pattern 1: High amount anomaly (value > 10x user average)
        if random.random() < 0.005:  # 0.5% chance to attempt amount fraud
            amount = profile["avg_spend"] * random.uniform(15.0, 30.0)
            merchant_cat = random.choice(["5944", "5732"])  # Jewelry or Electronics
            is_fraud = 1
            fraud_reason = "high_amount"

        # Inject Fraud Pattern 2: Short-window velocity
        # Check user's last transactions
        user_history = user_recent_txs[u_id]
        # Keep only last 10 minutes history
        user_history = [t for t in user_history if (current_time - t) < timedelta(minutes=10)]
        user_recent_txs[u_id] = user_history

        if len(user_history) >= 4 and random.random() < 0.6:  # High frequency
            is_fraud = 1
            fraud_reason = "velocity"
            amount = random.uniform(10.0, 100.0)
            merchant_cat = "4829"  # Wire Transfers

        # Inject Fraud Pattern 3: Country / Geolocation hop
        if random.random() < 0.004:
            ip_country = random.choice([c for c in countries if c != country])
            is_fraud = 1
            fraud_reason = "geo_hop"
            merchant_cat = "7995"  # Casino

        # Normal random variance (1% random background noise fraud)
        if is_fraud == 0 and random.random() < 0.008:
            is_fraud = 1
            fraud_reason = "stealth"

        # Setup IP addresses
        if ip_country == country:
            ip_address = f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}"
        else:
            ip_address = f"{random.randint(10, 220)}.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"

        # Track transaction time
        user_recent_txs[u_id].append(current_time)

        # Output payload mapping
        records.append(
            {
                "transaction_id": str(uuid.uuid4()),
                "sender_id": u_id,
                "receiver_id": f"merch_{random.randint(10000, 99999)}",
                "amount": round(amount, 2),
                "currency": currency,
                "merchant_category": merchant_cat,
                "location_country": ip_country,
                "location_city": (
                    city if ip_country == country else f"ForeignCity_{random.randint(1, 10)}"
                ),
                "device_id": (
                    device if fraud_reason != "geo_hop" else f"dev_{uuid.uuid4().hex[:12]}"
                ),
                "ip_address": ip_address,
                "timestamp": current_time.isoformat(),
                "is_fraud": is_fraud,
            }
        )

    df = pd.DataFrame(records)
    print(f"Generation complete. Data shape: {df.shape}")
    print(f"Fraud distribution:\n{df['is_fraud'].value_counts(normalize=True) * 100}")

    return df


if __name__ == "__main__":
    # Ensure data directory exists
    os.makedirs("data/raw", exist_ok=True)

    raw_df = generate_synthetic_data()
    output_path = "data/raw/transactions_raw.csv"
    raw_df.to_csv(output_path, index=False)
    print(f"Raw dataset successfully saved to: {output_path}")
