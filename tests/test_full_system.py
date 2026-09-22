from datetime import datetime

from src.model.feature_builder import FraudModelFeatureBuilder
from src.domain.transaction import CanonicalTransaction
from src.features.canonical import CanonicalFeatureEngine
from src.features.historical import HistoricalFeatureEngine
from src.features.state_store import CardStateStore
from src.model.predictor import FraudPredictor
from src.review.review_queue import ReviewQueue
from src.rules.risk_engine import RiskEngine
from src.services.fraud_scoring import FraudScoringService
from src.storage.transaction_store import TransactionStore

class FixedProbabilityPredictor:

    def __init__(self, probabilities):
        self.probabilities = list(probabilities)
        self.call_index = 0

    def predict_probability(self, features):
        if self.call_index >= len(self.probabilities):
            raise RuntimeError(
                "FixedProbabilityPredictor received more calls "
                "than configured probabilities."
            )

        probability = self.probabilities[self.call_index]
        self.call_index += 1

        return probability

def create_system(tmp_path):
    state_store = CardStateStore(
        db_path=str(tmp_path / "state.db")
    )

    transaction_store = TransactionStore(
        db_path=str(tmp_path / "transactions.db")
    )

    historical_engine = HistoricalFeatureEngine(
        state_store=state_store
    )

    feature_engine = CanonicalFeatureEngine(
        historical_engine=historical_engine
    )

    predictor = FraudPredictor()

    risk_engine = RiskEngine(
        review_threshold=0.40,
        high_risk_threshold=0.80,
        late_night_hours={22, 23, 0, 1, 2, 3},
        elevated_fraud_categories={
            "shopping_net",
            "misc_net",
            "grocery_pos",
        },
    )

    review_queue = ReviewQueue(
        db_path=str(tmp_path / "review.db"),
        transaction_store=transaction_store,
    )

    service = FraudScoringService(
        feature_engine=feature_engine,
        predictor=predictor,
        feature_builder=FraudModelFeatureBuilder(),
        risk_engine=risk_engine,
        review_queue=review_queue,
        transaction_store=transaction_store,
    )

    return (
        service,
        state_store,
        review_queue,
        transaction_store,
    )


def test_full_transaction_lifecycle(tmp_path):
    (
        service,
        state_store,
        review_queue,
        transaction_store,
    ) = create_system(tmp_path)

    # --------------------------------------------------
    # 1. First transaction: cold start
    # --------------------------------------------------

    result_1 = service.score_transaction(
        CanonicalTransaction(
            transaction_id="txn_001",
            entity_id="CARD_001",
            amount=50.0,
            category="grocery_pos",
            transaction_time=datetime(2020, 6, 21, 12, 0),
        )
    )

    assert result_1.prev_avg_amt is None
    assert result_1.prev_5_avg_amt is None
    assert result_1.amt_ratio_recent5 is None
    assert result_1.action == "APPROVE"
    assert result_1.risk_level == "LOW_RISK"
    assert result_1.model_decision == "LEGITIMATE"

    # --------------------------------------------------
    # 2. Second transaction: historical features exist
    # --------------------------------------------------

    result_2 = service.score_transaction(
        CanonicalTransaction(
            transaction_id="txn_002",
            entity_id="CARD_001",
            amount=55.0,
            category="grocery_pos",
            transaction_time=datetime(2020, 6, 21, 13, 0),
        )
    )

    assert result_2.prev_avg_amt == 50.0
    assert result_2.prev_5_avg_amt == 50.0
    assert result_2.amt_ratio_recent5 == 1.1

    # --------------------------------------------------
    # 3. Extreme transaction: high-risk HOLD
    # --------------------------------------------------

    result_3 = service.score_transaction(
        CanonicalTransaction(
            transaction_id="txn_003",
            entity_id="CARD_001",
            amount=5000.0,
            category="grocery_pos",
            transaction_time=datetime(2020, 6, 21, 14, 0),
        )
    )

    assert result_3.prev_avg_amt == 52.5
    assert result_3.prev_5_avg_amt == 52.5
    assert result_3.amt_ratio_recent5 == 5000.0 / 52.5

    assert result_3.action == "HOLD"
    assert result_3.risk_level == "HIGH_RISK"

    # --------------------------------------------------
    # 4. HOLD transactions do NOT enter review queue
    # --------------------------------------------------

    pending = review_queue.get_pending_reviews()

    assert pending == []

    # --------------------------------------------------
    # 5. Verify transaction persistence
    # --------------------------------------------------

    stored = transaction_store.get_transaction("txn_003")

    assert stored is not None
    assert stored["transaction_id"] == "txn_003"
    assert stored["amount"] == 5000.0
    assert stored["action"] == "HOLD"
    assert stored["risk_level"] == "HIGH_RISK"

    # --------------------------------------------------
    # 6. Verify historical state was updated exactly once
    # --------------------------------------------------

    state = state_store.get_entity("CARD_001")

    assert state is not None
    assert state["transaction_count"] == 3
    assert state["total_amount"] == 5105.0
    assert state["avg_amount"] == 5105.0 / 3


