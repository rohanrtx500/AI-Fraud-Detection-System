import numpy as np
import pandas as pd


class FraudRiskScoringEngine:
    """
    Custom Fraud Risk Scoring Engine.
    Evaluates individual dimensions (Amount, Frequency, Geolocation, multivariate Behavior)
    and aggregates them into a final score (0-100) mapped to severity risk buckets.
    Integrates with User Behavioral Profiling to flag deviations from normal baselines.
    """

    def __init__(self):
        # Weight configurations
        self.w_behavior = 0.30
        self.w_amount = 0.25
        self.w_location = 0.25
        self.w_frequency = 0.20

        # Max-pool safety factor (prevents dilution of critical sub-risks)
        self.max_pool_factor = 0.85

    def calculate_amount_risk(self, row: pd.Series, deviations: dict | None = None) -> float:
        """
        Calculates risk score based on transaction amount and spending average.
        Integrates Z-score deviations from user behavioral profiling.
        """
        amount = float(row.get("amount", 0.0))
        ratio = float(row.get("amount_to_user_avg_ratio", 1.0))

        # 1. Absolute size risk mapping
        if amount <= 50.0:
            size_risk = 10.0
        elif amount <= 250.0:
            size_risk = 30.0
        elif amount <= 1000.0:
            size_risk = 60.0
        elif amount <= 3000.0:
            size_risk = 80.0
        else:
            size_risk = 95.0

        # 2. Relative spend ratio mapping
        if ratio <= 1.0:
            ratio_risk = 10.0
        elif ratio <= 2.5:
            ratio_risk = 10.0 + (ratio - 1.0) * (40.0 / 1.5)
        elif ratio <= 6.0:
            ratio_risk = 50.0 + (ratio - 2.5) * (40.0 / 3.5)
        else:
            ratio_risk = 98.0

        amount_risk = max(size_risk, ratio_risk)

        # 3. Behavioral deviation overrides
        if deviations:
            z_score = deviations.get("amount_z_score", 0.0)
            if z_score > 5.0:
                amount_risk = max(amount_risk, 95.0)  # Extreme spend anomaly
            elif z_score > 3.0:
                amount_risk = max(amount_risk, 80.0)  # High spend anomaly

        return float(np.clip(amount_risk, 0.0, 100.0))

    def calculate_frequency_risk(
        self,
        row: pd.Series,
        deviations: dict | None = None,
        graph_metrics: dict | None = None,
    ) -> float:
        """
        Calculates risk score based on rolling velocity windows.
        Integrates frequency anomalies from user profiling and device/card sharing from graph analysis.
        """
        vel_5m = int(row.get("user_velocity_5m", 0))
        vel_1h = int(row.get("user_velocity_1h", 0))

        # 1. Immediate 5-minute velocity threat
        if vel_5m == 0:
            v5_risk = 0.0
        elif vel_5m == 1:
            v5_risk = 30.0
        elif vel_5m == 2:
            v5_risk = 70.0
        else:
            v5_risk = 98.0

        # 2. 1-hour cumulative velocity threat
        if vel_1h <= 1:
            v1h_risk = 10.0
        elif vel_1h <= 4:
            v1h_risk = 10.0 + (vel_1h - 1) * 15.0
        elif vel_1h <= 8:
            v1h_risk = 55.0 + (vel_1h - 4) * 8.0
        else:
            v1h_risk = 95.0

        frequency_risk = max(v5_risk, v1h_risk)

        # 3. Profiling frequency deviation overrides
        if deviations:
            freq_dev = deviations.get("frequency_deviation", 0)
            if freq_dev == 1:
                frequency_risk = max(frequency_risk, 90.0)  # Transaction occurs too fast

        # 4. Graph sharing overrides
        if graph_metrics:
            if graph_metrics.get("card_user_count", 0) > 1:
                frequency_risk = max(frequency_risk, 90.0)  # Card shared across accounts
            if graph_metrics.get("user_card_count", 0) > 2:
                frequency_risk = max(frequency_risk, 70.0)  # User has too many cards in graph

        return float(np.clip(frequency_risk, 0.0, 100.0))

    def calculate_location_risk(self, row: pd.Series, deviations: dict | None = None) -> float:
        """
        Calculates risk score based on geolocation hops and IP country mismatches.
        Integrates profiling mismatches (unseen countries / cities).
        """
        ip_country_mismatch = int(row.get("ip_country_mismatch", 0))

        if ip_country_mismatch == 1:
            location_risk = 90.0
        else:
            location_risk = 10.0

        # Geographic deviations from learned baseline profiles
        if deviations:
            country_dev = deviations.get("location_country_deviation", 0)
            city_dev = deviations.get("location_city_deviation", 0)
            if country_dev == 1:
                location_risk = max(location_risk, 90.0)  # Completely unseen country
            elif city_dev == 1:
                location_risk = max(location_risk, 65.0)  # Completely unseen city

        return float(np.clip(location_risk, 0.0, 100.0))

    def calculate_behavior_risk(
        self,
        row: pd.Series,
        ml_prob: float,
        deviations: dict | None = None,
        graph_metrics: dict | None = None,
    ) -> float:
        """
        Calculates risk score combining ML prediction probability, typical hours, device configurations, and graph sharing centralities.
        """
        hour = int(row.get("hour_of_day", 12))
        ml_score = ml_prob * 100.0

        if 1 <= hour <= 5:
            time_risk = 75.0
        else:
            time_risk = 10.0

        behavior_risk = (0.80 * ml_score) + (0.20 * time_risk)

        # Behavioral deviations from baseline profiling
        if deviations:
            device_dev = deviations.get("device_deviation", 0)
            time_dev = deviations.get("time_deviation", 0)
            if device_dev == 1:
                behavior_risk = max(behavior_risk, 80.0)  # Completely unseen device ID
            elif time_dev == 1:
                behavior_risk = max(behavior_risk, 60.0)  # Transaction occurs at atypical hour

        # Graph network anomaly overrides
        if graph_metrics:
            if graph_metrics.get("device_user_count", 0) > 2:
                behavior_risk = max(behavior_risk, 85.0)  # Device shared by 3+ accounts
            if graph_metrics.get("card_user_count", 0) > 1:
                behavior_risk = max(
                    behavior_risk, 95.0
                )  # Card shared by 2+ accounts (High ATO Risk)
            if graph_metrics.get("user_device_count", 0) > 3:
                behavior_risk = max(behavior_risk, 75.0)  # User multiplexing 4+ devices

        return float(np.clip(behavior_risk, 0.0, 100.0))

    def score_transaction(
        self, row: pd.Series, ml_prob: float, raw_tx_payload: dict | None = None
    ) -> dict:
        """
        Aggregates individual sub-risk evaluations into a final score (0-100)
        and risk bucket (Low, Medium, High, Critical).
        """
        # 1. Look up user profiling deviations and graph sharing metrics if raw payload exists
        deviations = None
        graph_metrics = None
        if raw_tx_payload:
            sender_id = raw_tx_payload.get("sender_id")
            if sender_id:
                # Profiling deviations
                from src.features.profiling import calculate_behavioral_deviations, load_profile

                profile = load_profile(sender_id)
                if profile:
                    deviations = calculate_behavioral_deviations(raw_tx_payload, profile)

                # Graph metrics
                import os

                from src.features.graph_analysis import GraphFraudDetector

                graph_path = os.path.join("models/registry", "graph_fraud_model.pkl")
                if os.path.exists(graph_path):
                    detector = GraphFraudDetector()
                    try:
                        detector.load_graph(graph_path)
                        device_id = raw_tx_payload.get("device_id")
                        raw_tx_payload.get("transaction_id", "dummy_tx")
                        receiver_id = raw_tx_payload.get("receiver_id")
                        graph_metrics = detector.compute_graph_metrics(
                            sender_id=sender_id, device_id=device_id, receiver_id=receiver_id
                        )
                    except Exception as e:
                        print(f"Error loading graph or computing metrics: {e}")

        # 2. Calculate sub-scores integrating profile & graph metrics
        amount_risk = self.calculate_amount_risk(row, deviations)
        frequency_risk = self.calculate_frequency_risk(row, deviations, graph_metrics)
        location_risk = self.calculate_location_risk(row, deviations)
        behavior_risk = self.calculate_behavior_risk(row, ml_prob, deviations, graph_metrics)

        # Compute weighted sum
        weighted_score = (
            (self.w_behavior * behavior_risk)
            + (self.w_amount * amount_risk)
            + (self.w_location * location_risk)
            + (self.w_frequency * frequency_risk)
        )

        # Apply max-pool override to prevent diluting critical indicator tags
        max_sub_score = max(amount_risk, frequency_risk, location_risk, behavior_risk)
        final_score = max(weighted_score, max_sub_score * self.max_pool_factor)
        final_score = round(float(np.clip(final_score, 0.0, 100.0)), 2)

        # Map to risk severity buckets
        if final_score <= 30.00:
            risk_bucket = "Low"
        elif final_score <= 60.00:
            risk_bucket = "Medium"
        elif final_score <= 80.00:
            risk_bucket = "High"
        else:
            risk_bucket = "Critical"

        res = {
            "sub_scores": {
                "amount_risk": round(amount_risk, 2),
                "frequency_risk": round(frequency_risk, 2),
                "location_risk": round(location_risk, 2),
                "behavior_risk": round(behavior_risk, 2),
            },
            "risk_score": final_score,
            "risk_bucket": risk_bucket,
        }

        # Include metadata in output if calculated
        if deviations:
            res["behavioral_deviations"] = deviations
        if graph_metrics:
            res["graph_metrics"] = graph_metrics

        return res


if __name__ == "__main__":
    # Test CLI script
    engine = FraudRiskScoringEngine()
    print("Scoring engine with profiling tests ready.")
