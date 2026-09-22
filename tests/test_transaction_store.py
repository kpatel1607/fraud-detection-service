from pathlib import Path

from src.storage.transaction_store import TransactionStore


def test_transaction_can_be_saved_and_retrieved(tmp_path):
    db_path = tmp_path / "transactions.db"

    store = TransactionStore(
        db_path=str(db_path)
    )

    store.save_transaction(
        transaction_id="txn_001",
        entity_id="CARD_001",
        amount=100.0,
        category="grocery_pos",
        transaction_time="2020-06-21T12:00:00",
        fraud_probability=0.01,
        model_decision="LEGITIMATE",
        risk_level="LOW_RISK",
        action="APPROVE",
        reasons=["Test transaction"],
        prev_avg_amt=None,
        prev_5_avg_amt=None,
        amt_ratio_recent5=None,
        created_at="2026-09-15T10:00:00",
    )

    transaction = store.get_transaction("txn_001")

    assert transaction is not None
    assert transaction["transaction_id"] == "txn_001"
    assert transaction["cc_num"] == "CARD_001"
    assert transaction["amount"] == 100.0
    assert transaction["category"] == "grocery_pos"
    assert transaction["fraud_probability"] == 0.01
    assert transaction["action"] == "APPROVE"


def test_missing_transaction_returns_none(tmp_path):
    db_path = tmp_path / "transactions.db"

    store = TransactionStore(
        db_path=str(db_path)
    )

    transaction = store.get_transaction(
        "does_not_exist"
    )

    assert transaction is None
    
def test_transaction_store_has_ground_truth_columns(tmp_path):
    db_path = tmp_path / "transactions.db"

    TransactionStore(
        db_path=str(db_path)
    )

    import sqlite3

    conn = sqlite3.connect(db_path)

    columns = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(transactions)"
        ).fetchall()
    }

    conn.close()

    assert "actual_outcome" in columns
    assert "outcome_source" in columns
    assert "outcome_reason" in columns
    assert "outcome_at" in columns
    
def test_actual_outcome_can_be_recorded(tmp_path):
    db_path = tmp_path / "transactions.db"

    store = TransactionStore(
        db_path=str(db_path)
    )

    store.save_transaction(
        transaction_id="txn_001",
        entity_id="CARD_001",
        amount=100.0,
        category="shopping_net",
        transaction_time="2020-06-21T12:00:00",
        fraud_probability=0.10,
        model_decision="LEGITIMATE",
        risk_level="LOW_RISK",
        action="APPROVE",
        reasons=[],
        prev_avg_amt=None,
        prev_5_avg_amt=None,
        amt_ratio_recent5=None,
        created_at="2026-09-15T10:00:00",
    )

    updated = store.set_actual_outcome(
        transaction_id="txn_001",
        actual_outcome="FRAUD",
        outcome_source="analyst",
        outcome_reason="Manual investigation confirmed fraud.",
    )

    assert updated is not None
    assert updated["actual_outcome"] == "FRAUD"
    assert updated["outcome_source"] == "analyst"
    assert (
        updated["outcome_reason"]
        == "Manual investigation confirmed fraud."
    )
    assert updated["outcome_at"] is not None

    # Original model prediction must remain unchanged.
    assert updated["model_decision"] == "LEGITIMATE"
    assert updated["fraud_probability"] == 0.10


def test_unknown_transaction_outcome_returns_none(tmp_path):
    db_path = tmp_path / "transactions.db"

    store = TransactionStore(
        db_path=str(db_path)
    )

    result = store.set_actual_outcome(
        transaction_id="does_not_exist",
        actual_outcome="LEGITIMATE",
        outcome_source="analyst",
    )

    assert result is None