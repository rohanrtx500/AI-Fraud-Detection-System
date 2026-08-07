import json
import os

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """
    Profile representing learned normal user transactional behavior baseline parameters.
    """

    sender_id: str = Field(..., description="Unique user ID")
    avg_amount: float = Field(0.0, description="Average spend size")
    std_amount: float = Field(0.0, description="Spending standard deviation deviation")
    preferred_countries: list[str] = Field(
        default_factory=list, description="List of preferred country locations"
    )
    preferred_cities: list[str] = Field(
        default_factory=list, description="List of preferred city locations"
    )
    preferred_devices: list[str] = Field(
        default_factory=list, description="List of used hardware devices"
    )
    typical_hours: list[int] = Field(
        default_factory=list, description="Typical transaction hours of day"
    )
    avg_inter_time_seconds: float = Field(0.0, description="Average time gap between transactions")
    last_tx_timestamp: str | None = Field(None, description="ISO timestamp of last transaction")


def fit_user_profiles(df: pd.DataFrame) -> dict[str, UserProfile]:
    """
    Fits baseline behavioral profiles for all users present in the training set.
    """
    print("Fitting user behavioral profiles from historical dataset...")
    df_sorted = df.copy()
    df_sorted["datetime"] = pd.to_datetime(df_sorted["timestamp"])
    df_sorted = df_sorted.sort_values("datetime")

    profiles: dict[str, UserProfile] = {}

    for sender_id, group in df_sorted.groupby("sender_id"):
        sender_str = str(sender_id)

        # Spend metrics
        avg_amt = float(group["amount"].mean())
        std_amt = float(group["amount"].std())
        if np.isnan(std_amt):
            std_amt = 0.0

        # Locations
        countries = group["location_country"].dropna().unique().tolist()
        cities = group["location_city"].dropna().unique().tolist()

        # Hardware Devices
        devices = group["device_id"].dropna().unique().tolist()

        # Temporal patterns (unseen hours)
        hours = group["datetime"].dt.hour.dropna().unique().tolist()

        # Frequency calculations
        times = group["datetime"].sort_values()
        diffs = times.diff().dropna().dt.total_seconds()
        avg_inter = float(diffs.mean()) if not diffs.empty else 0.0
        last_ts = times.iloc[-1].isoformat() if not times.empty else None

        profiles[sender_str] = UserProfile(
            sender_id=sender_str,
            avg_amount=avg_amt,
            std_amount=std_amt,
            preferred_countries=countries,
            preferred_cities=cities,
            preferred_devices=devices,
            typical_hours=hours,
            avg_inter_time_seconds=avg_inter,
            last_tx_timestamp=last_ts,
        )

    print(f"Learned profiles for {len(profiles)} unique users.")
    return profiles


def save_profile(
    sender_id: str, profile: UserProfile, directory: str = "models/registry/user_profiles"
) -> None:
    """
    Serializes a user profile to disk in JSON format.
    """
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, f"{sender_id}.json")
    with open(path, "w") as f:
        f.write(profile.model_dump_json(indent=4))


def load_profile(
    sender_id: str, directory: str = "models/registry/user_profiles"
) -> UserProfile | None:
    """
    Deserializes a user profile from disk JSON files.
    """
    path = os.path.join(directory, f"{sender_id}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            data = json.load(f)
            return UserProfile(**data)
    except Exception:
        return None


def calculate_behavioral_deviations(tx_payload: dict, profile: UserProfile) -> dict:
    """
    Compares an incoming transaction against the user profile.
    Flags anomalies in Amount, Location country/city, Device, Time-of-day, and Frequency.
    """
    amount = float(tx_payload.get("amount", 0.0))
    country = str(tx_payload.get("location_country"))
    city = str(tx_payload.get("location_city"))
    device = str(tx_payload.get("device_id"))
    timestamp_str = str(tx_payload.get("timestamp"))

    # 1. Amount Z-score deviation
    if profile.std_amount > 0:
        z_score = abs(amount - profile.avg_amount) / profile.std_amount
    else:
        # Fallback ratio variation if std is zero
        z_score = abs(amount - profile.avg_amount) / (profile.avg_amount + 1e-5)

    # 2. Location mismatches
    country_deviation = 1 if country not in profile.preferred_countries else 0
    city_deviation = 1 if city not in profile.preferred_cities else 0

    # 3. Hardware device mismatch
    device_deviation = 1 if device not in profile.preferred_devices else 0

    # 4. Time of day atypical hour check
    tx_datetime = pd.to_datetime(timestamp_str)
    tx_hour = tx_datetime.hour
    time_deviation = 1 if tx_hour not in profile.typical_hours else 0

    # 5. Frequency velocity check (time since last purchase)
    frequency_deviation = 0
    time_diff = None
    if profile.last_tx_timestamp:
        try:
            last_dt = pd.to_datetime(profile.last_tx_timestamp)
            # Ensure timezone compatibility
            if last_dt.tzinfo is not None and tx_datetime.tzinfo is None:
                tx_datetime = tx_datetime.tz_localize(last_dt.tzinfo)
            time_diff = (tx_datetime - last_dt).total_seconds()

            # If current purchase gap is abnormally small (< 1% of mean gap)
            if profile.avg_inter_time_seconds > 0 and time_diff > 0:
                if time_diff < 0.01 * profile.avg_inter_time_seconds:
                    frequency_deviation = 1
        except Exception:
            pass

    return {
        "amount_z_score": round(float(z_score), 4),
        "location_country_deviation": country_deviation,
        "location_city_deviation": city_deviation,
        "device_deviation": device_deviation,
        "time_deviation": time_deviation,
        "frequency_deviation": frequency_deviation,
        "time_since_last_tx_seconds": round(float(time_diff), 2) if time_diff is not None else None,
    }


if __name__ == "__main__":
    # Test profile fit CLI script
    print("=" * 60)
    print("TESTING USER BEHAVIORAL PROFILING ENGINE")
    print("=" * 60)

    # Read raw transactions dataset
    raw_path = "data/raw/transactions_raw.csv"
    if os.path.exists(raw_path):
        df = pd.read_csv(raw_path)
        profiles = fit_user_profiles(df)

        # Save profiles for first 5 users
        for i, (usr_id, prof) in enumerate(profiles.items()):
            if i >= 5:
                break
            save_profile(usr_id, prof)
            print(f"Saved profile for {usr_id} with avg spend ${prof.avg_amount:.2f}")
    else:
        print("Raw dataset transactions_raw.csv not found to test fit.")
    print("=" * 60)
