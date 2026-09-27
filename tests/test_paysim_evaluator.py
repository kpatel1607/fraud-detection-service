from src.monitoring.paysim_evaluator import (
    PaySimTransactionEvaluator,
)
from src.storage.paysim_transaction_store import (
    PaySimTransactionStore,
)


def save_transaction(
    store,
    transaction_id,
    model_decision,
    actual_outcome,
):
    store.save_transaction(
        transaction_id=transaction_id,
        transaction_type="TRANSFER",
        amount=100.0,
        oldbalance_org=500.0,
        oldbalance_dest=0.0,
        fraud_probability=0.5,
        model_decision=model_decision,
        risk_level="REVIEW",
        action="HUMAN_REVIEW",
        created_at="2026-09-25T10:00:00",
    )

    store.set_actual_outcome(
        transaction_id=transaction_id,
        actual_outcome=actual_outcome,
        outcome_source="test",
    )


def test_paysim_evaluator_builds_confusion_matrix(tmp_path):
    store = PaySimTransactionStore(
        db_path=str(tmp_path / "paysim_transactions.db")
    )

    save_transaction(
        store,
        "txn_tp",
        "FRAUD",
        "FRAUD",
    )

    save_transaction(
        store,
        "txn_tn",
        "LEGITIMATE",
        "LEGITIMATE",
    )

    save_transaction(
        store,
        "txn_fp",
        "FRAUD",
        "LEGITIMATE",
    )

    save_transaction(
        store,
        "txn_fn",
        "LEGITIMATE",
        "FRAUD",
    )

    evaluator = PaySimTransactionEvaluator(store)

    metrics = evaluator.evaluate()

    assert metrics.true_positives == 1
    assert metrics.true_negatives == 1
    assert metrics.false_positives == 1
    assert metrics.false_negatives == 1


def test_unresolved_paysim_transactions_are_excluded(tmp_path):
    store = PaySimTransactionStore(
        db_path=str(tmp_path / "paysim_transactions.db")
    )

    store.save_transaction(
        transaction_id="unresolved",
        transaction_type="TRANSFER",
        amount=100.0,
        oldbalance_org=500.0,
        oldbalance_dest=0.0,
        fraud_probability=0.5,
        model_decision="FRAUD",
        risk_level="REVIEW",
        action="HUMAN_REVIEW",
        created_at="2026-09-25T10:00:00",
    )

    evaluator = PaySimTransactionEvaluator(store)

    metrics = evaluator.evaluate()

    assert metrics.true_positives == 0
    assert metrics.true_negatives == 0
    assert metrics.false_positives == 0
    assert metrics.false_negatives == 0