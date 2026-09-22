from src.monitoring.evaluator import TransactionEvaluator
from src.storage.transaction_store import TransactionStore


def save_transaction(
    store,
    transaction_id,
    model_decision,
    actual_outcome,
):
    store.save_transaction(
        transaction_id=transaction_id,
        entity_id=f"CARD_{transaction_id}",
        amount=100.0,
        category="grocery_pos",
        transaction_time="2020-06-21T12:00:00",
        fraud_probability=0.5,
        model_decision=model_decision,
        risk_level="REVIEW",
        action="HUMAN_REVIEW",
        reasons=[],
        prev_avg_amt=None,
        prev_5_avg_amt=None,
        amt_ratio_recent5=None,
        created_at="2026-09-15T10:00:00",
    )

    store.set_actual_outcome(
        transaction_id=transaction_id,
        actual_outcome=actual_outcome,
        outcome_source="test",
    )


def test_evaluator_builds_confusion_matrix(tmp_path):
    store = TransactionStore(
        db_path=str(tmp_path / "transactions.db")
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

    evaluator = TransactionEvaluator(store)

    metrics = evaluator.evaluate()

    assert metrics.true_positives == 1
    assert metrics.true_negatives == 1
    assert metrics.false_positives == 1
    assert metrics.false_negatives == 1


def test_unresolved_transactions_are_excluded(tmp_path):
    store = TransactionStore(
        db_path=str(tmp_path / "transactions.db")
    )

    store.save_transaction(
        transaction_id="unresolved",
        entity_id="CARD_001",
        amount=100.0,
        category="grocery_pos",
        transaction_time="2020-06-21T12:00:00",
        fraud_probability=0.5,
        model_decision="FRAUD",
        risk_level="REVIEW",
        action="HUMAN_REVIEW",
        reasons=[],
        prev_avg_amt=None,
        prev_5_avg_amt=None,
        amt_ratio_recent5=None,
        created_at="2026-09-15T10:00:00",
    )

    evaluator = TransactionEvaluator(store)

    metrics = evaluator.evaluate()

    assert metrics.true_positives == 0
    assert metrics.true_negatives == 0
    assert metrics.false_positives == 0
    assert metrics.false_negatives == 0