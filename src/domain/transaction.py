from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CanonicalTransaction:
    transaction_id: str
    entity_id: str
    amount: float
    category: str
    transaction_time: datetime

    def __post_init__(self) -> None:
        if not self.transaction_id.strip():
            raise ValueError("transaction_id cannot be empty.")

        if not self.entity_id.strip():
            raise ValueError("card_id cannot be empty.")

        if self.amount <= 0:
            raise ValueError("amount must be greater than zero.")

        if not self.category.strip():
            raise ValueError("category cannot be empty.")