import json
import time
import uuid

from fastapi import FastAPI, HTTPException, Request, Depends

from src.logging_config import configure_logging, get_logger
from src.config import Settings

from src.monitoring.evaluator import TransactionEvaluator

from src.api.security import create_api_key_dependency
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from src.api.schemas import (
    ScoreRequest,
    ScoreResponse,
    ReviewResponse,
    ResolveReviewRequest,
    MetricsResponse,
)
from src.features.historical import HistoricalFeatureEngine
from src.features.state_store import CardStateStore
from src.model.predictor import FraudPredictor
from src.review.review_queue import ReviewQueue
from src.rules.risk_engine import RiskEngine
from src.services.fraud_scoring import FraudScoringService
from src.model.feature_builder import FraudModelFeatureBuilder
from src.storage.transaction_store import TransactionStore
from src.domain.transaction import CanonicalTransaction
from src.features.canonical import CanonicalFeatureEngine


def create_app(
    settings: Settings | None = None,
) -> FastAPI:

    if settings is None:
        settings = Settings()

    api_key_dependency = create_api_key_dependency(
        settings.api_key
    )

    configure_logging(settings)
    logger = get_logger(__name__)

    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        description=settings.api_description,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )
    
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_host_list,
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["X-API-Key", "Content-Type"],
    )

    # --------------------------------------------------
    # System dependencies
    # --------------------------------------------------

    state_store = CardStateStore(
        db_path=settings.state_db_path
    )

    transaction_store = TransactionStore(
        db_path=settings.transaction_db_path
    )
    
    evaluator = TransactionEvaluator(
        transaction_store=transaction_store
    )

    historical_engine = HistoricalFeatureEngine(
        state_store=state_store
    )

    feature_engine = CanonicalFeatureEngine(
        historical_engine=historical_engine
    )

    predictor = FraudPredictor(
        preprocessor_path=settings.preprocessor_path,
        model_path=settings.model_path,
    )

    risk_engine = RiskEngine(
        review_threshold=settings.review_threshold,
        high_risk_threshold=settings.high_risk_threshold,
        late_night_hours=settings.late_night_hour_set,
        elevated_fraud_categories=settings.elevated_fraud_category_set,
    )

    review_queue = ReviewQueue(
        db_path=settings.review_db_path,
        transaction_store=transaction_store,
    )

    fraud_service = FraudScoringService(
        feature_engine=feature_engine,
        predictor=predictor,
        feature_builder=FraudModelFeatureBuilder(),
        risk_engine=risk_engine,
        review_queue=review_queue,
        transaction_store=transaction_store,
    )

    # --------------------------------------------------
    # Routes
    # --------------------------------------------------
    
    @app.middleware("http")
    async def request_logging_middleware(
        request: Request,
        call_next,
    ):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.perf_counter()

        logger.info(
            "request_started request_id=%s method=%s path=%s",
            request_id,
            request.method,
            request.url.path,
        )

        try:
            response = await call_next(request)

            elapsed_ms = (
                time.perf_counter() - start_time
            ) * 1000

            response.headers["X-Request-ID"] = request_id

            logger.info(
                "request_completed request_id=%s "
                "status_code=%s latency_ms=%.2f",
                request_id,
                response.status_code,
                elapsed_ms,
            )

            return response

        except Exception:
            elapsed_ms = (
                time.perf_counter() - start_time
            ) * 1000

            logger.exception(
                "request_failed request_id=%s "
                "method=%s path=%s latency_ms=%.2f",
                request_id,
                request.method,
                request.url.path,
                elapsed_ms,
            )

            raise

    @app.get("/health")
    def health_check():
        return {
            "status": "ok",
            "service": "fraud-detection-api",
            "model_version": settings.model_version,
        }

    @app.post(
        "/score",
        response_model=ScoreResponse,
        dependencies=[Depends(api_key_dependency)],
    )
    def score_transaction(
        request: Request,
        payload: ScoreRequest,
    ):
        try:
            transaction = CanonicalTransaction(
                transaction_id=payload.transaction_id,
                entity_id=payload.entity_id,
                amount=payload.amount,
                category=payload.category,
                transaction_time=payload.transaction_time,
            )

            result = fraud_service.score_transaction(transaction)

            logger.info(
                "transaction_scored "
                "request_id=%s transaction_id=%s "
                "probability=%.6f model_decision=%s "
                "risk_level=%s action=%s",
                request.state.request_id,
                payload.transaction_id,
                result.fraud_probability,
                result.model_decision,
                result.risk_level,
                result.action,
            )

            return ScoreResponse(
                transaction_id=result.transaction_id,
                fraud_probability=result.fraud_probability,
                model_decision=result.model_decision,
                risk_level=result.risk_level,
                action=result.action,
                reasons=result.reasons,
                amount=result.amt,
                hour=result.hour,
                category=result.category,
                prev_avg_amt=result.prev_avg_amt,
                prev_5_avg_amt=result.prev_5_avg_amt,
                amt_ratio_recent5=result.amt_ratio_recent5,
            )

        except ValueError as exc:
            logger.warning(
                "transaction_validation_error "
                "request_id=%s transaction_id=%s error=%s",
                request.state.request_id,
                payload.transaction_id,
                str(exc),
            )

            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

        except Exception:
            logger.exception(
                "transaction_scoring_error "
                "request_id=%s transaction_id=%s",
                request.state.request_id,
                payload.transaction_id,
            )

            raise HTTPException(
                status_code=500,
                detail="Internal fraud scoring error.",
            )

    def review_to_response(review: dict) -> ReviewResponse:
        try:
            reasons = json.loads(review["reasons"])
        except (TypeError, json.JSONDecodeError):
            reasons = []

        return ReviewResponse(
            review_id=review["review_id"],
            transaction_id=review["transaction_id"],
            entity_id=review["entity_id"],
            amount=review["amount"],
            category=review["category"],
            transaction_time=review["transaction_time"],
            fraud_probability=review["fraud_probability"],
            risk_level=review["risk_level"],
            action=review["action"],
            prev_avg_amt=review["prev_avg_amt"],
            prev_5_avg_amt=review["prev_5_avg_amt"],
            amt_ratio_recent5=review["amt_ratio_recent5"],
            reasons=reasons,
            status=review["status"],
            analyst_decision=review["analyst_decision"],
            analyst_reason=review["analyst_reason"],
            created_at=review["created_at"],
            reviewed_at=review["reviewed_at"],
        )

    @app.get(
        "/reviews/pending",
        response_model=list[ReviewResponse],
        dependencies=[Depends(api_key_dependency)],
    )
    def get_pending_reviews():
        reviews = review_queue.get_pending_reviews()

        return [
            review_to_response(review)
            for review in reviews
        ]

    @app.post(
        "/reviews/{transaction_id}/resolve",
        response_model=ReviewResponse,
        dependencies=[Depends(api_key_dependency)],
    )
    def resolve_review(
        transaction_id: str,
        request: Request,
        payload: ResolveReviewRequest,
    ):
        try:
            review = review_queue.resolve_review(
                transaction_id=transaction_id,
                analyst_decision=payload.analyst_decision,
                analyst_reason=payload.analyst_reason,
            )

            if review is None:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        f"No review found for "
                        f"transaction_id={transaction_id}"
                    ),
                )

            logger.info(
                "review_resolved "
                "request_id=%s transaction_id=%s "
                "analyst_decision=%s",
                request.state.request_id,
                transaction_id,
                payload.analyst_decision,
            )

            return review_to_response(review)

        except HTTPException:
            raise

        except ValueError as exc:
            logger.warning(
                "review_validation_error "
                "request_id=%s transaction_id=%s error=%s",
                request.state.request_id,
                transaction_id,
                str(exc),
            )

            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

        except Exception:
            logger.exception(
                "review_resolution_error "
                "request_id=%s transaction_id=%s",
                request.state.request_id,
                transaction_id,
            )

            raise HTTPException(
                status_code=500,
                detail="Internal review resolution error.",
            )
            
    @app.get(
        "/monitoring/metrics",
        response_model=MetricsResponse,
        dependencies=[Depends(api_key_dependency)],
    )
    def get_monitoring_metrics():
        metrics = evaluator.evaluate()

        evaluated_transactions = (
            metrics.true_positives
            + metrics.true_negatives
            + metrics.false_positives
            + metrics.false_negatives
        )

        return MetricsResponse(
            evaluated_transactions=evaluated_transactions,
            true_positives=metrics.true_positives,
            true_negatives=metrics.true_negatives,
            false_positives=metrics.false_positives,
            false_negatives=metrics.false_negatives,
            precision=metrics.precision,
            recall=metrics.recall,
            f1_score=metrics.f1_score,
            accuracy=metrics.accuracy,
        )

    return app

# Production application
app = create_app()