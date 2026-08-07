import pytest
from pydantic import ValidationError

from src.api.schemas.transaction import TransactionCreate


def test_transaction_create_valid(mock_transaction_payload):
    """
    Assures that a valid transaction payload maps correctly without errors.
    """
    transaction = TransactionCreate(**mock_transaction_payload)
    assert transaction.sender_id == mock_transaction_payload["sender_id"]
    assert transaction.amount == mock_transaction_payload["amount"]


def test_transaction_create_invalid_amount(mock_transaction_payload):
    """
    Assures that non-positive amounts fail constraints.
    """
    invalid_payload = mock_transaction_payload.copy()
    invalid_payload["amount"] = -10.0
    with pytest.raises(ValidationError):
        TransactionCreate(**invalid_payload)
