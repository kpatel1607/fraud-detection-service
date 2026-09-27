from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.domain.paysim_transaction import PaySimTransaction
from src.model.paysim_predictor import PaySimFraudPredictor
from src.review.paysim_review import PaySimReview
from src.review.paysim_review_queue import PaySimReviewQueue
from src.rules.paysim_risk_policy import PaySimRiskPolicy
from src.storage.paysim_transaction_store import (
    PaySimTransactionStore,
)


@dataclass(frozen=True)
class PaySimScoreResult:
    transaction_id: str
    fraud_probability: float
    model_decision: str
    risk_level: str
    action: str

    @classmethod
    def from_stored_transaction(
        cls,
        transaction: dict,
    ) -> "PaySimScoreResult":
        return cls(
            transaction_id=transaction["transaction_id"],
            fraud_probability=transaction["fraud_probability"],
            model_decision=transaction["model_decision"],
            risk_level=transaction["risk_level"],
            action=transaction["action"],
        )


class PaySimScoringService:
    """
    Scores PaySim transactions using the PaySim-specific model
    and operational risk policy.

    Every scored transaction is persisted so that its prediction
    can later be evaluated against a known ground-truth outcome.
    """

    def __init__(
        self,
        predictor: PaySimFraudPredictor | None = None,
        risk_policy: PaySimRiskPolicy | None = None,
        review_queue: PaySimReviewQueue | None = None,
        transaction_store: PaySimTransactionStore | None = None,
    ) -> None:
        self.predictor = predictor or PaySimFraudPredictor()
        self.risk_policy = risk_policy or PaySimRiskPolicy()
        self.review_queue = review_queue or PaySimReviewQueue()
        self.transaction_store = (
            transaction_store or PaySimTransactionStore()
        )

    def score(
        self,
        transaction: PaySimTransaction,
    ) -> PaySimScoreResult:

        # ----------------------------------------------------
        # 1. Idempotency check
        # ----------------------------------------------------
        existing_transaction = (
            self.transaction_store.get_transaction(
                transaction.transaction_id
            )
        )

        if existing_transaction is not None:
            return PaySimScoreResult.from_stored_transaction(
                existing_transaction
            )

        # ----------------------------------------------------
        # 2. ML prediction
        # ----------------------------------------------------
        fraud_probability = (
            self.predictor.predict_probability(
                transaction
            )
        )

        # ----------------------------------------------------
        # 3. ML-only classification
        # ----------------------------------------------------
        model_decision = (
            "FRAUD"
            if fraud_probability >= 0.50
            else "LEGITIMATE"
        )

        # ----------------------------------------------------
        # 4. Apply operational risk policy
        # ----------------------------------------------------
        risk_assessment = self.risk_policy.assess(
            fraud_probability=fraud_probability,
        )

        # ----------------------------------------------------
        # 5. Add human-review cases to queue
        # ----------------------------------------------------
        if risk_assessment.action == "HUMAN_REVIEW":
            review = PaySimReview(
                transaction_id=transaction.transaction_id,
                transaction_type=transaction.transaction_type,
                amount=transaction.amount,
                oldbalance_org=transaction.oldbalance_org,
                oldbalance_dest=transaction.oldbalance_dest,
                fraud_probability=fraud_probability,
                model_decision=model_decision,
                risk_level=risk_assessment.risk_level,
                action=risk_assessment.action,
            )

            self.review_queue.add_review(review)

        # ----------------------------------------------------
        # 6. Build result
        # ----------------------------------------------------
        result = PaySimScoreResult(
            transaction_id=transaction.transaction_id,
            fraud_probability=fraud_probability,
            model_decision=model_decision,
            risk_level=risk_assessment.risk_level,
            action=risk_assessment.action,
        )

        # ----------------------------------------------------
        # 7. Persist every scored transaction
        # ----------------------------------------------------
        self.transaction_store.save_transaction(
            transaction_id=result.transaction_id,
            transaction_type=transaction.transaction_type,
            amount=transaction.amount,
            oldbalance_org=transaction.oldbalance_org,
            oldbalance_dest=transaction.oldbalance_dest,
            fraud_probability=result.fraud_probability,
            model_decision=result.model_decision,
            risk_level=result.risk_level,
            action=result.action,
            created_at=datetime.now().isoformat(),
        )

        return result