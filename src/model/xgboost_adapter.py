from __future__ import annotations

from pathlib import Path

import joblib
from xgboost import XGBClassifier

from src.model.model_adapter import ModelAdapter


class XGBoostModelAdapter(ModelAdapter):
    """
    Loads an XGBoost model and its fitted preprocessor.
    """

    def __init__(
        self,
        preprocessor_path: str,
        model_path: str,
    ) -> None:
        self.preprocessor_path = Path(preprocessor_path)
        self.model_path = Path(model_path)

        if not self.preprocessor_path.exists():
            raise FileNotFoundError(
                f"Preprocessor not found: {self.preprocessor_path}"
            )

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Model not found: {self.model_path}"
            )

        self.preprocessor = joblib.load(
            self.preprocessor_path
        )

        self.model = XGBClassifier()

        self.model.load_model(
            self.model_path
        )

    def predict_probability(
        self,
        features,
    ) -> float:
        transformed = self.preprocessor.transform(
            features
        )

        probability = self.model.predict_proba(
            transformed
        )[0, 1]

        return float(probability)