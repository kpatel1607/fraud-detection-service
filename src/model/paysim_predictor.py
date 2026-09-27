from __future__ import annotations

from src.model.paysim_feature_builder import PaySimFeatureBuilder
from src.model.xgboost_adapter import XGBoostModelAdapter


class PaySimFraudPredictor:
    """
    PaySim-specific prediction layer.

    Builds PaySim features and delegates model inference
    to the shared XGBoost model adapter.
    """

    def __init__(
        self,
        preprocessor_path: str = "models/paysim/preprocessor.joblib",
        model_path: str = "models/paysim/xgboost_model.json",
    ) -> None:
        self.feature_builder = PaySimFeatureBuilder()

        self.model = XGBoostModelAdapter(
            preprocessor_path=preprocessor_path,
            model_path=model_path,
        )

    def predict_probability(self, transaction) -> float:
        features = self.feature_builder.build(transaction)

        return self.model.predict_probability(features)