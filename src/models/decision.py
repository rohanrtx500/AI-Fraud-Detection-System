class DecisionEngine:
    """
    Intelligent Decision Engine.
    Lays down conditional routing matrices incorporating ML risk score,
    geographical speed anomalies, network graph risks, and threat intelligence matches
    to output recommended action codes and structured text explanations.
    """

    @staticmethod
    def evaluate_decision(
        risk_score: float,
        threat_match: dict,
        behavioral_deviations: dict | None = None,
        graph_metrics: dict | None = None,
        impossible_travel: bool = False,
    ) -> dict:
        """
        Determines action recommendation: APPROVE, REQUEST_VERIFICATION, MANUAL_REVIEW, ESCALATE, BLOCK.
        Includes a list of reasoning explanations.
        """
        reasons = []
        action = "APPROVE"

        # 1. Threat Intelligence Blacklist Matches
        threat_triggered = threat_match.get("matched", False)
        multiplier = threat_match.get("risk_multiplier", 1.0)

        # Apply threat multipliers to risk score
        calibrated_score = min(100.0, risk_score * multiplier)

        if threat_triggered:
            action = "BLOCK"
            for ind in threat_match.get("indicators", []):
                reasons.append(
                    f"Threat Intelligence: Blacklisted {ind['type']} value '{ind['value']}' matched (Source: {ind['source']})."
                )

        # 2. Impossible Travel Geolocation hops
        if impossible_travel:
            action = "BLOCK"
            reasons.append(
                "Impossible Travel: Geographical velocity exceeds physical flight speed thresholds."
            )

        # 3. Behavioral deviations Z-Score overrides
        if behavioral_deviations:
            if behavioral_deviations.get("amount_z_score", 0.0) > 4.0:
                reasons.append(
                    f"Behavioral Profile: Spend amount deviation (Z-Score = {behavioral_deviations['amount_z_score']:.2f}) exceeds normal boundaries."
                )
            if behavioral_deviations.get("frequency_deviation", 0) == 1:
                reasons.append(
                    "Behavioral Profile: Velocity spike indicates potential automated transaction script."
                )

        # 4. Graph Shared Entity Centralities
        if graph_metrics:
            card_sharing = graph_metrics.get("card_user_count", 0)
            user_cards = graph_metrics.get("user_card_count", 0)
            is_in_ring = graph_metrics.get("is_fraud_ring_member", False)

            if card_sharing > 1:
                reasons.append(
                    f"Knowledge Graph: Payment card shared across {card_sharing} accounts, indicating credit card sharing rings."
                )
            if user_cards > 2:
                reasons.append(
                    f"Knowledge Graph: User account associated with {user_cards} unique cards, indicating high card velocity."
                )
            if is_in_ring:
                action = "ESCALATE"
                reasons.append(
                    "Knowledge Graph: Node belongs to a highly correlated fraudulent cluster ring."
                )

        # 5. Core ML Calibrated Risk Score Boundaries
        if action != "BLOCK" and action != "ESCALATE":
            if calibrated_score >= 90.0:
                action = "BLOCK"
                reasons.append(
                    f"Risk Assessment: Calibrated score ({calibrated_score:.1f}) exceeds BLOCK limit (90.0)."
                )
            elif calibrated_score >= 75.0:
                action = "ESCALATE"
                reasons.append(
                    f"Risk Assessment: Calibrated score ({calibrated_score:.1f}) triggers Case Escalation."
                )
            elif calibrated_score >= 50.0:
                action = "MANUAL_REVIEW"
                reasons.append(
                    f"Risk Assessment: Calibrated score ({calibrated_score:.1f}) requires Analyst manual review."
                )
            elif calibrated_score >= 30.0:
                action = "REQUEST_VERIFICATION"
                reasons.append(
                    f"Risk Assessment: Calibrated score ({calibrated_score:.1f}) requires Step-Up Verification (MFA)."
                )
            else:
                action = "APPROVE"
                reasons.append(
                    f"Risk Assessment: Low score ({calibrated_score:.1f}) maps to low risk."
                )

        if not reasons:
            reasons.append("All scoring parameters reside within benign thresholds.")

        return {
            "action": action,
            "calibrated_score": round(calibrated_score, 2),
            "reasons": reasons,
            "threat_triggered": threat_triggered,
            "impossible_travel": impossible_travel,
        }
