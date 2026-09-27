from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PaySimRiskAssessment:
    fraud_probability: float
    risk_level: str
    action: str


class PaySimRiskPolicy:
    """
    Converts a PaySim model score into an operational decision.

    PaySim has a highly separated score distribution, so its policy
    is intentionally independent of the card-model RiskEngine.
    """

    def __init__(
        self,
        review_threshold: float = 0.40,
        high_risk_threshold: float = 0.80,
    ) -> None:
        if not (
            0.0 < review_threshold < high_risk_threshold < 1.0
        ):
            raise ValueError(
                "Thresholds must satisfy: "
                "0 < review_threshold < high_risk_threshold < 1"
            )

        self.review_threshold = review_threshold
        self.high_risk_threshold = high_risk_threshold

    def assess(
        self,
        fraud_probability: float,
    ) -> PaySimRiskAssessment:

        if fraud_probability >= self.high_risk_threshold:
            risk_level = "HIGH_RISK"
            action = "HOLD"

        elif fraud_probability >= self.review_threshold:
            risk_level = "REVIEW"
            action = "HUMAN_REVIEW"

        else:
            risk_level = "LOW_RISK"
            action = "APPROVE"

        return PaySimRiskAssessment(
            fraud_probability=fraud_probability,
            risk_level=risk_level,
            action=action,
        )