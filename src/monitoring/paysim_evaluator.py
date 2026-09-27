from __future__ import annotations

from src.monitoring.metrics import (
    ClassificationMetrics,
    calculate_metrics,
)
from src.monitoring.outcomes import classify_outcome
from src.storage.paysim_transaction_store import (
    PaySimTransactionStore,
)


class PaySimTransactionEvaluator:
    """
    Evaluates persisted PaySim predictions against known
    ground-truth outcomes.
    """

    def __init__(
        self,
        transaction_store: PaySimTransactionStore,
    ) -> None:
        self.transaction_store = transaction_store

    def evaluate(self) -> ClassificationMetrics:
        transactions = (
            self.transaction_store.get_evaluated_transactions()
        )

        true_positives = 0
        true_negatives = 0
        false_positives = 0
        false_negatives = 0

        for transaction in transactions:
            outcome = classify_outcome(
                predicted=transaction["model_decision"],
                actual=transaction["actual_outcome"],
            )

            if outcome.label == "TP":
                true_positives += 1

            elif outcome.label == "TN":
                true_negatives += 1

            elif outcome.label == "FP":
                false_positives += 1

            elif outcome.label == "FN":
                false_negatives += 1

        return calculate_metrics(
            true_positives=true_positives,
            true_negatives=true_negatives,
            false_positives=false_positives,
            false_negatives=false_negatives,
        )