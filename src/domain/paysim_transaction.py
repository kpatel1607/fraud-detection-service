from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PaySimTransaction:
    """
    Domain representation of a PaySim transaction.

    This keeps PaySim-specific transaction semantics separate
    from the canonical card-transaction domain.
    """

    transaction_id: str
    transaction_type: str
    amount: float
    oldbalance_org: float
    oldbalance_dest: float

    def __post_init__(self) -> None:
        if not self.transaction_id.strip():
            raise ValueError(
                "transaction_id cannot be empty."
            )

        if not self.transaction_type.strip():
            raise ValueError(
                "transaction_type cannot be empty."
            )

        if self.amount < 0:
            raise ValueError(
                "amount cannot be negative."
            )

        if self.oldbalance_org < 0:
            raise ValueError(
                "oldbalance_org cannot be negative."
            )

        if self.oldbalance_dest < 0:
            raise ValueError(
                "oldbalance_dest cannot be negative."
            )