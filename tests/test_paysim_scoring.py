from src.domain.paysim_transaction import PaySimTransaction
from src.storage.paysim_transaction_store import (
    PaySimTransactionStore,
)
from src.review.paysim_review_queue import PaySimReviewQueue
from src.rules.paysim_risk_policy import PaySimRiskPolicy
from src.services.paysim_scoring import PaySimScoringService


class FakePaySimPredictor:
    def predict_probability(self, transaction) -> float:
        return 0.60


def test_review_transaction_is_added_to_queue(tmp_path):
    queue = PaySimReviewQueue(
        db_path=str(tmp_path / "paysim_reviews.db")
    )

    transaction_store = PaySimTransactionStore(
        db_path=str(tmp_path / "paysim_transactions.db")
    )

    service = PaySimScoringService(
        predictor=FakePaySimPredictor(),
        risk_policy=PaySimRiskPolicy(),
        review_queue=queue,
        transaction_store=transaction_store,
    )

    transaction = PaySimTransaction(
        transaction_id="review-test-001",
        transaction_type="TRANSFER",
        amount=10000.0,
        oldbalance_org=20000.0,
        oldbalance_dest=0.0,
    )

    result = service.score(transaction)

    assert result.fraud_probability == 0.60
    assert result.model_decision == "FRAUD"
    assert result.risk_level == "REVIEW"
    assert result.action == "HUMAN_REVIEW"

    pending_reviews = queue.get_pending_reviews()

    assert len(pending_reviews) == 1
    assert pending_reviews[0]["transaction_id"] == "review-test-001"
    assert pending_reviews[0]["status"] == "PENDING"
    
def test_scored_transaction_is_persisted(tmp_path):
    queue = PaySimReviewQueue(
        db_path=str(tmp_path / "paysim_reviews.db")
    )

    transaction_store = PaySimTransactionStore(
        db_path=str(tmp_path / "paysim_transactions.db")
    )

    service = PaySimScoringService(
        predictor=FakePaySimPredictor(),
        risk_policy=PaySimRiskPolicy(),
        review_queue=queue,
        transaction_store=transaction_store,
    )

    transaction = PaySimTransaction(
        transaction_id="persist-test-001",
        transaction_type="TRANSFER",
        amount=1000.0,
        oldbalance_org=5000.0,
        oldbalance_dest=0.0,
    )

    result = service.score(transaction)

    stored = transaction_store.get_transaction(
        "persist-test-001"
    )

    assert stored is not None
    assert stored["transaction_id"] == result.transaction_id
    assert stored["fraud_probability"] == result.fraud_probability
    assert stored["model_decision"] == result.model_decision
    assert stored["risk_level"] == result.risk_level
    assert stored["action"] == result.action


def test_duplicate_paysim_transaction_is_idempotent(tmp_path):
    queue = PaySimReviewQueue(
        db_path=str(tmp_path / "paysim_reviews.db")
    )

    transaction_store = PaySimTransactionStore(
        db_path=str(tmp_path / "paysim_transactions.db")
    )

    service = PaySimScoringService(
        predictor=FakePaySimPredictor(),
        risk_policy=PaySimRiskPolicy(),
        review_queue=queue,
        transaction_store=transaction_store,
    )

    transaction = PaySimTransaction(
        transaction_id="idempotency-test-001",
        transaction_type="TRANSFER",
        amount=1000.0,
        oldbalance_org=5000.0,
        oldbalance_dest=0.0,
    )

    first_result = service.score(transaction)
    second_result = service.score(transaction)

    assert second_result == first_result

    stored = transaction_store.get_transaction(
        "idempotency-test-001"
    )

    assert stored is not None
    assert stored["transaction_id"] == "idempotency-test-001"
    
def test_resolving_paysim_review_records_actual_outcome(tmp_path):
    queue = PaySimReviewQueue(
        db_path=str(tmp_path / "paysim_reviews.db")
    )
    transaction_store = PaySimTransactionStore(
        db_path=str(tmp_path / "paysim_transactions.db")
    )

    service = PaySimScoringService(
        predictor=FakePaySimPredictor(),
        risk_policy=PaySimRiskPolicy(),
        review_queue=queue,
        transaction_store=transaction_store,
    )

    transaction = PaySimTransaction(
        transaction_id="outcome-test-001",
        transaction_type="TRANSFER",
        amount=10000.0,
        oldbalance_org=20000.0,
        oldbalance_dest=0.0,
    )

    result = service.score(transaction)

    assert result.action == "HUMAN_REVIEW"

    review = queue.resolve_review(
        transaction_id="outcome-test-001",
        actual_outcome="FRAUD",
    )

    assert review is not None
    assert review["status"] == "RESOLVED"
    assert review["actual_outcome"] == "FRAUD"

    updated = transaction_store.set_actual_outcome(
        transaction_id="outcome-test-001",
        actual_outcome="FRAUD",
        outcome_source="ANALYST_REVIEW",
        outcome_reason="PaySim review resolved by analyst.",
    )

    assert updated is not None
    assert updated["actual_outcome"] == "FRAUD"

    stored = transaction_store.get_transaction(
        "outcome-test-001"
    )

    assert stored is not None
    assert stored["actual_outcome"] == "FRAUD"
    assert stored["outcome_source"] == "ANALYST_REVIEW"
    assert stored["outcome_reason"] == (
        "PaySim review resolved by analyst."
    )
    assert stored["outcome_at"] is not None