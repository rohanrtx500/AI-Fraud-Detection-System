from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FeatureExplanation(BaseModel):
    feature_name: str = Field(..., description="Name of the feature used in the model")
    shap_value: float = Field(..., description="Raw SHAP value contribution")
    impact_score: float = Field(
        ..., description="Relative normalized percentage impact on output decision"
    )
    direction: str = Field(
        ..., description="Direction of risk impact: 'INCREASED_RISK' or 'DECREASED_RISK'"
    )
    description: str = Field(
        ..., description="Human-readable explanation of feature's contribution"
    )


class RiskAssessmentResponse(BaseModel):
    assessment_id: str | None = Field(None, description="UUID of DB risk assessment record")
    transaction_id: str = Field(..., description="UUID of scored transaction")
    risk_score: float = Field(
        ..., ge=0.0, le=100.0, description="Calibrated risk score between 0 and 100"
    )
    risk_bucket: str = Field(..., description="Severity risk bucket: Low, Medium, High, Critical")
    sub_scores: dict[str, float] = Field(
        ...,
        description="Risk score components: amount_risk, frequency_risk, location_risk, behavior_risk",
    )
    recommendation: str = Field(
        ..., description="System automated decision recommendation: ALLOW, FLAG, BLOCK"
    )
    model_version: str = Field(..., description="ML model identifier used for inference")
    assessed_at: datetime = Field(..., description="UTC timestamp when transaction was scored")
    explanations: list[FeatureExplanation] = Field(
        ..., description="Top contributing features to risk decision (SHAP derived)"
    )
    decision_action: str | None = Field(
        None,
        description="Detailed enterprise decision action (Approve, Review, Verify, Escalate, Block)",
    )
    decision_reasons: list[str] | None = Field(
        None, description="Structured reasons justifying the decision action"
    )

    model_config = ConfigDict(from_attributes=True)
