from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class PaySimReview:
    """
    Represents a PaySim transaction requiring human review.
    """

    transaction_id: str
    transaction_type: str
    amount: float
    oldbalance_org: float
    oldbalance_dest: float

    fraud_probability: float
    model_decision: str
    risk_level: str
    action: str

    status: str = "PENDING"
    actual_outcome: str | None = None
    reviewed_at: datetime | None = None

    def resolve(self, actual_outcome: str) -> None:
        if self.status != "PENDING":
            raise ValueError(
                "Only pending PaySim reviews can be resolved."
            )

        if actual_outcome not in {"FRAUD", "LEGITIMATE"}:
            raise ValueError(
                "actual_outcome must be FRAUD or LEGITIMATE."
            )

        self.actual_outcome = actual_outcome
        self.status = "RESOLVED"
        self.reviewed_at = datetime.utcnow()