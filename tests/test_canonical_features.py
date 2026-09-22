from datetime import datetime

from src.domain.transaction import CanonicalTransaction
from src.features.canonical import CanonicalFeatureEngine
from src.features.historical import HistoricalFeatureEngine
from src.features.state_store import CardStateStore


def test_canonical_feature_engine_calculates_previous_state(
    tmp_path,
):
    state_store = CardStateStore(
        db_path=str(tmp_path / "state.db")
    )

    historical_engine = HistoricalFeatureEngine(
        state_store=state_store
    )

    feature_engine = CanonicalFeatureEngine(
        historical_engine=historical_engine
    )

    first_transaction = CanonicalTransaction(
        transaction_id="tx_001",
        entity_id="card_001",
        amount=100.0,
        category="grocery_pos",
        transaction_time=datetime.fromisoformat(
            "2020-06-21T12:00:00"
        ),
    )

    feature_engine.update(first_transaction)

    second_transaction = CanonicalTransaction(
        transaction_id="tx_002",
        entity_id="card_001",
        amount=200.0,
        category="shopping_net",
        transaction_time=datetime.fromisoformat(
            "2020-06-21T13:00:00"
        ),
    )

    features = feature_engine.calculate(
        second_transaction
    )

    assert features.prev_avg_amt == 100.0
    assert features.prev_5_avg_amt == 100.0
    assert features.amt_ratio_recent5 == 2.0