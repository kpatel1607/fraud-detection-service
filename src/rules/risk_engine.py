from __future__ import annotations

from dataclasses import dataclass, field

from src.rules.context_analyzer import ContextAnalyzer


@dataclass
class RiskAssessment:
    """
    Final operational assessment.
    """

    fraud_probability: float
    risk_level: str
    action: str
    reasons: list[str] = field(default_factory=list)


class RiskEngine:
    """
    Converts ML probability + contextual signals
    into an operational decision.

    ML probability is never modified.
    """

    def __init__(
        self,
        review_threshold: float = 0.40,
        high_risk_threshold: float = 0.80,
        late_night_hours: set[int] | None = None,
        elevated_fraud_categories: set[str] | None = None,
    ) -> None:
        if not (0.0 < review_threshold < high_risk_threshold < 1.0):
            raise ValueError(
                "Thresholds must satisfy: "
                "0 < review_threshold < high_risk_threshold < 1"
            )

        if late_night_hours is None:
            raise ValueError(
                "late_night_hours must be provided."
            )

        if elevated_fraud_categories is None:
            raise ValueError(
                "elevated_fraud_categories must be provided."
            )

        self.review_threshold = review_threshold
        self.high_risk_threshold = high_risk_threshold

        self.context_analyzer = ContextAnalyzer(
            late_night_hours=late_night_hours,
            elevated_fraud_categories=elevated_fraud_categories,
        )

    def assess(
        self,
        fraud_probability: float,
        amount: float,
        hour: int,
        category: str,
        prev_avg_amt: float | None,
        prev_5_avg_amt: float | None,
    ) -> RiskAssessment:

        # ----------------------------------------------------
        # 1. Base decision from ML probability
        # ----------------------------------------------------

        if fraud_probability >= self.high_risk_threshold:
            risk_level = "HIGH_RISK"
            action = "HOLD"

        elif fraud_probability >= self.review_threshold:
            risk_level = "REVIEW"
            action = "HUMAN_REVIEW"

        else:
            risk_level = "LOW_RISK"
            action = "APPROVE"

        # ----------------------------------------------------
        # 2. Analyze contextual behavior
        # ----------------------------------------------------

        signals = self.context_analyzer.analyze(
            amount=amount,
            hour=hour,
            category=category,
            prev_avg_amt=prev_avg_amt,
            prev_5_avg_amt=prev_5_avg_amt,
        )

        reasons = [
            signal.message
            for signal in signals
        ]

        # ----------------------------------------------------
        # 3. Escalate extreme contextual anomalies
        #
        # IMPORTANT:
        # We do not change fraud_probability.
        # We only change the operational action.
        # ----------------------------------------------------

        high_severity_signals = [
            signal
            for signal in signals
            if signal.severity == "HIGH"
        ]

        if (
            risk_level == "LOW_RISK"
            and high_severity_signals
        ):
            risk_level = "REVIEW"
            action = "HUMAN_REVIEW"

            reasons.insert(
                0,
                (
                    "Transaction was escalated because "
                    "an extreme behavioral anomaly was detected."
                )
            )

        return RiskAssessment(
            fraud_probability=fraud_probability,
            risk_level=risk_level,
            action=action,
            reasons=reasons,
        )