import math
import random
import uuid
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.crud import create_risk_assessment, create_transaction
from src.database.models import Case

# Static global dictionary of cities across the world with geographical coordinates
CITIES = {
    "New York": {
        "country": "US",
        "lat": 40.7128,
        "lon": -74.0060,
        "ip_prefixes": ["104.244", "198.51"],
    },
    "Los Angeles": {
        "country": "US",
        "lat": 34.0522,
        "lon": -118.2437,
        "ip_prefixes": ["104.244", "198.51"],
    },
    "Chicago": {
        "country": "US",
        "lat": 41.8781,
        "lon": -87.6298,
        "ip_prefixes": ["104.244", "198.51"],
    },
    "London": {
        "country": "GB",
        "lat": 51.5074,
        "lon": -0.1278,
        "ip_prefixes": ["82.165", "195.171"],
    },
    "Paris": {"country": "FR", "lat": 48.8566, "lon": 2.3522, "ip_prefixes": ["90.84", "194.254"]},
    "Moscow": {
        "country": "RU",
        "lat": 55.7558,
        "lon": 37.6173,
        "ip_prefixes": ["95.105", "185.220"],
    },
    "Tokyo": {
        "country": "JP",
        "lat": 35.6762,
        "lon": 139.6503,
        "ip_prefixes": ["122.211", "210.140"],
    },
    "Sydney": {
        "country": "AU",
        "lat": -33.8688,
        "lon": 151.2093,
        "ip_prefixes": ["120.146", "203.26"],
    },
    "Toronto": {
        "country": "CA",
        "lat": 43.6532,
        "lon": -79.3832,
        "ip_prefixes": ["198.100", "204.101"],
    },
    "Mumbai": {
        "country": "IN",
        "lat": 19.0760,
        "lon": 72.8777,
        "ip_prefixes": ["103.206", "115.112"],
    },
}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes the geographical distance between two points using the Haversine formula (in km).
    """
    R = 6371.0  # Radius of the earth in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


class SyntheticFraudEngine:
    """
    High-fidelity Synthetic Fraud Scenario Generator Engine.
    Generates baseline benign activity and realistic scenarios for card testing,
    account takeovers, velocity spikes, device spoofing, geographical travels, and merchant abuse.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)
        np.random.seed(seed)
        self.user_profiles = {}
        self.device_pool = [f"dev_{uuid.uuid4().hex[:12]}" for _ in range(100)]
        self.merchant_pool = [f"merch_{random.randint(10000, 99999)}" for _ in range(50)]

    def generate_user_profiles(self, num_users: int = 50) -> dict:
        """
        Builds static profile properties for synthetic cardholders/users.
        """
        city_names = list(CITIES.keys())
        for i in range(num_users):
            user_id = f"usr_{100000 + i}"
            home_city = random.choice(city_names)
            home_country = CITIES[home_city]["country"]
            ip_pref = random.choice(CITIES[home_city]["ip_prefixes"])

            # Personal profile baselines
            common_devices = [random.choice(self.device_pool) for _ in range(random.choice([1, 2]))]
            common_ips = [
                f"{ip_pref}.{random.randint(1, 254)}.{random.randint(1, 254)}"
                for _ in range(random.choice([1, 2]))
            ]
            mean_amount = random.uniform(15.0, 120.0)

            self.user_profiles[user_id] = {
                "user_id": user_id,
                "home_city": home_city,
                "home_country": home_country,
                "common_devices": common_devices,
                "common_ips": common_ips,
                "mean_amount": mean_amount,
                "typical_mccs": random.sample(
                    ["5411", "5812", "5814", "5912", "5311", "4812"], k=3
                ),
                "currency": (
                    "USD"
                    if home_country == "US"
                    else (
                        "CAD"
                        if home_country == "CA"
                        else ("EUR" if home_country in ["FR", "GB"] else "USD")
                    )
                ),
            }
        return self.user_profiles

    def _generate_ip_for_city(self, city_name: str) -> str:
        prefixes = CITIES[city_name]["ip_prefixes"]
        return f"{random.choice(prefixes)}.{random.randint(1, 254)}.{random.randint(1, 254)}"

    def _get_or_create_profile(self, user_id: str) -> dict:
        if user_id not in self.user_profiles:
            # Dynamically generate a profile for this user ID
            city_names = list(CITIES.keys())
            home_city = random.choice(city_names)
            home_country = CITIES[home_city]["country"]
            ip_pref = random.choice(CITIES[home_city]["ip_prefixes"])
            common_devices = [random.choice(self.device_pool) for _ in range(random.choice([1, 2]))]
            common_ips = [
                f"{ip_pref}.{random.randint(1, 254)}.{random.randint(1, 254)}"
                for _ in range(random.choice([1, 2]))
            ]
            mean_amount = random.uniform(15.0, 120.0)

            self.user_profiles[user_id] = {
                "user_id": user_id,
                "home_city": home_city,
                "home_country": home_country,
                "common_devices": common_devices,
                "common_ips": common_ips,
                "mean_amount": mean_amount,
                "typical_mccs": random.sample(
                    ["5411", "5812", "5814", "5912", "5311", "4812"], k=3
                ),
                "currency": (
                    "USD"
                    if home_country == "US"
                    else (
                        "CAD"
                        if home_country == "CA"
                        else ("EUR" if home_country in ["FR", "GB"] else "USD")
                    )
                ),
            }
        return self.user_profiles[user_id]

    def generate_benign_transaction(self, user_id: str, timestamp: datetime) -> dict:
        """
        Simulates standard transactional habits for a given user profile.
        """
        profile = self._get_or_create_profile(user_id)

        # Log-normal distribution to guarantee realistic amount spreads
        amount = float(np.random.lognormal(mean=math.log(profile["mean_amount"]), sigma=0.4))
        amount = round(max(1.0, amount), 2)

        return {
            "transaction_id": str(uuid.uuid4()),
            "sender_id": user_id,
            "receiver_id": random.choice(self.merchant_pool),
            "amount": amount,
            "currency": profile["currency"],
            "merchant_category": random.choice(profile["typical_mccs"]),
            "location_country": profile["home_country"],
            "location_city": profile["home_city"],
            "device_id": random.choice(profile["common_devices"]),
            "ip_address": random.choice(profile["common_ips"]),
            "timestamp": timestamp,
            "is_fraud": 0,
            "scenario_type": "normal",
        }

    def generate_account_takeover(self, user_id: str, start_time: datetime) -> list[dict]:
        """
        Scenario: Account Takeover (ATO).
        User performs some normal transactions, then a sudden shift in device/IP location
        occurs followed by a rapid burst of high-value luxury purchases.
        """
        profile = self._get_or_create_profile(user_id)
        events = []

        # 1. 2 Benign Transactions
        curr_time = start_time
        for _ in range(2):
            events.append(self.generate_benign_transaction(user_id, curr_time))
            curr_time += timedelta(hours=random.randint(12, 24))

        # 2. Fraud takeover transactions
        curr_time += timedelta(hours=2)  # takeover delay
        new_device = f"dev_{uuid.uuid4().hex[:12]}"

        # Takeover comes from an overseas city (e.g. Moscow if user is from US, Tokyo if from GB)
        remote_city = "Moscow" if profile["home_country"] != "RU" else "Tokyo"
        remote_country = CITIES[remote_city]["country"]
        remote_ip = self._generate_ip_for_city(remote_city)

        for i in range(3):
            # High-end categories: 5944 (Jewelry), 5732 (Electronics)
            mcc = "5944" if i % 2 == 0 else "5732"
            amount = round(profile["mean_amount"] * random.uniform(6.0, 12.0), 2)
            events.append(
                {
                    "transaction_id": str(uuid.uuid4()),
                    "sender_id": user_id,
                    "receiver_id": random.choice(self.merchant_pool),
                    "amount": amount,
                    "currency": "USD",
                    "merchant_category": mcc,
                    "location_country": remote_country,
                    "location_city": remote_city,
                    "device_id": new_device,
                    "ip_address": remote_ip,
                    "timestamp": curr_time,
                    "is_fraud": 1,
                    "scenario_type": "account_takeover",
                }
            )
            curr_time += timedelta(minutes=random.randint(5, 15))

        return events

    def generate_card_testing(self, user_id: str, start_time: datetime) -> list[dict]:
        """
        Scenario: Card Testing.
        Sequence of micro-value transactions (e.g. $0.50 - $2.00) at low-friction online merchants,
        instantly followed by a massive transaction once validity is established.
        """
        events = []
        curr_time = start_time

        # Rapid successive digital MCC checks: 4814 (Telecom), 5968 (Sub)
        for _ in range(4):
            events.append(
                {
                    "transaction_id": str(uuid.uuid4()),
                    "sender_id": user_id,
                    "receiver_id": f"merch_digital_{random.randint(100, 999)}",
                    "amount": round(random.uniform(0.15, 2.50), 2),
                    "currency": "USD",
                    "merchant_category": "5968",
                    "location_country": "US",
                    "location_city": "New York",
                    "device_id": f"dev_digital_{uuid.uuid4().hex[:6]}",
                    "ip_address": "198.51.100.44",
                    "timestamp": curr_time,
                    "is_fraud": 1,
                    "scenario_type": "card_testing",
                }
            )
            curr_time += timedelta(seconds=random.randint(15, 45))

        # Target payout transaction
        events.append(
            {
                "transaction_id": str(uuid.uuid4()),
                "sender_id": user_id,
                "receiver_id": random.choice(self.merchant_pool),
                "amount": round(random.uniform(850.00, 1900.00), 2),
                "currency": "USD",
                "merchant_category": "5732",  # Electronics
                "location_country": "US",
                "location_city": "New York",
                "device_id": events[-1]["device_id"],
                "ip_address": events[-1]["ip_address"],
                "timestamp": curr_time + timedelta(seconds=10),
                "is_fraud": 1,
                "scenario_type": "card_testing",
            }
        )
        return events

    def generate_velocity_attack(self, user_id: str, start_time: datetime) -> list[dict]:
        """
        Scenario: Transaction Velocity Attack.
        A single card is hit with a rapid succession of swipes (e.g. 8 swipes in 2 minutes)
        at the same physical merchant category, depleting limits.
        """
        events = []
        curr_time = start_time
        target_merchant = random.choice(self.merchant_pool)

        for _ in range(8):
            events.append(
                {
                    "transaction_id": str(uuid.uuid4()),
                    "sender_id": user_id,
                    "receiver_id": target_merchant,
                    "amount": round(random.uniform(75.0, 110.0), 2),
                    "currency": "USD",
                    "merchant_category": "5411",  # Grocery/Supermarket
                    "location_country": "US",
                    "location_city": "Los Angeles",
                    "device_id": "dev_velocity_pos_terminal",
                    "ip_address": "104.244.20.12",
                    "timestamp": curr_time,
                    "is_fraud": 1,
                    "scenario_type": "velocity_attack",
                }
            )
            curr_time += timedelta(seconds=random.randint(5, 20))

        return events

    def generate_device_spoofing(self, start_time: datetime) -> list[dict]:
        """
        Scenario: Device Spoofing (Emulator / Click-Farm).
        A single device fingerprint is utilized to authenticate transactions for 8 different
        user card numbers within a compressed time frame.
        """
        events = []
        shared_device = f"dev_emul_{uuid.uuid4().hex[:8]}"
        curr_time = start_time

        for i in range(8):
            fake_user = f"usr_spoof_{100 + i}"
            events.append(
                {
                    "transaction_id": str(uuid.uuid4()),
                    "sender_id": fake_user,
                    "receiver_id": random.choice(self.merchant_pool),
                    "amount": round(random.uniform(40.00, 250.00), 2),
                    "currency": "USD",
                    "merchant_category": "5812",  # Dining
                    "location_country": "US",
                    "location_city": "Chicago",
                    "device_id": shared_device,
                    "ip_address": "198.51.100.80",
                    "timestamp": curr_time,
                    "is_fraud": 1,
                    "scenario_type": "device_spoofing",
                }
            )
            curr_time += timedelta(minutes=random.randint(1, 3))

        return events

    def generate_location_anomaly(self, user_id: str, start_time: datetime) -> list[dict]:
        """
        Scenario: Location Anomaly (Impossible Travel).
        A user has a transaction in New York, and 15 minutes later has a transaction in London.
        Geographical velocity calculation indicates speed far exceeding supersonic physical travel.
        """
        profile = self._get_or_create_profile(user_id)
        events = []

        # Transaction 1: Normal home city New York
        t1 = start_time
        events.append(
            {
                "transaction_id": str(uuid.uuid4()),
                "sender_id": user_id,
                "receiver_id": random.choice(self.merchant_pool),
                "amount": round(profile["mean_amount"], 2),
                "currency": profile["currency"],
                "merchant_category": random.choice(profile["typical_mccs"]),
                "location_country": "US",
                "location_city": "New York",
                "device_id": profile["common_devices"][0],
                "ip_address": profile["common_ips"][0],
                "timestamp": t1,
                "is_fraud": 0,
                "scenario_type": "impossible_travel",
            }
        )

        # Transaction 2: Impossible travel to London 15 minutes later
        t2 = t1 + timedelta(minutes=15)
        events.append(
            {
                "transaction_id": str(uuid.uuid4()),
                "sender_id": user_id,
                "receiver_id": random.choice(self.merchant_pool),
                "amount": round(profile["mean_amount"] * 1.5, 2),
                "currency": "USD",
                "merchant_category": "5812",
                "location_country": "GB",
                "location_city": "London",
                "device_id": f"dev_london_{uuid.uuid4().hex[:6]}",
                "ip_address": "82.165.40.12",
                "timestamp": t2,
                "is_fraud": 1,
                "scenario_type": "impossible_travel",
            }
        )

        return events

    def generate_merchant_abuse(self, start_time: datetime) -> list[dict]:
        """
        Scenario: Merchant Promo/Refund Abuse.
        A single high-risk merchant receiver is hit with multiple rapid transactions
        and refunds (negative amounts) from different fake accounts.
        """
        events = []
        target_merchant = f"merch_abuse_target_{random.randint(10, 99)}"
        curr_time = start_time

        for i in range(12):
            fake_user = f"usr_abuse_{200 + (i // 2)}"
            # Alternate positive charging and negative refund claims
            if i % 3 == 0:
                amount = -round(random.uniform(50.00, 150.00), 2)  # Refund abuse
                mcc = "5968"
            else:
                amount = round(random.uniform(100.00, 300.00), 2)
                mcc = "5311"  # Department store

            events.append(
                {
                    "transaction_id": str(uuid.uuid4()),
                    "sender_id": fake_user,
                    "receiver_id": target_merchant,
                    "amount": amount,
                    "currency": "USD",
                    "merchant_category": mcc,
                    "location_country": "US",
                    "location_city": "Chicago",
                    "device_id": f"dev_abuse_{uuid.uuid4().hex[:6]}",
                    "ip_address": f"198.51.10.{(i * 10) % 250 + 1}",
                    "timestamp": curr_time,
                    "is_fraud": 1,
                    "scenario_type": "merchant_abuse",
                }
            )
            curr_time += timedelta(minutes=random.randint(1, 4))

        return events

    def build_dataset(
        self,
        num_normal: int = 1000,
        num_ato: int = 5,
        num_card_testing: int = 5,
        num_velocity: int = 5,
        num_device_spoofing: int = 5,
        num_location_anomaly: int = 5,
        num_merchant_abuse: int = 5,
    ) -> pd.DataFrame:
        """
        Assembles all baseline benign and fraud scenarios into a unified, sorted dataset.
        """
        self.generate_user_profiles(num_users=60)
        user_ids = list(self.user_profiles.keys())
        all_transactions = []

        base_start = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=30)

        # 1. Generate normal transactions
        for _ in range(num_normal):
            user = random.choice(user_ids)
            time_offset = base_start + timedelta(
                minutes=random.randint(0, 43200)  # spread over 30 days
            )
            tx = self.generate_benign_transaction(user, time_offset)
            all_transactions.append(tx)

        # 2. Inject Account Takeovers
        for _ in range(num_ato):
            user = random.choice(user_ids)
            time_offset = base_start + timedelta(minutes=random.randint(0, 40000))
            all_transactions.extend(self.generate_account_takeover(user, time_offset))

        # 3. Inject Card Testing
        for _ in range(num_card_testing):
            user = random.choice(user_ids)
            time_offset = base_start + timedelta(minutes=random.randint(0, 40000))
            all_transactions.extend(self.generate_card_testing(user, time_offset))

        # 4. Inject Velocity Attacks
        for _ in range(num_velocity):
            user = random.choice(user_ids)
            time_offset = base_start + timedelta(minutes=random.randint(0, 40000))
            all_transactions.extend(self.generate_velocity_attack(user, time_offset))

        # 5. Inject Device Spoofing
        for _ in range(num_device_spoofing):
            time_offset = base_start + timedelta(minutes=random.randint(0, 40000))
            all_transactions.extend(self.generate_device_spoofing(time_offset))

        # 6. Inject Location Anomalies
        for _ in range(num_location_anomaly):
            user = random.choice(user_ids)
            time_offset = base_start + timedelta(minutes=random.randint(0, 40000))
            all_transactions.extend(self.generate_location_anomaly(user, time_offset))

        # 7. Inject Merchant Abuse
        for _ in range(num_merchant_abuse):
            time_offset = base_start + timedelta(minutes=random.randint(0, 40000))
            all_transactions.extend(self.generate_merchant_abuse(time_offset))

        # Sort dataset chronologically
        df = pd.DataFrame(all_transactions)
        df = df.sort_values(by="timestamp").reset_index(drop=True)
        return df

    async def seed_database(self, db: AsyncSession, df: pd.DataFrame) -> None:
        """
        Saves transaction objects and generates consistent RiskAssessments/Cases in the DB.
        """
        for _, row in df.iterrows():
            tx_data = {
                "transaction_id": row["transaction_id"],
                "sender_id": row["sender_id"],
                "receiver_id": row["receiver_id"],
                "amount": row["amount"],
                "currency": row["currency"],
                "merchant_category": row["merchant_category"],
                "location_country": row["location_country"],
                "location_city": row["location_city"],
                "device_id": row["device_id"],
                "ip_address": row["ip_address"],
                "timestamp": row["timestamp"],
            }
            # Insert Transaction
            tx = await create_transaction(db, tx_data)

            # Generate matched Risk Assessment outcomes
            is_fraud = row["is_fraud"]
            scenario = row["scenario_type"]

            if is_fraud:
                # Fraud: High scores
                risk_score = round(random.uniform(55.0, 99.0), 2)
                recommendation = "BLOCK" if risk_score >= 80.0 else "FLAG"
            else:
                # Benign: Low scores
                risk_score = round(random.uniform(0.1, 28.0), 2)
                recommendation = "ALLOW"

            shap_values = {
                "amount": 0.4 if row["amount"] > 500.0 else 0.0,
                "ip_country_mismatch": 0.35 if row["location_country"] != "US" else 0.0,
                "velocity_5m": 0.3 if scenario in ["velocity_attack", "card_testing"] else 0.0,
            }

            ra_data = {
                "assessment_id": str(uuid.uuid4()),
                "transaction_id": tx.transaction_id,
                "risk_score": risk_score,
                "recommendation": recommendation,
                "model_version": "xgboost-v1.0.0",
                "shap_values": shap_values,
                "assessed_at": row["timestamp"],
            }
            ra = await create_risk_assessment(db, ra_data)

            # If risk score triggers BLOCK or FLAG, simulate Case creation for high-fidelity database state
            if recommendation in ["BLOCK", "FLAG"] and random.random() < 0.65:
                # Open or investigate cases
                status = random.choice(["OPEN", "INVESTIGATING", "RESOLVED", "FALSE_POSITIVE"])
                priority = (
                    "CRITICAL"
                    if risk_score >= 90.0
                    else ("HIGH" if risk_score >= 75.0 else "MEDIUM")
                )

                case = Case(
                    case_id=str(uuid.uuid4()),
                    alert_id=ra.assessment_id,
                    analyst=(
                        random.choice(["analyst_rohan", "analyst_clara"])
                        if status != "OPEN"
                        else None
                    ),
                    priority=priority,
                    status=status,
                    created_at=ra.assessed_at,
                    resolved_at=(
                        ra.assessed_at + timedelta(hours=random.randint(1, 48))
                        if status in ["RESOLVED", "FALSE_POSITIVE"]
                        else None
                    ),
                )
                db.add(case)

        await db.commit()
