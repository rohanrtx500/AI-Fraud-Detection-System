from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class TransactionBase(BaseModel):
    sender_id: str = Field(..., description="Unique identifier of the transaction initiator")
    receiver_id: str = Field(..., description="Unique identifier of the transaction recipient")
    amount: float = Field(..., gt=0.0, description="Transaction amount in currency units")
    currency: str = Field("USD", min_length=3, max_length=3, description="ISO currency code")
    merchant_category: str = Field(
        ..., description="Merchant category code or industry classification"
    )
    location_country: str = Field(
        ...,
        min_length=2,
        max_length=2,
        description="Two-letter ISO country code of transaction source",
    )
    location_city: str = Field(..., description="City where the transaction occurred")
    device_id: str = Field(..., description="Unique hardware fingerprint of client device")
    ip_address: str = Field(..., description="IPv4 or IPv6 address of transaction source")


class TransactionCreate(TransactionBase):
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None),
        description="UTC timestamp of the transaction",
    )


class TransactionResponse(TransactionBase):
    transaction_id: str = Field(..., description="System-generated UUID for the transaction")
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
