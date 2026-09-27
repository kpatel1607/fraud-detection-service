from datetime import datetime

from pydantic import BaseModel, Field
from typing import Literal


class ScoreRequest(BaseModel):
    transaction_id: str = Field(min_length=1)
    entity_id: str = Field(min_length=1)
    amount: float = Field(gt=0)
    category: str = Field(min_length=1)
    transaction_time: datetime


class ScoreResponse(BaseModel):
    transaction_id: str

    fraud_probability: float
    model_decision: str

    risk_level: str
    action: str
    reasons: list[str]

    amount: float
    hour: int
    category: str

    prev_avg_amt: float | None
    prev_5_avg_amt: float | None
    amt_ratio_recent5: float | None
    
class ReviewResponse(BaseModel):
    review_id: int
    transaction_id: str
    entity_id: str

    amount: float
    category: str
    transaction_time: datetime

    fraud_probability: float
    risk_level: str
    action: str

    prev_avg_amt: float | None
    prev_5_avg_amt: float | None
    amt_ratio_recent5: float | None

    reasons: list[str]

    status: str
    analyst_decision: str | None
    analyst_reason: str | None

    created_at: str
    reviewed_at: str | None


class ResolveReviewRequest(BaseModel):
    analyst_decision: Literal["CONFIRMED_FRAUD", "LEGITIMATE"]
    analyst_reason: str = Field(min_length=1)
    
class MetricsResponse(BaseModel):
    evaluated_transactions: int

    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int

    precision: float
    recall: float
    f1_score: float
    accuracy: float
    
class PaySimScoreRequest(BaseModel):
    transaction_id: str = Field(min_length=1)
    transaction_type: str = Field(min_length=1)
    amount: float = Field(ge=0)
    oldbalance_org: float = Field(ge=0)
    oldbalance_dest: float = Field(ge=0)


class PaySimScoreResponse(BaseModel):
    transaction_id: str
    fraud_probability: float
    model_decision: str
    risk_level: str
    action: str
    
class PaySimReviewResponse(BaseModel):
    review_id: int
    transaction_id: str
    transaction_type: str

    amount: float
    oldbalance_org: float
    oldbalance_dest: float

    fraud_probability: float
    model_decision: str
    risk_level: str
    action: str

    status: str
    actual_outcome: str | None
    created_at: str
    reviewed_at: str | None


class PaySimResolveReviewRequest(BaseModel):
    actual_outcome: str