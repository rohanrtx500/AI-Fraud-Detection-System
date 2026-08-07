from typing import Any

import numpy as np
import pandas as pd
import shap
from sklearn.pipeline import Pipeline


class SHAPExplainerWrapper:
    """
    Explainable AI (XAI) Wrapper for the Fraud Detection system.
    Runs SHAP TreeExplainer on preprocessed features, maps attribution weights
    back to raw feature definitions, and provides human-readable reason descriptions.
    """

    def __init__(self):
        self.explainer = None
        self.preprocessor = None
        self.feature_names_out = None

    def fit_or_load(self, pipeline: Pipeline):
        """
        Extracts preprocessor and model estimator, and instantiates the TreeExplainer.
        """
        self.preprocessor = pipeline.named_steps["preprocessor"]
        classifier = pipeline.named_steps["classifier"]

        # Instantiate TreeExplainer directly on fitted classifier tree-structure
        # (This is extremely fast and suited for real-time API latency)
        self.explainer = shap.TreeExplainer(classifier)

        # Track output features of preprocessor
        # Handled differently depending on sklearn versions
        if hasattr(self.preprocessor, "get_feature_names_out"):
            self.feature_names_out = self.preprocessor.get_feature_names_out()
        else:
            # Fallback for older scikit-learn
            self.feature_names_out = None

    def explain_transaction(self, raw_features: pd.DataFrame) -> list[dict[str, Any]]:
        """
        Computes SHAP values, aggregates one-hot encoded dimensions back to raw inputs,
        and outputs sorted lists of positive and negative risk contributors.
        """
        if self.explainer is None or self.preprocessor is None:
            raise RuntimeError("SHAP explainer is not initialized. Call fit_or_load() first.")

        # 1. Transform raw 1-row transaction into preprocessed numerical feature vector
        X_preprocessed = self.preprocessor.transform(raw_features)

        # Resolve feature names
        if self.feature_names_out is not None:
            feature_names = self.feature_names_out
        else:
            # Build names dynamically if get_feature_names_out is missing
            feature_names = [f"f_{i}" for i in range(X_preprocessed.shape[1])]

        # 2. Compute raw SHAP values
        raw_shaps = self.explainer.shap_values(X_preprocessed)

        # 3. Parse SHAP output array dimensions robustly (handles XGBoost vs Random Forest formats)
        if isinstance(raw_shaps, list):
            # RandomForest classification outputs list of arrays per class (index 1 is fraud class)
            shaps = raw_shaps[1][0] if len(raw_shaps) > 1 else raw_shaps[0][0]
        elif isinstance(raw_shaps, np.ndarray):
            if len(raw_shaps.shape) == 3:  # shape: (1, num_features, num_classes)
                shaps = raw_shaps[0, :, 1]
            elif len(raw_shaps.shape) == 2:  # shape: (1, num_features)
                shaps = raw_shaps[0]
            else:
                shaps = raw_shaps
        else:
            shaps = np.array(raw_shaps)

        # 4. Map preprocessed features back to raw inputs
        # E.g. summing cat__currency_USD and cat__currency_EUR back into a single 'currency' weight
        mapped_attributions: dict[str, float] = {}

        for name, val in zip(feature_names, shaps, strict=False):
            raw_name = name
            if name.startswith("num__"):
                raw_name = name[5:]
            elif name.startswith("cat__"):
                # Check which categorical column from definition is inside name
                raw_name = None
                for cat_col in ["currency", "merchant_category", "location_country"]:
                    if name[5:].startswith(cat_col):
                        raw_name = cat_col
                        break
                if not raw_name:
                    raw_name = name[5:].split("_")[0]  # Fallback

            mapped_attributions[raw_name] = mapped_attributions.get(raw_name, 0.0) + float(val)

        # 5. Formulate sorted human-readable explanations list
        explanations = []
        total_abs_shap = sum(abs(v) for v in mapped_attributions.values()) + 1e-5

        for f_name, val in mapped_attributions.items():
            impact = (abs(val) / total_abs_shap) * 100.0
            direction = "INCREASED_RISK" if val > 0 else "DECREASED_RISK"

            # Context-specific reason descriptions
            if f_name == "ip_country_mismatch" and val > 0:
                desc = f"IP Country location does not match home billing country (+{val:.2f})"
            elif f_name == "amount_to_user_avg_ratio" and val > 0:
                desc = f"Transaction amount is significantly higher than user's normal average (+{val:.2f})"
            elif f_name == "user_velocity_5m" and val > 0:
                desc = f"High frequency of transactions within a 5-minute window (+{val:.2f})"
            elif f_name == "user_velocity_1h" and val > 0:
                desc = f"High frequency of transactions within a 1-hour window (+{val:.2f})"
            elif f_name == "amount" and val > 0:
                desc = f"High absolute transaction amount (+{val:.2f})"
            elif val > 0:
                desc = f"Feature '{f_name}' contributed to increased risk (+{val:.2f})"
            else:
                desc = f"Feature '{f_name}' acted as a risk mitigator ({val:.2f})"

            explanations.append(
                {
                    "feature_name": f_name,
                    "shap_value": round(val, 4),
                    "impact_score": round(impact, 2),
                    "direction": direction,
                    "description": desc,
                }
            )

        # Sort explanations by absolute contribution strength descending
        explanations = sorted(explanations, key=lambda x: abs(x["shap_value"]), reverse=True)
        return explanations
