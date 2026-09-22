from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json

from src.domain.transaction import CanonicalTransaction
from src.features.canonical import CanonicalFeatureEngine
from src.model.predictor import FraudPredictor
from src.review.review_queue import ReviewQueue
from src.rules.risk_engine import RiskAssessment, RiskEngine
from src.storage.transaction_store import TransactionStore
from src.model.feature_builder import FraudModelFeatureBuilder


@dataclass
class FraudScoreResult:
    transaction_id: str
    fraud_probability: float
    model_decision: str
    risk_level: str
    action: str
    reasons: list[str]
    amt: float
    hour: int
    category: str
    prev_avg_amt: float | None
    prev_5_avg_amt: float | None
    amt_ratio_recent5: float | None

    @classmethod
    def from_stored_transaction(
        cls,
        transaction: dict,
    ) -> "FraudScoreResult":
        return cls(
            transaction_id=transaction["transaction_id"],
            fraud_probability=transaction["fraud_probability"],
            model_decision=transaction["model_decision"],
            risk_level=transaction["risk_level"],
            action=transaction["action"],
            reasons=json.loads(transaction["reasons"]),
            amt=transaction["amount"],
            hour=datetime.fromisoformat(
                transaction["transaction_time"]
            ).hour,
            category=transaction["category"],
            prev_avg_amt=transaction["prev_avg_amt"],
            prev_5_avg_amt=transaction["prev_5_avg_amt"],
            amt_ratio_recent5=transaction["amt_ratio_recent5"],
        )


class FraudScoringService:
    """
    Coordinates:

        CanonicalTransaction
            ↓
        Historical features
            ↓
        ML prediction
            ↓
        Risk policy
            ↓
        Review queue (if required)
            ↓
        Transaction persistence
            ↓
        Card state update

    The current transaction is always scored BEFORE
    it is added to historical state.
    """

    def __init__(
        self,
        feature_engine: CanonicalFeatureEngine,
        predictor: FraudPredictor,
        feature_builder: FraudModelFeatureBuilder,
        risk_engine: RiskEngine,
        review_queue: ReviewQueue,
        transaction_store: TransactionStore,
    ) -> None:
        self.feature_engine = feature_engine
        self.predictor = predictor
        self.feature_builder = feature_builder
        self.risk_engine = risk_engine
        self.review_queue = review_queue
        self.transaction_store = transaction_store

    def score_transaction(
        self,
        transaction: CanonicalTransaction,
    ) -> FraudScoreResult:

        # ----------------------------------------------------
        # 1. Idempotency check
        # ----------------------------------------------------
        existing_transaction = (
            self.transaction_store.get_transaction(
                transaction.transaction_id
            )
        )

        if existing_transaction is not None:
            return FraudScoreResult.from_stored_transaction(
                existing_transaction
            )

        # ----------------------------------------------------
        # 2. Extract hour
        # ----------------------------------------------------
        hour = transaction.transaction_time.hour

        historical = self.feature_engine.calculate(
            transaction
        )

        model_features = self.feature_builder.build(
            transaction=transaction,
            historical=historical,
        )

        # ----------------------------------------------------
        # 5. ML prediction
        # ----------------------------------------------------
        fraud_probability = (
            self.predictor.predict_probability(
                model_features
            )
        )

        # ----------------------------------------------------
        # 6. ML-only classification
        # ----------------------------------------------------
        model_decision = (
            "FRAUD"
            if fraud_probability >= 0.50
            else "LEGITIMATE"
        )

        # ----------------------------------------------------
        # 7. Apply operational risk policy
        # ----------------------------------------------------
        risk_assessment: RiskAssessment = (
            self.risk_engine.assess(
                fraud_probability=fraud_probability,
                amount=transaction.amount,
                hour=hour,
                category=transaction.category,
                prev_avg_amt=historical.prev_avg_amt,
                prev_5_avg_amt=historical.prev_5_avg_amt,
            )
        )

        # ----------------------------------------------------
        # 8. Add human-review cases to queue
        # ----------------------------------------------------
        if risk_assessment.action == "HUMAN_REVIEW":
            self.review_queue.add_review(
                transaction_id=transaction.transaction_id,
                entity_id=transaction.entity_id,
                amount=transaction.amount,
                category=transaction.category,
                transaction_time=(
                    transaction.transaction_time.isoformat()
                ),
                fraud_probability=fraud_probability,
                risk_level=risk_assessment.risk_level,
                action=risk_assessment.action,
                prev_avg_amt=historical.prev_avg_amt,
                prev_5_avg_amt=historical.prev_5_avg_amt,
                amt_ratio_recent5=(
                    historical.amt_ratio_recent5
                ),
                reasons=risk_assessment.reasons,
            )

        # ----------------------------------------------------
        # 9. Build complete result
        # ----------------------------------------------------
        result = FraudScoreResult(
            transaction_id=transaction.transaction_id,
            fraud_probability=fraud_probability,
            model_decision=model_decision,
            risk_level=risk_assessment.risk_level,
            action=risk_assessment.action,
            reasons=risk_assessment.reasons,
            amt=transaction.amount,
            hour=hour,
            category=transaction.category,
            prev_avg_amt=historical.prev_avg_amt,
            prev_5_avg_amt=historical.prev_5_avg_amt,
            amt_ratio_recent5=historical.amt_ratio_recent5,
        )

        # ----------------------------------------------------
        # 10. Persist scored transaction
        # ----------------------------------------------------
        self.transaction_store.save_transaction(
            transaction_id=result.transaction_id,
            entity_id=transaction.entity_id,
            amount=result.amt,
            category=result.category,
            transaction_time=(
                transaction.transaction_time.isoformat()
            ),
            fraud_probability=result.fraud_probability,
            model_decision=result.model_decision,
            risk_level=result.risk_level,
            action=result.action,
            reasons=result.reasons,
            prev_avg_amt=result.prev_avg_amt,
            prev_5_avg_amt=result.prev_5_avg_amt,
            amt_ratio_recent5=result.amt_ratio_recent5,
            created_at=datetime.now().isoformat(),
        )

        # ----------------------------------------------------
        # 11. Update card history AFTER scoring
        # ----------------------------------------------------
        self.feature_engine.update(transaction)

        return result