from src.storage.paysim_transaction_store import (
    PaySimTransactionStore,
)


def test_paysim_transaction_can_be_saved_and_retrieved(tmp_path):
    db_path = tmp_path / "paysim_transactions.db"

    store = PaySimTransactionStore(
        db_path=str(db_path)
    )

    store.save_transaction(
        transaction_id="paysim_001",
        transaction_type="TRANSFER",
        amount=1000.0,
        oldbalance_org=5000.0,
        oldbalance_dest=0.0,
        fraud_probability=0.95,
        model_decision="FRAUD",
        risk_level="HIGH_RISK",
        action="HOLD",
        created_at="2026-09-25T10:00:00",
    )

    transaction = store.get_transaction(
        "paysim_001"
    )

    assert transaction is not None
    assert transaction["transaction_id"] == "paysim_001"
    assert transaction["transaction_type"] == "TRANSFER"
    assert transaction["amount"] == 1000.0
    assert transaction["oldbalance_org"] == 5000.0
    assert transaction["fraud_probability"] == 0.95
    assert transaction["model_decision"] == "FRAUD"
    assert transaction["action"] == "HOLD"


def test_missing_paysim_transaction_returns_none(tmp_path):
    db_path = tmp_path / "paysim_transactions.db"

    store = PaySimTransactionStore(
        db_path=str(db_path)
    )

    transaction = store.get_transaction(
        "does_not_exist"
    )

    assert transaction is None


def test_paysim_actual_outcome_can_be_recorded(tmp_path):
    db_path = tmp_path / "paysim_transactions.db"

    store = PaySimTransactionStore(
        db_path=str(db_path)
    )

    store.save_transaction(
        transaction_id="paysim_002",
        transaction_type="CASH_OUT",
        amount=2500.0,
        oldbalance_org=2500.0,
        oldbalance_dest=0.0,
        fraud_probability=0.90,
        model_decision="FRAUD",
        risk_level="HIGH_RISK",
        action="HOLD",
        created_at="2026-09-25T10:00:00",
    )

    updated = store.set_actual_outcome(
        transaction_id="paysim_002",
        actual_outcome="LEGITIMATE",
        outcome_source="analyst",
        outcome_reason="Manual investigation found no fraud.",
    )

    assert updated is not None
    assert updated["actual_outcome"] == "LEGITIMATE"
    assert updated["outcome_source"] == "analyst"
    assert (
        updated["outcome_reason"]
        == "Manual investigation found no fraud."
    )
    assert updated["outcome_at"] is not None

    # Model prediction must remain unchanged.
    assert updated["model_decision"] == "FRAUD"
    assert updated["fraud_probability"] == 0.90


def test_unknown_paysim_transaction_outcome_returns_none(tmp_path):
    db_path = tmp_path / "paysim_transactions.db"

    store = PaySimTransactionStore(
        db_path=str(db_path)
    )

    result = store.set_actual_outcome(
        transaction_id="does_not_exist",
        actual_outcome="LEGITIMATE",
        outcome_source="analyst",
    )

    assert result is None


def test_paysim_evaluated_transactions_only_include_known_outcomes(
    tmp_path,
):
    db_path = tmp_path / "paysim_transactions.db"

    store = PaySimTransactionStore(
        db_path=str(db_path)
    )

    store.save_transaction(
        transaction_id="paysim_003",
        transaction_type="TRANSFER",
        amount=1000.0,
        oldbalance_org=5000.0,
        oldbalance_dest=0.0,
        fraud_probability=0.95,
        model_decision="FRAUD",
        risk_level="HIGH_RISK",
        action="HOLD",
        created_at="2026-09-25T10:00:00",
    )

    store.save_transaction(
        transaction_id="paysim_004",
        transaction_type="PAYMENT",
        amount=100.0,
        oldbalance_org=500.0,
        oldbalance_dest=1000.0,
        fraud_probability=0.01,
        model_decision="LEGITIMATE",
        risk_level="LOW_RISK",
        action="APPROVE",
        created_at="2026-09-25T10:01:00",
    )

    store.set_actual_outcome(
        transaction_id="paysim_003",
        actual_outcome="FRAUD",
        outcome_source="analyst",
    )

    evaluated = store.get_evaluated_transactions()

    assert len(evaluated) == 1
    assert evaluated[0]["transaction_id"] == "paysim_003"
    assert evaluated[0]["model_decision"] == "FRAUD"
    assert evaluated[0]["actual_outcome"] == "FRAUD"