def test_human_review_lifecycle_and_ground_truth(tmp_path):
    (
        service,
        state_store,
        review_queue,
        transaction_store,
    ) = create_system(tmp_path)
    
    service.predictor = FixedProbabilityPredictor( 
        probabilities=[0.10, 0.60]
    )


    # --------------------------------------------------
    # 1. Establish card history
    # --------------------------------------------------

    service.score_transaction(
        CanonicalTransaction(
            transaction_id="txn_history_001",
            entity_id="CARD_001",
            amount=50.0,
            category="grocery_pos",
            transaction_time=datetime(2020, 6, 21, 12, 0),
        )
    )

    # --------------------------------------------------
    # 2. Create transaction that should enter HUMAN_REVIEW
    #
    # This mirrors the known behavioral-anomaly scenario:
    # large deviation + late-night transaction.
    # --------------------------------------------------

    result = service.score_transaction(
        CanonicalTransaction(
            transaction_id="txn_review_001",
            entity_id="CARD_001",
            amount=5000.0,
            category="grocery_pos",
            transaction_time=datetime(2020, 6, 21, 23, 0),
        )
    )

    assert result.action == "HUMAN_REVIEW"
    assert result.risk_level == "REVIEW"

    # --------------------------------------------------
    # 3. Verify review was created
    # --------------------------------------------------

    pending = review_queue.get_pending_reviews()

    assert len(pending) == 1

    review = pending[0]

    assert review["transaction_id"] == "txn_review_001"
    assert review["status"] == "PENDING"

    # --------------------------------------------------
    # 4. Verify transaction exists before resolution
    # --------------------------------------------------

    stored_before = transaction_store.get_transaction(
        "txn_review_001"
    )

    assert stored_before is not None
    assert stored_before["actual_outcome"] is None
    assert stored_before["outcome_source"] is None
    assert stored_before["outcome_reason"] is None

    # --------------------------------------------------
    # 5. Resolve review as confirmed fraud
    # --------------------------------------------------

    resolved = review_queue.resolve_review(
        transaction_id="txn_review_001",
        analyst_decision="CONFIRMED_FRAUD",
        analyst_reason="Manual investigation confirmed fraud.",
    )

    assert resolved is not None
    assert resolved["status"] == "RESOLVED"
    assert resolved["analyst_decision"] == "CONFIRMED_FRAUD"
    assert (
        resolved["analyst_reason"]
        == "Manual investigation confirmed fraud."
    )

    # --------------------------------------------------
    # 6. Verify ground truth was recorded
    # --------------------------------------------------

    stored_after = transaction_store.get_transaction(
        "txn_review_001"
    )

    assert stored_after is not None
    assert stored_after["actual_outcome"] == "FRAUD"
    assert stored_after["outcome_source"] == "analyst_review"
    assert (
        stored_after["outcome_reason"]
        == "Manual investigation confirmed fraud."
    )
    assert stored_after["outcome_at"] is not None

    # --------------------------------------------------
    # 7. Original model prediction must remain unchanged
    # --------------------------------------------------

    assert (
        stored_after["model_decision"]
        == result.model_decision
    )

    assert (
        stored_after["fraud_probability"]
        == result.fraud_probability
    )

    # --------------------------------------------------
    # 8. Review queue should now be empty
    # --------------------------------------------------

    pending_after = review_queue.get_pending_reviews()

    assert pending_after == []


def test_duplicate_transaction_is_idempotent(tmp_path):
    (
        service,
        state_store,
        review_queue,
        transaction_store,
    ) = create_system(tmp_path)

    transaction = CanonicalTransaction(
        transaction_id="txn_duplicate_001",
        entity_id="CARD_001",
        amount=50.0,
        category="grocery_pos",
        transaction_time=datetime(2020, 6, 21, 12, 0),
    )

    # --------------------------------------------------
    # 1. First scoring
    # --------------------------------------------------

    result_1 = service.score_transaction(transaction)

    # --------------------------------------------------
    # 2. Same transaction submitted again
    # --------------------------------------------------

    result_2 = service.score_transaction(transaction)

    # --------------------------------------------------
    # 3. Results must be identical
    # --------------------------------------------------

    assert result_2.transaction_id == result_1.transaction_id
    assert result_2.fraud_probability == result_1.fraud_probability
    assert result_2.model_decision == result_1.model_decision
    assert result_2.risk_level == result_1.risk_level
    assert result_2.action == result_1.action
    assert result_2.reasons == result_1.reasons

    # --------------------------------------------------
    # 4. Card state must only be updated once
    # --------------------------------------------------

    state = state_store.get_entity("CARD_001")

    assert state is not None
    assert state["transaction_count"] == 1
    assert state["total_amount"] == 50.0

    # --------------------------------------------------
    # 5. Only one transaction should exist
    # --------------------------------------------------

    stored = transaction_store.get_transaction(
        "txn_duplicate_001"
    )

    assert stored is not None
    assert stored["transaction_id"] == "txn_duplicate_001"