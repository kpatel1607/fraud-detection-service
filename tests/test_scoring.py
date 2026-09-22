from datetime import datetime

from src.model.feature_builder import FraudModelFeatureBuilder
from src.features.canonical import CanonicalFeatureEngine
from src.features.historical import HistoricalFeatureEngine
from src.features.state_store import CardStateStore
from src.model.predictor import FraudPredictor
from src.review.review_queue import ReviewQueue
from src.rules.risk_engine import RiskEngine
from src.services.fraud_scoring import FraudScoringService
from src.domain.transaction import CanonicalTransaction
from src.storage.transaction_store import TransactionStore


def create_scoring_service(tmp_path):
    state_store = CardStateStore(
        db_path=str(tmp_path / "state.db")
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
        db_path=str(tmp_path / "review.db")
    )

    transaction_store = TransactionStore(
        db_path=str(tmp_path / "transactions.db")
    )

    service = FraudScoringService(
        feature_engine=feature_engine,
        predictor=predictor,
        feature_builder=FraudModelFeatureBuilder(),
        risk_engine=risk_engine,
        review_queue=review_queue,
        transaction_store=transaction_store,
    )

    return service, state_store


def test_cold_start_transaction(tmp_path):
    service, state_store = create_scoring_service(tmp_path)

    result = service.score_transaction(
        CanonicalTransaction(
            transaction_id="txn_001",
            entity_id="CARD_001",
            amount=50.0,
            category="grocery_pos",
            transaction_time=datetime(2020, 6, 21, 12, 0),
        )
    )

    assert result.prev_avg_amt is None
    assert result.prev_5_avg_amt is None
    assert result.amt_ratio_recent5 is None

    state = state_store.get_entity("CARD_001")

    assert state["transaction_count"] == 1
    assert state["total_amount"] == 50.0


def test_historical_features_use_previous_transactions(tmp_path):
    service, state_store = create_scoring_service(tmp_path)

    service.score_transaction(
        CanonicalTransaction(
            transaction_id="txn_001",
            entity_id="CARD_001",
            amount=50.0,
            category="grocery_pos",
            transaction_time=datetime(2020, 6, 21, 12, 0),
        )
    )

    result = service.score_transaction(
        CanonicalTransaction(
            transaction_id="txn_002",
            entity_id="CARD_001",
            amount=55.0,
            category="grocery_pos",
            transaction_time=datetime(2020, 6, 21, 13, 0),
        )
    )
    

    assert result.prev_avg_amt == 50.0
    assert result.prev_5_avg_amt == 50.0
    assert result.amt_ratio_recent5 == 1.1
    
    state = state_store.get_entity("CARD_001")

    assert state["transaction_count"] == 2
    assert state["total_amount"] == 105.0


def test_extreme_behavioral_anomaly_is_sent_to_review(tmp_path):
    service, state_store = create_scoring_service(tmp_path)

    service.score_transaction(
        CanonicalTransaction(
            transaction_id="txn_001",
            entity_id="CARD_001",
            amount=50.0,
            category="grocery_pos",
            transaction_time=datetime(2020, 6, 21, 12, 0),
        )
    )

    result = service.score_transaction(
        CanonicalTransaction(
            transaction_id="txn_002",
            entity_id="CARD_001",
            amount=5000.0,
            category="grocery_pos",
            transaction_time=datetime(2020, 6, 21, 23, 0),
        )
    )

    assert result.amt_ratio_recent5 == 100.0
    assert result.action == "HOLD"
    assert result.risk_level == "HIGH_RISK"
    
    state = state_store.get_entity("CARD_001")

    assert state["transaction_count"] == 2
    assert state["total_amount"] == 5050.0


def test_duplicate_transaction_is_idempotent(tmp_path):
    service, state_store = create_scoring_service(tmp_path)

    first = service.score_transaction(
        CanonicalTransaction(
            transaction_id="txn_001",
            entity_id="CARD_001",
            amount=50.0,
            category="grocery_pos",
            transaction_time=datetime(2020, 6, 21, 12, 0),
        )
    )

    second = service.score_transaction(
        CanonicalTransaction(
            transaction_id="txn_001",
            entity_id="CARD_001",
            amount=50.0,
            category="grocery_pos",
            transaction_time=datetime(2020, 6, 21, 12, 0),
        )
    )

    assert second == first

    state = state_store.get_entity("CARD_001")

    assert state["transaction_count"] == 1
    assert state["total_amount"] == 50.0
    assert state["recent_amounts"] == "[50.0]"