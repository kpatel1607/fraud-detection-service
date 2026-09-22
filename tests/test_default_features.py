from datetime import datetime

from src.domain.transaction import CanonicalTransaction
from src.features.historical import HistoricalFeatures
from src.model.default_features import build_default_feature_registry


def test_default_feature_registry_builds_expected_features():
    registry = build_default_feature_registry()

    transaction = CanonicalTransaction(
        transaction_id="TX_TEST_001",
        entity_id="ENTITY_TEST_001",
        amount=500.0,
        category="shopping_net",
        transaction_time=datetime(2020, 6, 21, 23, 15),
    )

    historical = HistoricalFeatures(
        prev_avg_amt=100.0,
        prev_5_avg_amt=50.0,
        amt_ratio_recent5=10.0,
    )

    expected_values = {
        "amt": 500.0,
        "hour": 23,
        "category": "shopping_net",
        "prev_avg_amt": 100.0,
        "prev_5_avg_amt": 50.0,
        "amt_ratio_recent5": 10.0,
    }

    for feature_name, expected_value in expected_values.items():
        provider = registry.get(feature_name)

        assert provider is not None
        assert provider(transaction, historical) == expected_value