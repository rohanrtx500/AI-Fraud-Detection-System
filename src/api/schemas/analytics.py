import datetime

from pydantic import BaseModel, Field


class RiskDistributionBucket(BaseModel):
    score_range: str = Field(..., description="Bucket range, e.g., '0-20', '21-40'")
    count: int = Field(..., description="Number of transactions falling in this score range")
    percentage: float = Field(..., description="Percentage of total transactions in this bucket")


class DailyTransactionMetrics(BaseModel):
    date: datetime.date = Field(..., description="Calendar date for the metrics")
    total_transactions: int = Field(..., description="Total volume of transactions processed")
    total_amount: float = Field(..., description="Total aggregate currency value processed")
    flagged_fraud_transactions: int = Field(
        ..., description="Count of transactions flagged as suspicious"
    )
    blocked_transactions: int = Field(
        ..., description="Count of transactions blocked by the platform"
    )


class FraudSummaryMetrics(BaseModel):
    total_processed_count: int = Field(
        ..., description="Lifetime or query-window transaction count"
    )
    total_processed_value: float = Field(..., description="Total currency value processed")
    overall_fraud_rate: float = Field(
        ..., description="Percentage of total transactions confirmed as fraudulent"
    )
    active_alerts_count: int = Field(
        ..., description="Total open risk review alerts pending compliance decision"
    )
    risk_distribution: list[RiskDistributionBucket] = Field(
        ..., description="Aggregated distribution of risk scores"
    )
