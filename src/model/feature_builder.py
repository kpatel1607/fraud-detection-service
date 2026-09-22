from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.domain.transaction import CanonicalTransaction
from src.features.historical import HistoricalFeatures
from src.model.default_features import build_default_feature_registry
from src.model.feature_registry import FeatureRegistry


class FraudModelFeatureBuilder:
    """
    Builds the feature vector expected by the deployed fraud model.

    The model metadata defines which features are required.
    The feature registry defines how those features are produced.
    """

    def __init__(
        self,
        metadata_path: str = "models/fraud_model_metadata.json",
        feature_registry: FeatureRegistry | None = None,
    ) -> None:
        self.metadata_path = Path(metadata_path)

        if not self.metadata_path.exists():
            raise FileNotFoundError(
                f"Model metadata not found: {self.metadata_path}"
            )

        with self.metadata_path.open("r", encoding="utf-8") as file:
            self.metadata = json.load(file)

        self.expected_features = self.metadata["features"]

        self.feature_registry = (
            feature_registry
            if feature_registry is not None
            else build_default_feature_registry()
        )

    def build(
        self,
        transaction: CanonicalTransaction,
        historical: HistoricalFeatures,
    ) -> pd.DataFrame:

        feature_values = {}

        missing_features = []

        for feature in self.expected_features:
            provider = self.feature_registry.get(feature)

            if provider is None:
                missing_features.append(feature)
                continue

            feature_values[feature] = provider(
                transaction,
                historical,
            )

        if missing_features:
            raise ValueError(
                "Unable to build required model features: "
                + ", ".join(missing_features)
            )

        return pd.DataFrame(
            [
                {
                    feature: feature_values[feature]
                    for feature in self.expected_features
                }
            ]
        )