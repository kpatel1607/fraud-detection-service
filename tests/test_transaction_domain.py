from datetime import datetime

import pytest

from src.domain.transaction import CanonicalTransaction


def test_canonical_transaction_accepts_valid_transaction():
    transaction = CanonicalTransaction(
        transaction_id="tx_001",
        entity_id="card_001",
        amount=150.0,
        category="grocery_pos",
        transaction_time=datetime.fromisoformat(
            "2020-06-21T12:00:00"
        ),
    )

    assert transaction.transaction_id == "tx_001"
    assert transaction.entity_id == "card_001"
    assert transaction.amount == 150.0
    assert transaction.category == "grocery_pos"
    assert transaction.transaction_time == datetime.fromisoformat(
        "2020-06-21T12:00:00"
    )


def test_canonical_transaction_rejects_non_positive_amount():
    with pytest.raises(ValueError):
        CanonicalTransaction(
            transaction_id="tx_001",
            entity_id="card_001",
            amount=0,
            category="grocery_pos",
            transaction_time=datetime.fromisoformat(
                "2020-06-21T12:00:00"
            ),
        )


def test_canonical_transaction_rejects_empty_card_id():
    with pytest.raises(ValueError):
        CanonicalTransaction(
            transaction_id="tx_001",
            entity_id="",
            amount=100,
            category="grocery_pos",
            transaction_time=datetime.fromisoformat(
                "2020-06-21T12:00:00"
            ),
        )