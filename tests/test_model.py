import pandas as pd

from src.model.predictor import FraudPredictor
from src.model.xgboost_adapter import XGBoostModelAdapter


EXPECTED_FEATURES = [
    "amt",
    "hour",
    "category",
    "prev_avg_amt",
    "prev_5_avg_amt",
    "amt_ratio_recent5",
]


def test_model_artifacts_load():
    predictor = FraudPredictor()

    assert predictor.preprocessor is not None
    assert predictor.model is not None


def test_model_feature_contract():
    predictor = FraudPredictor()

    actual_features = list(
        predictor.preprocessor.feature_names_in_
    )

    assert actual_features == EXPECTED_FEATURES


def test_model_returns_valid_probability():
    predictor = FraudPredictor()

    features = pd.DataFrame(
        [
            {
                "amt": 50.0,
                "hour": 12,
                "category": "grocery_pos",
                "prev_avg_amt": None,
                "prev_5_avg_amt": None,
                "amt_ratio_recent5": None,
            }
        ]
    )

    probability = predictor.predict_probability(features)

    assert isinstance(probability, float)
    assert 0.0 <= probability <= 1.0


def test_model_probability_is_reproducible():
    predictor = FraudPredictor()

    features = pd.DataFrame(
        [
            {
                "amt": 5000.0,
                "hour": 23,
                "category": "shopping_net",
                "prev_avg_amt": 55.0,
                "prev_5_avg_amt": 55.0,
                "amt_ratio_recent5": 5000.0 / 55.0,
            }
        ]
    )

    probability_1 = predictor.predict_probability(features)
    probability_2 = predictor.predict_probability(features)

    assert probability_1 == probability_2
    
def test_xgboost_adapter_loads_model_artifacts():
    adapter = XGBoostModelAdapter(
        preprocessor_path="models/fraud_preprocessor.joblib",
        model_path="models/fraud_xgb_model.json",
    )

    assert adapter.preprocessor is not None
    assert adapter.model is not None


def test_xgboost_adapter_returns_valid_probability():
    adapter = XGBoostModelAdapter(
        preprocessor_path="models/fraud_preprocessor.joblib",
        model_path="models/fraud_xgb_model.json",
    )

    features = pd.DataFrame(
        [
            {
                "amt": 100.0,
                "hour": 12,
                "category": "grocery_pos",
                "prev_avg_amt": 100.0,
                "prev_5_avg_amt": 100.0,
                "amt_ratio_recent5": 1.0,
            }
        ]
    )

    probability = adapter.predict_probability(features)

    assert 0.0 <= probability <= 1.0