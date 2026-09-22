from __future__ import annotations

from datetime import datetime

from src.domain.transaction import CanonicalTransaction


class KaggleFraudAdapter:
    """Maps the current Kaggle fraud dataset schema to the canonical schema."""

    @staticmethod
    def to_canonical_transaction(
        transaction: dict,
    ) -> CanonicalTransaction:
        required_fields = (
            "transaction_id",
            "cc_num",
            "amount",
            "category",
            "transaction_time",
        )

        missing_fields = [
            field
            for field in required_fields
            if field not in transaction
        ]

        if missing_fields:
            raise ValueError(
                "Missing required fields: "
                + ", ".join(missing_fields)
            )

        try:
            transaction_time = datetime.fromisoformat(
                transaction["transaction_time"]
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "transaction_time must be a valid ISO datetime."
            ) from exc

        return CanonicalTransaction(
            transaction_id=str(transaction["transaction_id"]),
            entity_id=str(transaction["cc_num"]),
            amount=float(transaction["amount"]),
            category=str(transaction["category"]),
            transaction_time=transaction_time,
        )