from __future__ import annotations

from src.domain.transaction import CanonicalTransaction
from src.features.historical import HistoricalFeatures
from src.model.feature_registry import FeatureRegistry


def build_default_feature_registry() -> FeatureRegistry:
    """
    Build the feature registry for the currently deployed fraud model.
    """

    registry = FeatureRegistry()

    registry.register(
        "amt",
        lambda transaction, historical: transaction.amount,
    )

    registry.register(
        "hour",
        lambda transaction, historical: transaction.transaction_time.hour,
    )

    registry.register(
        "category",
        lambda transaction, historical: transaction.category,
    )

    registry.register(
        "prev_avg_amt",
        lambda transaction, historical: historical.prev_avg_amt,
    )

    registry.register(
        "prev_5_avg_amt",
        lambda transaction, historical: historical.prev_5_avg_amt,
    )

    registry.register(
        "amt_ratio_recent5",
        lambda transaction, historical: historical.amt_ratio_recent5,
    )

    return registry