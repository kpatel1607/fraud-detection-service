from __future__ import annotations

import json
from dataclasses import dataclass

from src.features.state_store import EntityStateStore
from datetime import datetime


@dataclass
class HistoricalFeatures:
    """
    Historical features required by the fraud model.
    """

    prev_avg_amt: float | None
    prev_5_avg_amt: float | None
    amt_ratio_recent5: float | None


class HistoricalFeatureEngine:
    """
    Calculates card-level historical features using only
    information available BEFORE the current transaction.
    """

    def __init__(self, state_store: EntityStateStore) -> None:
        self.state_store = state_store

    def calculate(
        self,
        entity_id: str,
        current_amount: float,
    ) -> HistoricalFeatures:
        """
        Calculate historical features from the current card state.

        This method does NOT update the state.
        """

        state = self.state_store.get_entity(entity_id)

        # No previous transactions for this card.
        if state is None:
            return HistoricalFeatures(
                prev_avg_amt=None,
                prev_5_avg_amt=None,
                amt_ratio_recent5=None,
            )

        # Lifetime historical average.
        prev_avg_amt = state["avg_amount"]

        # Recent transaction amounts.
        recent_amounts = json.loads(
            state["recent_amounts"]
        )

        if recent_amounts:
            prev_5_avg_amt = (
                sum(recent_amounts)
                / len(recent_amounts)
            )
        else:
            prev_5_avg_amt = None

        # Current amount relative to recent behavior.
        if (
            prev_5_avg_amt is not None
            and prev_5_avg_amt > 0
        ):
            amt_ratio_recent5 = (
                current_amount / prev_5_avg_amt
            )
        else:
            amt_ratio_recent5 = None

        return HistoricalFeatures(
            prev_avg_amt=prev_avg_amt,
            prev_5_avg_amt=prev_5_avg_amt,
            amt_ratio_recent5=amt_ratio_recent5,
        )

    def update(
        self,
        entity_id: str,
        amount: float,
        transaction_time: datetime,
    ) -> None:
        """
        Update card state AFTER the transaction has been scored.
        """

        state = self.state_store.get_entity(entity_id)

        # First transaction for this card.
        if state is None:

            recent_amounts = [amount]

            self.state_store.upsert_entity(
                entity_id=entity_id,
                transaction_count=1,
                total_amount=amount,
                avg_amount=amount,
                recent_amounts=json.dumps(
                    recent_amounts
                ),
                last_transaction_time=(
                    transaction_time.isoformat()
                ),
            )

            return

        # Existing card state.
        transaction_count = (
            state["transaction_count"] + 1
        )

        total_amount = (
            state["total_amount"] + amount
        )

        avg_amount = (
            total_amount / transaction_count
        )

        recent_amounts = json.loads(
            state["recent_amounts"]
        )

        recent_amounts.append(amount)

        # Keep only the most recent 5 transactions.
        recent_amounts = recent_amounts[-5:]

        self.state_store.upsert_entity(
            entity_id=entity_id,
            transaction_count=transaction_count,
            total_amount=total_amount,
            avg_amount=avg_amount,
            recent_amounts=json.dumps(
                recent_amounts
            ),
            last_transaction_time=(
                transaction_time.isoformat()
            ),
        )