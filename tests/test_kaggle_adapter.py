from datetime import datetime

import pytest

from src.adapters.kaggle_fraud import KaggleFraudAdapter


def test_kaggle_adapter_maps_transaction():
    raw_transaction = {
        "transaction_id": "tx_001",
        "cc_num": "4111111111111111",
        "amount": 250.50,
        "category": "shopping_net",
        "transaction_time": "2020-06-21T22:30:00",
    }

    transaction = (
        KaggleFraudAdapter.to_canonical_transaction(
            raw_transaction
        )
    )

    assert transaction.transaction_id == "tx_001"
    assert transaction.entity_id == "4111111111111111"
    assert transaction.amount == 250.50
    assert transaction.category == "shopping_net"
    assert transaction.transaction_time == datetime.fromisoformat(
        "2020-06-21T22:30:00"
    )


def test_kaggle_adapter_rejects_invalid_datetime():
    raw_transaction = {
        "transaction_id": "tx_001",
        "cc_num": "4111111111111111",
        "amount": 250.50,
        "category": "shopping_net",
        "transaction_time": "not-a-date",
    }

    with pytest.raises(
        ValueError,
        match="transaction_time must be a valid ISO datetime",
    ):
        KaggleFraudAdapter.to_canonical_transaction(
            raw_transaction
        )


def test_kaggle_adapter_rejects_missing_required_field():
    raw_transaction = {
        "transaction_id": "tx_001",
        "amount": 250.50,
        "category": "shopping_net",
        "transaction_time": "2020-06-21T22:30:00",
    }

    with pytest.raises(ValueError):
        KaggleFraudAdapter.to_canonical_transaction(
            raw_transaction
        )