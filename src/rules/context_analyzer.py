from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ContextSignal:
    name: str
    severity: str
    message: str


class ContextAnalyzer:
    def __init__(
        self,
        late_night_hours: set[int],
        elevated_fraud_categories: set[str],
    ) -> None:
        self.late_night_hours = late_night_hours
        self.elevated_fraud_categories = elevated_fraud_categories

    def analyze(
        self,
        amount: float,
        hour: int,
        category: str,
        prev_avg_amt: float | None,
        prev_5_avg_amt: float | None,
    ) -> list[ContextSignal]:
        signals: list[ContextSignal] = []

        if prev_5_avg_amt is not None and prev_5_avg_amt > 0:
            recent_ratio = amount / prev_5_avg_amt

            if recent_ratio >= 20:
                signals.append(
                    ContextSignal(
                        name="EXTREME_RECENT_DEVIATION",
                        severity="HIGH",
                        message=(
                            f"Transaction amount is {recent_ratio:.1f}× "
                            "the card's recent 5-transaction average."
                        ),
                    )
                )

            elif recent_ratio >= 5:
                signals.append(
                    ContextSignal(
                        name="LARGE_RECENT_DEVIATION",
                        severity="MEDIUM",
                        message=(
                            f"Transaction amount is {recent_ratio:.1f}× "
                            "the card's recent 5-transaction average."
                        ),
                    )
                )

        if prev_avg_amt is not None and prev_avg_amt > 0:
            lifetime_ratio = amount / prev_avg_amt

            if lifetime_ratio >= 20:
                signals.append(
                    ContextSignal(
                        name="EXTREME_LIFETIME_DEVIATION",
                        severity="HIGH",
                        message=(
                            f"Transaction amount is {lifetime_ratio:.1f}× "
                            "the card's historical average."
                        ),
                    )
                )

            elif lifetime_ratio >= 5:
                signals.append(
                    ContextSignal(
                        name="LARGE_LIFETIME_DEVIATION",
                        severity="MEDIUM",
                        message=(
                            f"Transaction amount is {lifetime_ratio:.1f}× "
                            "the card's historical average."
                        ),
                    )
                )

        if hour in self.late_night_hours:
            signals.append(
                ContextSignal(
                    name="LATE_NIGHT_TRANSACTION",
                    severity="MEDIUM",
                    message="Transaction occurred during a late-night period.",
                )
            )

        if category in self.elevated_fraud_categories:
            signals.append(
                ContextSignal(
                    name="ELEVATED_FRAUD_CATEGORY",
                    severity="LOW",
                    message=(
                        f"Transaction category '{category}' has historically "
                        "elevated fraud rates in this dataset."
                    ),
                )
            )

        return signals