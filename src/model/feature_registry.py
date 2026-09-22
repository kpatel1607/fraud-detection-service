from __future__ import annotations

from collections.abc import Callable

from src.domain.transaction import CanonicalTransaction
from src.features.historical import HistoricalFeatures


FeatureProvider = Callable[
    [CanonicalTransaction, HistoricalFeatures],
    object,
]


class FeatureRegistry:
    """
    Maps model feature names to functions that produce their values.
    """

    def __init__(self) -> None:
        self._providers: dict[str, FeatureProvider] = {}

    def register(
        self,
        name: str,
        provider: FeatureProvider,
    ) -> None:
        if not name.strip():
            raise ValueError("Feature name cannot be empty.")

        if name in self._providers:
            raise ValueError(
                f"Feature provider already registered: {name}"
            )

        self._providers[name] = provider

    def get(self, name: str) -> FeatureProvider | None:
        return self._providers.get(name)

    def has(self, name: str) -> bool:
        return name in self._providers