from datetime import datetime
import json

from src.domain.transaction import CanonicalTransaction
from src.features.historical import HistoricalFeatures
from src.model.feature_builder import FraudModelFeatureBuilder
from src.model.feature_registry import FeatureRegistry


def test_feature_builder_uses_model_metadata_contract(tmp_path):
    metadata_path = tmp_path / "metadata.json"

    metadata_path.write_text(
        json.dumps(
            {
                "features": [
                    "amt",
                    "hour",
                    "category",
                    "prev_avg_amt",
                    "prev_5_avg_amt",
                    "amt_ratio_recent5",
                ]
            }
        ),
        encoding="utf-8",
    )

    builder = FraudModelFeatureBuilder(
        metadata_path=str(metadata_path)
    )

    transaction = CanonicalTransaction(
        transaction_id="TX_001",
        entity_id="ENTITY_001",
        amount=500.0,
        category="shopping_net",
        transaction_time=datetime(2026, 9, 15, 23, 0),
    )

    historical = HistoricalFeatures(
        prev_avg_amt=100.0,
        prev_5_avg_amt=80.0,
        amt_ratio_recent5=6.25,
    )

    features = builder.build(
        transaction=transaction,
        historical=historical,
    )

    assert list(features.columns) == [
        "amt",
        "hour",
        "category",
        "prev_avg_amt",
        "prev_5_avg_amt",
        "amt_ratio_recent5",
    ]


def test_feature_builder_detects_missing_feature_contract(tmp_path):
    metadata_path = tmp_path / "metadata.json"

    metadata_path.write_text(
        json.dumps(
            {
                "features": [
                    "amt",
                    "hour",
                    "some_future_feature",
                ]
            }
        ),
        encoding="utf-8",
    )

    builder = FraudModelFeatureBuilder(
        metadata_path=str(metadata_path)
    )

    transaction = CanonicalTransaction(
        transaction_id="TX_002",
        entity_id="ENTITY_002",
        amount=500.0,
        category="shopping_net",
        transaction_time=datetime(2026, 9, 15, 23, 0),
    )

    historical = HistoricalFeatures(
        prev_avg_amt=100.0,
        prev_5_avg_amt=80.0,
        amt_ratio_recent5=6.25,
    )

    try:
        builder.build(
            transaction=transaction,
            historical=historical,
        )
    except ValueError as exc:
        assert "some_future_feature" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError for missing model feature."
        )
        
def test_feature_builder_accepts_custom_feature_registry(tmp_path):
    metadata_path = tmp_path / "metadata.json"

    metadata_path.write_text(
        """
        {
            "features": [
                "custom_amount",
                "custom_hour"
            ]
        }
        """,
        encoding="utf-8",
    )

    registry = FeatureRegistry()

    registry.register(
        "custom_amount",
        lambda transaction, historical: transaction.amount * 2,
    )

    registry.register(
        "custom_hour",
        lambda transaction, historical: transaction.transaction_time.hour + 1,
    )

    builder = FraudModelFeatureBuilder(
        metadata_path=str(metadata_path),
        feature_registry=registry,
    )

    transaction = CanonicalTransaction(
        transaction_id="TX_CUSTOM_001",
        entity_id="ENTITY_CUSTOM_001",
        amount=100.0,
        category="custom_category",
        transaction_time=datetime(2020, 6, 21, 22, 0),
    )

    historical = HistoricalFeatures(
        prev_avg_amt=None,
        prev_5_avg_amt=None,
        amt_ratio_recent5=None,
    )

    result = builder.build(
        transaction=transaction,
        historical=historical,
    )

    assert list(result.columns) == [
        "custom_amount",
        "custom_hour",
    ]

    assert result.iloc[0]["custom_amount"] == 200.0
    assert result.iloc[0]["custom_hour"] == 23