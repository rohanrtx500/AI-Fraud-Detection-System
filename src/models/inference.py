import math
import os
from datetime import datetime

import joblib
import numpy as np
import pandas as pd

from src.models.explainer import SHAPExplainerWrapper
from src.models.scoring_engine import FraudRiskScoringEngine

CITY_COORDINATES = {
    "New York": (40.7128, -74.0060),
    "London": (51.5074, -0.1278),
    "Paris": (48.8566, 2.3522),
    "Tokyo": (35.6762, 139.6503),
    "Mumbai": (19.0760, 72.8777),
    "Singapore": (1.3521, 103.8198),
    "Sydney": (-33.8688, 151.2093),
    "San Francisco": (37.7749, -122.4194),
    "Chicago": (41.8781, -87.6298),
    "Berlin": (52.5200, 13.4050),
}

COUNTRY_COORDINATES = {
    "US": (37.0902, -95.7129),
    "GB": (55.3781, -3.4360),
    "FR": (46.2276, 2.2137),
    "JP": (36.2048, 138.2529),
    "IN": (20.5937, 78.9629),
    "SG": (1.3521, 103.8198),
    "AU": (-25.2744, 133.7751),
    "DE": (51.1657, 10.4515),
    "CA": (56.1304, -106.3468),
}


def haversine_distance(coord1: tuple[float, float], coord2: tuple[float, float]) -> float:
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    R = 6371.0  # Earth radius in kilometers

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def check_impossible_travel(prev_tx, current_tx_payload: dict) -> bool:
    prev_time = prev_tx.timestamp
    curr_time = current_tx_payload.get("timestamp")

    if isinstance(curr_time, str):
        try:
            curr_time = datetime.fromisoformat(curr_time.replace("Z", "+00:00")).replace(
                tzinfo=None
            )
        except ValueError:
            return False
    elif not isinstance(curr_time, datetime):
        return False

    time_delta = (curr_time - prev_time).total_seconds()
    if time_delta < 0:
        time_delta = abs(time_delta)

    # Same city/country
    prev_city = prev_tx.location_city
    prev_country = prev_tx.location_country
    curr_city = current_tx_payload.get("location_city")
    curr_country = current_tx_payload.get("location_country")

    if prev_city == curr_city and prev_country == curr_country:
        return False

    def get_coords(city, country):
        if city in CITY_COORDINATES:
            return CITY_COORDINATES[city]
        if country in COUNTRY_COORDINATES:
            return COUNTRY_COORDINATES[country]
        return (0.0, 0.0)

    prev_coords = get_coords(prev_city, prev_country)
    curr_coords = get_coords(curr_city, curr_country)

    if prev_coords == (0.0, 0.0) or curr_coords == (0.0, 0.0):
        if prev_country != curr_country:
            distance = 2000.0
        else:
            distance = 500.0
    else:
        distance = haversine_distance(prev_coords, curr_coords)

    if distance < 50.0:
        return False

    time_hours = max(time_delta, 1.0) / 3600.0
    speed = distance / time_hours

    # Cruising speed of commercial jet is ~900 km/h. threshold = 1000 km/h
    return speed > 1000.0


