from __future__ import annotations

from src.domain.transaction import CanonicalTransaction
from src.features.historical import HistoricalFeatureEngine


class CanonicalFeatureEngine:
    """
    Adapts canonical transactions to the existing
    historical feature engine.
    """

    def __init__(
        self,
        historical_engine: HistoricalFeatureEngine,
    ) -> None:
        self.historical_engine = historical_engine

    def calculate(
        self,
        transaction: CanonicalTransaction,
    ):
        return self.historical_engine.calculate(
            entity_id=transaction.entity_id,
            current_amount=transaction.amount,
        )

    def update(
        self,
        transaction: CanonicalTransaction,
    ) -> None:
        self.historical_engine.update(
            entity_id=transaction.entity_id,
            amount=transaction.amount,
            transaction_time=transaction.transaction_time,
        )