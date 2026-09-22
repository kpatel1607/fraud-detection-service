from __future__ import annotations

from src.model.model_adapter import ModelAdapter
from src.model.xgboost_adapter import XGBoostModelAdapter


class FraudPredictor(ModelAdapter):
    """
    Prediction interface used by the fraud service.
    """

    def __init__(
        self,
        preprocessor_path: str = "models/fraud_preprocessor.joblib",
        model_path: str = "models/fraud_xgb_model.json",
    ) -> None:
        self.model = XGBoostModelAdapter(
            preprocessor_path=preprocessor_path,
            model_path=model_path,
        )

        # Preserve the existing public attributes.
        self.preprocessor = self.model.preprocessor
        self.xgb_model = self.model.model

    def predict_probability(
        self,
        features,
    ) -> float:
        return self.model.predict_probability(features)