class FraudInferenceEngine:
    """
    Production scoring engine.
    Lazy loads model pipelines and uses the FraudRiskScoringEngine and SHAPExplainerWrapper
    to calculate calibrated risk scores, severity buckets, and reason codes.
    """

    def __init__(self, models_dir: str = "models/registry"):
        if not os.path.isabs(models_dir):
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            alt_path = os.path.join(base_dir, models_dir)
            if os.path.exists(alt_path):
                models_dir = alt_path
        self.models_dir = models_dir
        self.loaded_models: dict[str, joblib.Pipeline] = {}
        self.scoring_engine = FraudRiskScoringEngine()
        self.explainer = SHAPExplainerWrapper()

    def _get_model_pipeline(self, model_type: str):
        """
        Loads model pipeline from registry with memory caching.
        """
        if model_type not in self.loaded_models:
            filename = f"{model_type}_pipeline.joblib"
            model_path = os.path.join(self.models_dir, filename)

            if not os.path.exists(model_path):
                base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
                fallback_path = os.path.join(base_dir, "models", "registry", filename)
                if os.path.exists(fallback_path):
                    model_path = fallback_path
                else:
                    raise FileNotFoundError(f"Selected model '{model_type}' not found at: {model_path}")

            print(f"Loading '{model_type}' pipeline into memory from {model_path}...")
            self.loaded_models[model_type] = joblib.load(model_path)

        return self.loaded_models[model_type]

    async def score_transaction(
        self,
        transaction_features: pd.DataFrame,
        model_type: str = "xgboost",
        raw_tx_payload: dict | None = None,
        db=None,
    ) -> dict:
        """
        Runs inference and returns custom multi-risk scores, recommendations, and SHAP explanations.
        Incorporates database threat matches, impossible travel, and decision engine logic.
        """
        pipeline = self._get_model_pipeline(model_type)

        # 1. Run predictions to get base ML probability
        if model_type == "isolation_forest":
            raw_anomaly_score = pipeline.score_samples(transaction_features)[0]
            ml_prob = float(1.0 / (1.0 + np.exp(10.0 * (raw_anomaly_score + 0.55))))
        else:
            ml_prob = float(pipeline.predict_proba(transaction_features)[0, 1])

        # 2. Invoke rules-based custom risk scoring engine
        row = transaction_features.iloc[0]
        scoring_out = self.scoring_engine.score_transaction(
            row, ml_prob, raw_tx_payload=raw_tx_payload
        )

        # 3. Calculate local SHAP explanations for explainability
        self.explainer.fit_or_load(pipeline)
        explanations = self.explainer.explain_transaction(transaction_features)

        # 4. Threat Intelligence Matches
        threat_match = {"matched": False, "indicators": [], "risk_multiplier": 1.0}
        if db is not None and raw_tx_payload is not None:
            from src.models.threat_intel import ThreatIntelRegistry

            try:
                threat_match = await ThreatIntelRegistry.evaluate_transaction(db, raw_tx_payload)
            except Exception as e:
                print(f"Threat Intelligence lookup failed: {e}")

        # 5. Impossible Travel check
        impossible_travel = False
        if db is not None and raw_tx_payload is not None:
            sender_id = raw_tx_payload.get("sender_id")
            if sender_id:
                from sqlalchemy import select

                from src.database.models import Transaction

                try:
                    stmt = (
                        select(Transaction)
                        .where(Transaction.sender_id == sender_id)
                        .order_by(Transaction.timestamp.desc())
                        .limit(1)
                    )
                    res = await db.execute(stmt)
                    prev_tx = res.scalar_one_or_none()
                    if prev_tx:
                        impossible_travel = check_impossible_travel(prev_tx, raw_tx_payload)
                except Exception as e:
                    print(f"Impossible Travel database lookup failed: {e}")

        # 6. Graph shared entity metrics lookup
        graph_metrics = None
        if raw_tx_payload is not None:
            from src.features.graph_analysis import GraphFraudDetector, get_card_id

            graph_path = os.path.join(self.models_dir, "graph_fraud_model.pkl")
            if os.path.exists(graph_path):
                try:
                    detector = GraphFraudDetector()
                    detector.load_graph(graph_path)
                    s_id = raw_tx_payload.get("sender_id")
                    d_id = raw_tx_payload.get("device_id")
                    tx_id = raw_tx_payload.get("transaction_id", "")
                    card_id = get_card_id(s_id, tx_id)
                    graph_metrics = detector.compute_graph_metrics(
                        sender_id=s_id, device_id=d_id, card_id=card_id
                    )

                    # Check if in fraud ring
                    is_in_ring = False
                    clusters = detector.detect_suspicious_clusters()
                    for c in clusters:
                        if c["cluster_type"] == "fraud_ring" and s_id in c.get(
                            "connected_users", []
                        ):
                            is_in_ring = True
                            break
                    graph_metrics["is_fraud_ring_member"] = is_in_ring
                except Exception as e:
                    print(f"Graph metrics computation failed: {e}")

        # 7. Map behavioral deviations (Z-score from amount / user average and frequency)
        behavioral_deviations = None
        amount_ratio = row.get("amount_to_user_avg_ratio", 1.0)
        freq_5m = row.get("user_velocity_5m", 1)
        behavioral_deviations = {
            "amount_z_score": float(amount_ratio),
            "frequency_deviation": 1 if freq_5m > 3 else 0,
        }

        # 8. Decision Intelligence Engine Routing
        from src.models.decision import DecisionEngine

        decision = DecisionEngine.evaluate_decision(
            risk_score=scoring_out["risk_score"],
            threat_match=threat_match,
            behavioral_deviations=behavioral_deviations,
            graph_metrics=graph_metrics,
            impossible_travel=impossible_travel,
        )

        # Map decision action back to simple recommendation (ALLOW, FLAG, BLOCK)
        action = decision["action"]
        if action == "APPROVE":
            recommendation = "ALLOW"
        elif action in ["REQUEST_VERIFICATION", "MANUAL_REVIEW"]:
            recommendation = "FLAG"
        else:
            recommendation = "BLOCK"

        risk_bucket = "Low"
        c_score = decision["calibrated_score"]
        if c_score >= 80.0:
            risk_bucket = "Critical"
        elif c_score >= 60.0:
            risk_bucket = "High"
        elif c_score >= 30.0:
            risk_bucket = "Medium"

        return {
            "sub_scores": scoring_out["sub_scores"],
            "risk_score": c_score,
            "risk_bucket": risk_bucket,
            "recommendation": recommendation,
            "model_version": f"{model_type}-v1.0.0",
            "explanations": explanations,
            "decision_action": action,
            "decision_reasons": decision["reasons"],
        }
